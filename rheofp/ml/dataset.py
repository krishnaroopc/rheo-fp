"""Dataset layer: labelled spectra -> padded, masked tensors.

The frozen architecture takes SET-BASED stacks, so a batch is ragged: each
example holds N curves with N varying. Everything here exists to turn that
into rectangular tensors plus a mask, without ever letting padding leak into
a gradient.

Two rules this module enforces, both of which are easy to get wrong:

  * Splits are by STACK, never by curve. Curves from one material at
    different temperatures are near-duplicates; splitting per curve would put
    a temperature twin in train and its sibling in test, and the reported
    accuracy would be fiction.
  * Normalisation statistics come from the TRAINING split only, then are
    applied unchanged to val and test. Fitting them on everything leaks the
    test set into the model.

Channels per curve, all in log10 and dimensionless where possible:
    log10 omega (centred), log10 G', log10 G'', log10 tan(delta)
Absolute modulus scale is preserved as a per-curve summary feature rather
than being normalised away - a 600 kPa plateau and a 6 Pa gel differ by five
decades and that is real information.
"""
from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import Dataset

from rheofp.data.synth import ALL_CLASSES, CLASS_REGIME
from rheofp.io.data import load_npz

# ── config ────────────────────────────────────────────────────────────────
CLASSES = list(ALL_CLASSES)
CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}
REGIMES = sorted({CLASS_REGIME[c] for c in CLASSES})
REGIME_TO_IDX = {r: i for i, r in enumerate(REGIMES)}

N_CHANNELS = 4          # log w, log G', log G'', log tan(delta)
N_SUMMARY = 6           # per-curve scalars, see _summary()
EPS = 1e-30
SPLIT_FRACTIONS = (0.70, 0.15, 0.15)   # train / val / test

# Head 2 emits a fixed-width vector, but classes carry different parameter
# counts (2 for a critical gel, 4 for sticky reptation). Targets are padded to
# this width and masked, so a short class never trains the unused slots.
N_PARAMS = 4


def _summary(w, Gp, Gpp, T_K):
    """Per-curve scalars the sequence encoder would otherwise have to
    rediscover: absolute scale, window position and width, and temperature."""
    lw = np.log10(w)
    return np.array([
        np.log10(np.median(Gp) + EPS),      # absolute modulus scale
        np.log10(np.median(Gpp) + EPS),
        lw.min(),                            # where the window sits
        lw.max(),
        np.ptp(lw),                          # how wide it is
        0.0 if not np.isfinite(T_K) else (T_K - 298.15) / 50.0,
    ], dtype=np.float32)


def curve_tensor(w, Gp, Gpp):
    """(n_points, N_CHANNELS) float32 for one curve."""
    w = np.asarray(w, float)
    Gp = np.clip(np.asarray(Gp, float), EPS, None)
    Gpp = np.clip(np.asarray(Gpp, float), EPS, None)
    lw = np.log10(w)
    return np.stack([
        lw - lw.mean(),                 # shape of the window, not its position
        np.log10(Gp),
        np.log10(Gpp),
        np.log10(Gpp / Gp),
    ], axis=-1).astype(np.float32)


def _param_target(params):
    """Pad a class's planted parameter vector to N_PARAMS.

    Returns (vector, has_target). Padding is zero and is never scored - the
    mask is what stops a 2-parameter gel from training slots 3 and 4.
    """
    out = np.zeros(N_PARAMS, dtype=np.float32)
    if params is None:
        return out, False
    p = np.asarray(params, dtype=np.float32).ravel()[:N_PARAMS]
    out[:len(p)] = p
    return out, True


def examples_to_records(examples):
    """Convert generator output (rheofp.data.synth) into flat records."""
    out = []
    for ex in examples:
        curves = [(np.asarray(w, float), np.asarray(gp, float),
                   np.asarray(gpp, float), float(T))
                  for w, gp, gpp, T in ex["curves"]]
        out.append({"curves": curves, "label": ex["label"],
                    "regime": ex["regime"],
                    "params": np.asarray(ex["params"], float)})
    return out


def npz_to_records(path):
    """Regroup a saved npz back into stacks via its stack_id field."""
    data = load_npz(path)
    stacks = {}
    for fields in data.values():
        sid = int(fields["stack_id"])
        stacks.setdefault(sid, {"curves": [], "label": str(fields["label"]),
                                "regime": str(fields["regime"]),
                                "params": np.asarray(fields["params"], float)})
        stacks[sid]["curves"].append((
            np.asarray(fields["omega"], float),
            np.asarray(fields["Gp"], float),
            np.asarray(fields["Gpp"], float),
            float(fields["T_K"]),
        ))
    return [stacks[k] for k in sorted(stacks)]


def split_records(records, fractions=SPLIT_FRACTIONS, seed=0):
    """Split BY STACK. Curves within one stack never cross the boundary."""
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(records))
    n_train = int(round(fractions[0] * len(records)))
    n_val = int(round(fractions[1] * len(records)))
    parts = (idx[:n_train], idx[n_train:n_train + n_val], idx[n_train + n_val:])
    return tuple([records[int(i)] for i in part] for part in parts)


class SpectraStacks(Dataset):
    """Ragged stacks of spectra with class + regime labels."""

    def __init__(self, records, norm=None):
        self.records = records
        self.norm = norm

    def __len__(self):
        return len(self.records)

    def __getitem__(self, i):
        rec = self.records[i]
        curves = [curve_tensor(w, gp, gpp) for w, gp, gpp, _ in rec["curves"]]
        summ = np.stack([_summary(w, gp, gpp, T)
                         for w, gp, gpp, T in rec["curves"]])
        x = np.stack(curves)                       # (n_curves, n_pts, C)
        if self.norm is not None:
            x = (x - self.norm["x_mean"]) / self.norm["x_std"]
            summ = (summ - self.norm["s_mean"]) / self.norm["s_std"]
        params, params_mask = _param_target(rec.get("params"))
        return {
            "x": torch.from_numpy(np.ascontiguousarray(x, dtype=np.float32)),
            "summary": torch.from_numpy(summ.astype(np.float32)),
            "label": CLASS_TO_IDX[rec["label"]],
            "regime": REGIME_TO_IDX[rec["regime"]],
            "params": torch.from_numpy(params),
            "params_mask": bool(params_mask),
        }


def fit_normalisation(records):
    """Channel statistics from the TRAINING split only."""
    xs, ss = [], []
    for rec in records:
        for w, gp, gpp, T in rec["curves"]:
            xs.append(curve_tensor(w, gp, gpp))
            ss.append(_summary(w, gp, gpp, T))
    X = np.concatenate(xs, axis=0)
    S = np.stack(ss)
    return {
        "x_mean": X.mean(axis=0).astype(np.float32),
        "x_std": (X.std(axis=0) + 1e-6).astype(np.float32),
        "s_mean": S.mean(axis=0).astype(np.float32),
        "s_std": (S.std(axis=0) + 1e-6).astype(np.float32),
    }


def collate_stacks(batch):
    """Pad ragged stacks to the batch's longest and emit a validity mask.

    The mask is the contract with the model: padded slots must never reach a
    pooled representation or a gradient.
    """
    n_max = max(b["x"].shape[0] for b in batch)
    n_pts = batch[0]["x"].shape[1]
    C = batch[0]["x"].shape[2]
    B = len(batch)

    x = torch.zeros(B, n_max, n_pts, C)
    summary = torch.zeros(B, n_max, N_SUMMARY)
    mask = torch.zeros(B, n_max, dtype=torch.bool)
    for i, b in enumerate(batch):
        n = b["x"].shape[0]
        x[i, :n] = b["x"]
        summary[i, :n] = b["summary"]
        mask[i, :n] = True
    return {
        "x": x,
        "summary": summary,
        "mask": mask,
        "label": torch.tensor([b["label"] for b in batch], dtype=torch.long),
        "regime": torch.tensor([b["regime"] for b in batch], dtype=torch.long),
        "params": torch.stack([b["params"] for b in batch]),
        "params_mask": torch.tensor([b["params_mask"] for b in batch],
                                    dtype=torch.bool),
    }
