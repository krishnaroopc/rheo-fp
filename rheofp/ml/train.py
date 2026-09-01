"""Training loop for RheoNet.

The interesting part is the abstention objective. Head 1 must be able to say
"this input does not discriminate" - but a model rewarded for abstaining will
abstain on everything, and a model never rewarded for it will never abstain.
So abstention is trained as a LEARNED-CONFIDENCE problem:

    loss = CE(class) + regime_weight * CE(regime)
         + abstain_weight * BCE(abstain_logit, target)
         + param_weight * SmoothL1(params)

where the abstention TARGET is not a hand-labelled flag but whether the
classifier actually got this example wrong (detached, so it trains the
abstention head without back-propagating into the classifier). The head
therefore learns to predict its own failures, which is exactly what an
abstention signal should be. ABSTAIN_WEIGHT keeps it from dominating.

Head 2 (parameters) is trained only where a target exists; classes have
different parameter counts, so targets are padded and masked.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader

from rheofp.ml.dataset import (
    SpectraStacks, collate_stacks, fit_normalisation, split_records, CLASSES,
)
from rheofp.ml.model import RheoNet, count_parameters, N_PARAMS_OUT

# ── config ────────────────────────────────────────────────────────────────
BATCH_SIZE = 64
LR = 3e-4
WEIGHT_DECAY = 1e-4
EPOCHS = 40
PATIENCE = 8              # early stop after this many epochs without val gain
REGIME_WEIGHT = 0.3       # regime head is an auxiliary task, not the objective
ABSTAIN_WEIGHT = 0.2
PARAM_WEIGHT = 0.1
GRAD_CLIP = 1.0
NUM_WORKERS = 0           # datasets are small and in memory; workers cost more
                          # than they save here


def device_auto():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def make_loaders(records, batch_size=BATCH_SIZE, seed=0):
    """Split by stack, fit normalisation on train only, build loaders."""
    train_rec, val_rec, test_rec = split_records(records, seed=seed)
    norm = fit_normalisation(train_rec)
    loaders = []
    for rec, shuffle in ((train_rec, True), (val_rec, False), (test_rec, False)):
        ds = SpectraStacks(rec, norm=norm)
        loaders.append(DataLoader(ds, batch_size=batch_size, shuffle=shuffle,
                                  collate_fn=collate_stacks,
                                  num_workers=NUM_WORKERS))
    return (*loaders, norm)


def compute_loss(out, batch):
    """Combined objective. Returns (total, parts dict).

    Head 2's targets are the planted parameter vectors, padded to a fixed
    width and masked - a 2-parameter critical gel must not train the two
    unused slots, or the head learns to predict padding.
    """
    labels = batch["label"]
    ce = F.cross_entropy(out["class_logits"], labels)
    reg = F.cross_entropy(out["regime_logits"], batch["regime"])

    # Abstention target: did the classifier get this one wrong? Detached, so
    # this term shapes the abstain head without steering the classifier.
    with torch.no_grad():
        wrong = (out["class_logits"].argmax(dim=1) != labels).float()
    ab = F.binary_cross_entropy_with_logits(out["abstain_logit"], wrong)

    total = ce + REGIME_WEIGHT * reg + ABSTAIN_WEIGHT * ab
    parts = {"ce": ce.item(), "regime": reg.item(), "abstain": ab.item(),
             "params": 0.0}

    tgt = batch.get("params")
    tgt_mask = batch.get("params_mask")
    if tgt is not None and tgt_mask is not None and tgt_mask.any():
        pl = F.smooth_l1_loss(out["params"][tgt_mask], tgt[tgt_mask])
        total = total + PARAM_WEIGHT * pl
        parts["params"] = pl.item()
    return total, parts


@torch.no_grad()
def evaluate(model, loader, device):
    """Accuracy, regime accuracy, and abstention diagnostics."""
    model.eval()
    n = correct = regime_correct = 0
    abstain_scores, was_wrong = [], []
    for batch in loader:
        x = batch["x"].to(device)
        s = batch["summary"].to(device)
        m = batch["mask"].to(device)
        y = batch["label"].to(device)
        out = model(x, s, m)
        pred = out["class_logits"].argmax(dim=1)
        correct += (pred == y).sum().item()
        regime_correct += (out["regime_logits"].argmax(dim=1)
                           == batch["regime"].to(device)).sum().item()
        abstain_scores.append(torch.sigmoid(out["abstain_logit"]).cpu().numpy())
        was_wrong.append((pred != y).cpu().numpy())
        n += y.numel()
    scores = np.concatenate(abstain_scores) if abstain_scores else np.zeros(0)
    wrong = np.concatenate(was_wrong) if was_wrong else np.zeros(0, bool)
    return {
        "accuracy": correct / max(1, n),
        "regime_accuracy": regime_correct / max(1, n),
        "abstain_mean": float(scores.mean()) if scores.size else 0.0,
        "abstain_auc": _auc(scores, wrong),
        "n": n,
    }


def _auc(scores, wrong):
    """Can the abstention score rank errors above correct predictions?

    0.5 means the signal is worthless; 1.0 means every error is flagged ahead
    of every correct answer. Rank-based, so it needs no threshold.
    """
    if scores.size == 0 or wrong.sum() == 0 or (~wrong).sum() == 0:
        return float("nan")
    # Average ranks over ties, so an all-constant (useless) score scores 0.5
    # rather than whatever order argsort happened to produce.
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    s_sorted = scores[order]
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + j + 2) / 2.0
        i = j + 1
    n_pos, n_neg = wrong.sum(), (~wrong).sum()
    return float((ranks[wrong].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def train(records, epochs=EPOCHS, lr=LR, batch_size=BATCH_SIZE, seed=0,
          device=None, checkpoint=None, verbose=True):
    """Train RheoNet. Returns (model, history, test_metrics, norm)."""
    torch.manual_seed(seed)
    device = device or device_auto()
    train_loader, val_loader, test_loader, norm = make_loaders(
        records, batch_size=batch_size, seed=seed)

    model = RheoNet().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, epochs))

    if verbose:
        print(f"device={device}  parameters={count_parameters(model):,}")
        print(f"train={len(train_loader.dataset)}  val={len(val_loader.dataset)} "
              f" test={len(test_loader.dataset)}")

    history, best_val, best_state, stale = [], -1.0, None, 0
    for epoch in range(1, epochs + 1):
        model.train()
        t0, running = time.time(), []
        for batch in train_loader:
            x = batch["x"].to(device)
            s = batch["summary"].to(device)
            m = batch["mask"].to(device)
            batch = {**batch, "label": batch["label"].to(device),
                     "regime": batch["regime"].to(device),
                     "params": batch["params"].to(device),
                     "params_mask": batch["params_mask"].to(device)}
            out = model(x, s, m)
            loss, parts = compute_loss(out, batch)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            opt.step()
            running.append(loss.item())
        sched.step()

        val = evaluate(model, val_loader, device)
        history.append({"epoch": epoch, "train_loss": float(np.mean(running)),
                        **{f"val_{k}": v for k, v in val.items()}})
        if verbose:
            print(f"  epoch {epoch:3d}  loss {np.mean(running):.4f}  "
                  f"val acc {val['accuracy']:.3f}  regime {val['regime_accuracy']:.3f}  "
                  f"abstain AUC {val['abstain_auc']:.3f}  ({time.time()-t0:.1f}s)")

        if val["accuracy"] > best_val:
            best_val, stale = val["accuracy"], 0
            best_state = {k: v.detach().cpu().clone()
                          for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= PATIENCE:
                if verbose:
                    print(f"  early stop at epoch {epoch} "
                          f"(no val gain for {PATIENCE})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    test = evaluate(model, test_loader, device)

    if checkpoint:
        Path(checkpoint).parent.mkdir(parents=True, exist_ok=True)
        torch.save({"state_dict": model.state_dict(), "norm": norm,
                    "classes": CLASSES, "history": history, "test": test},
                   checkpoint)
        if verbose:
            print(f"saved {checkpoint}")

    return model, history, test, norm
