"""Synthetic SAOS training-set generator.

Samples labelled (G'(omega), G''(omega)) spectra from the validated forward
models, in the set-based form the frozen architecture expects: every example
is a STACK of curves, and a single curve is the degenerate N=1 case.

Design notes:
  * Labels come from the generating model, not from a fit - this is planted
    ground truth, the same discipline the validation scripts use.
  * Sampling is in log space over the same parameter bounds the fitters use
    (rheofp.models.solutions.MODELS and the network bank), so the generated
    population and the fitting search space cannot drift apart.
  * Stacks are physically coherent, not independent draws: a temperature stack
    Arrhenius-shifts ONE set of parameters, and a concentration stack applies
    one scaling law. Independent draws per curve would teach the classifier a
    correlation that no real material has.
  * Output is the canonical npz layout (rheofp.io.data), so generated sets load
    with the same loader as the digitized literature data.

Everything hardcoded lives in the config block below.

Run via scripts/generate_dataset.py.
"""
from __future__ import annotations

import numpy as np

from rheofp.models.maxwell import (
    maxwell_spectrum, wlm_spectrum, branched_spectrum, arrhenius_shift,
)
from rheofp.models.network import chasset_thirion_spectrum, critical_gel_spectrum
from rheofp.models.solutions import MODELS as SOLUTION_MODELS

# ── config ────────────────────────────────────────────────────────────────
OMEGA_DECADES = (-2.0, 3.0)   # log10 rad/s, the span of a typical sweep
N_OMEGA = 60                  # default/reference density (see N_OMEGA_RANGE)
# Real uploads are not all one density: a curve digitized off a published
# figure carries ~10-20 points, a rheometer sweep 50-100. Training at a single
# fixed count taught the model to lean on density itself, and it then failed
# on every real curve until it was resampled. The count is therefore sampled
# per curve; the ML loader resamples to its own grid regardless
# (rheofp.ml.dataset.resample_log_grid), so this varies what the model sees
# rather than what it requires.
N_OMEGA_RANGE = (10, 100)
# A real instrument sees a window, not the whole spectrum. Randomly cropping
# the window is what teaches the classifier to abstain rather than assume the
# terminal region is absent because the material has none.
WINDOW_CROP_DECADES = (0.0, 2.5)
NOISE_DECADES = 0.02          # multiplicative log-normal scatter, ~2% - matches
                              # the digitizing scatter seen on real figures

STACK_SIZES = (1, 2, 3, 4, 5)
STACK_WEIGHTS = (0.40, 0.10, 0.15, 0.15, 0.20)   # N=1 is the common real case

T_REF = 298.15
T_SPREAD_K = (10.0, 60.0)     # total spread of a temperature stack
EA_RANGE = (20e3, 120e3)      # J/mol, activation energy for T-stacks

# Regime + class taxonomy. Values are (regime, sampler-name).
CLASS_REGIME = {
    "zimm": "terminal",
    "rouse_screened": "terminal",
    "reptation": "terminal",
    "sticky_rouse": "terminal",
    "sticky_reptation": "terminal",
    "cured_elastomer": "solid",
    "critical_gel": "solid",
    "wormlike_micelle": "terminal",
    "branched": "terminal",
}
# Classes the identifier can emit as a fine label; the rest are model-only
# (they exist in the population but are labelled at regime level).
FINE_CLASSES = ("zimm", "rouse_screened", "reptation", "sticky_rouse",
                "sticky_reptation", "cured_elastomer", "critical_gel")
MODEL_ONLY_CLASSES = ("wormlike_micelle", "branched")
ALL_CLASSES = FINE_CLASSES + MODEL_ONLY_CLASSES

# Network-family sampling ranges (log10 Pa where noted).
CURED_LOG_GINF = (3.0, 6.5)
CURED_LOG_C = (2.0, 5.0)
CURED_M = (0.05, 0.45)
GEL_LOG_C = (0.0, 4.0)
GEL_U = (0.45, 0.80)          # Winter-Chambon 0.5 through Tixier 0.75

WLM_LOG_G0 = (0.0, 4.0)
WLM_LOG_TAU_REP = (-1.0, 3.0)
WLM_LOG_TAU_BR = (-4.0, 0.0)
WLM_BETA = (0.2, 1.5)

BRANCHED_LOG_GE = (3.0, 6.0)
BRANCHED_LOG_TAU_B = (-1.0, 3.0)
# sigma = breadth of the mode ladder, in decades. The old ceiling of 4.0 made
# the whole class plateau-dominated (median tan(delta) ~0.32) while real LDPE
# melts sit near ~1.0 - so no synthetic branched example looked like the one
# real branched material in data/. Widened after fitting branched_spectrum to
# Pivokonsky E and B, which drove sigma hard against any ceiling it was given.
# Note the honest limit recorded in next-actions.md: even at large sigma this
# 3-parameter form only reaches ~0.2-0.28 decades RMS on that data (a 10-mode
# Maxwell reaches 0.02), so widening the range makes the class cover realistic
# breadth - it does not make the forward model adequate for real LDPE.
BRANCHED_SIGMA = (1.0, 10.0)


# ── parameter sampling ────────────────────────────────────────────────────
def _u(rng, lohi):
    return float(rng.uniform(*lohi))


def sample_params(rng, name):
    """Draw one physically-plausible parameter set for `name`."""
    if name in SOLUTION_MODELS:
        _, _, bounds, _ = SOLUTION_MODELS[name]
        return np.array([rng.uniform(lo, hi) for lo, hi in bounds], float)
    if name == "cured_elastomer":
        return np.array([_u(rng, CURED_LOG_GINF), _u(rng, CURED_LOG_C),
                         _u(rng, CURED_M)])
    if name == "critical_gel":
        return np.array([_u(rng, GEL_LOG_C), _u(rng, GEL_U)])
    if name == "wormlike_micelle":
        return np.array([_u(rng, WLM_LOG_G0), _u(rng, WLM_LOG_TAU_REP),
                         _u(rng, WLM_LOG_TAU_BR), _u(rng, WLM_BETA)])
    if name == "branched":
        return np.array([_u(rng, BRANCHED_LOG_GE), _u(rng, BRANCHED_LOG_TAU_B),
                         _u(rng, BRANCHED_SIGMA)])
    raise ValueError(f"unknown class {name!r}")


def forward(name, w, theta, tau_scale=1.0):
    """Evaluate a class's forward model. `tau_scale` multiplies every
    characteristic time, which is how a temperature stack is generated."""
    if name in SOLUTION_MODELS:
        fwd, _, _, _ = SOLUTION_MODELS[name]
        th = np.array(theta, float)
        # every solution model carries its time parameter(s) in log10 seconds
        th = _scale_solution_times(name, th, tau_scale)
        return fwd(w, th)
    if name == "cured_elastomer":
        lG, lc, m = theta
        # a springpot has no single relaxation time; shifting it in time is
        # equivalent to rescaling c by tau_scale**m
        return chasset_thirion_spectrum(w, 10.0**lG, 10.0**lc * tau_scale**m, m)
    if name == "critical_gel":
        lc, u = theta
        return critical_gel_spectrum(w, 10.0**lc * tau_scale**u, u)
    if name == "wormlike_micelle":
        lG0, lrep, lbr, beta = theta
        return wlm_spectrum(w, 10.0**lG0, 10.0**lrep * tau_scale,
                            10.0**lbr * tau_scale, beta)
    if name == "branched":
        lGe, ltau, sigma = theta
        return branched_spectrum(w, 10.0**lGe, 10.0**ltau * tau_scale, sigma)
    raise ValueError(f"unknown class {name!r}")


# index of the log10-time parameters in each solution model's theta
_SOLUTION_TIME_IDX = {
    "zimm": (1,), "rouse_screened": (1,), "reptation": (1,),
    "sticky_rouse": (1, 2), "sticky_reptation": (1, 3),
}


def _scale_solution_times(name, theta, tau_scale):
    if tau_scale == 1.0:
        return theta
    out = theta.copy()
    for i in _SOLUTION_TIME_IDX[name]:
        out[i] = out[i] + np.log10(tau_scale)
    return out


# ── one example ───────────────────────────────────────────────────────────
def _omega_window(rng, n=None):
    """A randomly cropped measurement window inside the full span.

    `n` is the point count; when None it is drawn from N_OMEGA_RANGE so the
    population spans the densities real uploads arrive at.
    """
    lo, hi = OMEGA_DECADES
    crop = rng.uniform(*WINDOW_CROP_DECADES)
    lo_shift = rng.uniform(0.0, crop)
    if n is None:
        n = int(rng.integers(N_OMEGA_RANGE[0], N_OMEGA_RANGE[1] + 1))
    return np.logspace(lo + lo_shift, hi - (crop - lo_shift), n)


def _add_noise(rng, Gp, Gpp):
    if NOISE_DECADES <= 0:
        return Gp, Gpp
    f = lambda a: a * 10.0 ** (rng.normal(0.0, NOISE_DECADES, size=np.shape(a)))
    return f(Gp), f(Gpp)


def make_example(rng, name, n_curves=None):
    """Generate one labelled stack.

    Returns dict(curves=[(omega, Gp, Gpp, T_K), ...], label=..., regime=...,
    params=..., Ea=...). A temperature stack shares one parameter set and one
    activation energy - only tau shifts between curves.
    """
    if n_curves is None:
        n_curves = int(rng.choice(STACK_SIZES, p=STACK_WEIGHTS))
    theta = sample_params(rng, name)
    w = _omega_window(rng)

    if n_curves == 1:
        Gp, Gpp = forward(name, w, theta)
        Gp, Gpp = _add_noise(rng, Gp, Gpp)
        return {"curves": [(w, Gp, Gpp, np.nan)], "label": name,
                "regime": CLASS_REGIME[name], "params": theta, "Ea": np.nan}

    spread = _u(rng, T_SPREAD_K)
    temps = np.linspace(T_REF - spread / 2, T_REF + spread / 2, n_curves)
    # A permanent network does not shift with temperature; everything else does.
    is_network = name in ("cured_elastomer", "critical_gel")
    Ea = 0.0 if is_network else _u(rng, EA_RANGE)

    curves = []
    lw = np.log10(w)
    for T in temps:
        # Same window (one material, one instrument), but each temperature is
        # its own sweep, so the point count is redrawn per curve.
        w_T = np.logspace(lw[0], lw[-1],
                          int(rng.integers(N_OMEGA_RANGE[0],
                                           N_OMEGA_RANGE[1] + 1)))
        tau_scale = 1.0 if is_network else float(
            arrhenius_shift(1.0, Ea, T, T_REF))
        Gp, Gpp = forward(name, w_T, theta, tau_scale=tau_scale)
        if is_network:
            # entropic elasticity: moduli scale with absolute temperature
            Gp, Gpp = Gp * (T / T_REF), Gpp * (T / T_REF)
        Gp, Gpp = _add_noise(rng, Gp, Gpp)
        curves.append((w_T, Gp, Gpp, float(T)))

    return {"curves": curves, "label": name, "regime": CLASS_REGIME[name],
            "params": theta, "Ea": Ea}


# ── dataset ───────────────────────────────────────────────────────────────
def generate(n_examples, classes=ALL_CLASSES, seed=0, progress=True):
    """Generate `n_examples` labelled stacks, balanced across `classes`.

    Returns a list of example dicts. Set progress=False to silence the bar.
    """
    rng = np.random.default_rng(seed)
    classes = list(classes)
    order = [classes[i % len(classes)] for i in range(n_examples)]
    rng.shuffle(order)

    it = order
    if progress:
        try:
            from tqdm import tqdm
            it = tqdm(order, desc="generating", unit="ex")
        except ImportError:
            pass

    out = []
    for name in it:
        out.append(make_example(rng, name))
    return out


def to_npz_dataset(examples):
    """Flatten examples into the canonical {sample: dict(...)} npz layout.

    Each curve becomes its own sample keyed "<index>_<label>_T<k>", carrying
    the label, regime and stack id so the training pipeline can regroup them.
    """
    dataset = {}
    for i, ex in enumerate(examples):
        for k, (w, Gp, Gpp, T) in enumerate(ex["curves"]):
            dataset[f"{i:06d}_{ex['label']}_T{k}"] = dict(
                omega=w, Gp=Gp, Gpp=Gpp, T_K=T, conc=np.nan,
                label=ex["label"], regime=ex["regime"],
                stack_id=i, n_curves=len(ex["curves"]),
                params=np.asarray(ex["params"], float), Ea=ex["Ea"],
            )
    return dataset


def class_counts(examples):
    counts = {}
    for ex in examples:
        counts[ex["label"]] = counts.get(ex["label"], 0) + 1
    return dict(sorted(counts.items()))
