"""Synthetic SAOS training-set generator.

Samples labelled (G'(omega), G''(omega)) spectra from the validated forward
models, in the set-based form the frozen architecture expects: every example
is a STACK of curves, and a single curve is the degenerate N=1 case.

Design notes:
  * Labels come from the generating model, not from a fit - this is planted
    ground truth, the same discipline the validation scripts use.
  * Sampling is in log space over the same parameter bounds the fitters use
    (rheofp.models.solutions.MODELS, the network bank, and
    rheofp.models.maxwell.BRANCHED_MODELS), so the generated population and
    the fitting search space cannot drift apart - there is a test for this.
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
    maxwell_spectrum, wlm_spectrum, bsw_spectrum, arrhenius_shift,
)
from rheofp.models.network import chasset_thirion_spectrum, critical_gel_spectrum
from rheofp.models.solutions import MODELS as SOLUTION_MODELS
from rheofp.models.star import star_spectrum, tau_of_s as star_tau_of_s

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
    "star": "terminal",
}
# Classes the identifier can emit as a fine label. wormlike_micelle and
# branched were model-only (regime-level-only) until 2026-09-07: BSW fits
# real LDPE to ~0.06 decades and its errors land on physically adjacent
# classes (zimm/rouse), and wormlike_micelle tested 100% self-correct against
# the sticky classes it was suspected of being confused with (measured
# 2026-09-07, n=40/class) - both promoted to ordinary fine labels by user
# decision. See CLAUDE.md and .claude-notes/next-actions.md.
# `star` (Milner-McLeish arm retraction) added 2026-09-09, closing the reverse
# bank/generator gap: it had been wired into identify()'s bank after its
# cannibalisation check while synth.py still could not sample it, so the AICc
# side could emit a class the neural head had never been trained on.
FINE_CLASSES = ("zimm", "rouse_screened", "reptation", "sticky_rouse",
                "sticky_reptation", "cured_elastomer", "critical_gel",
                "wormlike_micelle", "branched", "star")
ALL_CLASSES = FINE_CLASSES

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

# Branched / long-chain-branched melt (BSW spectrum). Ranges chosen so the
# synthetic population brackets the real LDPE melts in data/pivo2006.npz:
# fit_bsw on Pivokonsky E and B lands at G_N ~ 1 kPa (window-limited amplitude,
# not a true plateau), tau_max ~ 50-90 s, tau_c ~ 20-30 s, n_e ~ 0.55-0.68,
# n_g ~ 0.53-0.56. The old 3-param branched_spectrum could not reach that data
# (~0.28 decades RMS whatever sigma); BSW reaches ~0.06.
BRANCHED_LOG_GN = (2.5, 6.0)        # amplitude scale [log10 Pa]
BRANCHED_LOG_TAU_MAX = (-1.0, 3.0)  # longest time [log10 s]
# tau_c is drawn as an offset BELOW tau_max, in decades - so it is always the
# shorter time and the two never cross.
BRANCHED_TAU_C_OFFSET_DECADES = (0.2, 4.0)
BRANCHED_N_E = (0.15, 0.75)         # terminal-wedge exponent
BRANCHED_N_G = (0.40, 0.70)         # glassy-wedge exponent

# Star melt (Milner-McLeish arm retraction). Added 2026-09-09, after `star`
# was wired into identify()'s bank; before that the bank could emit a class
# the generator could not produce, so the neural head had no star label.
STAR_LOG_GN = (3.5, 6.5)            # plateau modulus [log10 Pa]
# Entanglements per arm - the ONLY shape parameter (arm COUNT does not enter
# LVE at all; see rheofp/models/star.py). Sampled a little inside the fitter's
# Z_BOUNDS = (4, 60) so a planted curve never sits on a bound.
STAR_Z = (5.0, 55.0)
# tau_e is NOT drawn independently. A star's spectrum spans ~23-24 decades
# from tau_e up to the terminal tau(1), while a sweep window is ~3-5 decades,
# so an independent draw would put the visible slice essentially anywhere -
# usually somewhere featureless. Instead the TERMINAL time is placed relative
# to the window (the physically meaningful anchor, and what a real experiment
# is set up to catch) and tau_e is back-computed from it, since tau(1)/tau_e
# is a fixed function of Z. Same idea as BRANCHED_TAU_C_OFFSET_DECADES
# deriving tau_c from tau_max rather than drawing it free.
#
# Offset in decades of the terminal time relative to the nominal window's low
# edge (1/w_lo): 0 puts terminal relaxation right at that edge, POSITIVE makes
# tau(1) longer so the terminal moves BELOW the window (not reached - the
# common case for a well-entangled star), NEGATIVE makes it shorter so flow is
# visible inside the sweep.
#
# Range chosen by measurement, not taste. The window is independently cropped
# by up to WINDOW_CROP_DECADES from BOTH ends after these params are drawn, so
# the effective low edge is typically ~1 decade above the nominal one - an
# offset centred on 0 therefore still lands most curves below the window. The
# range below was tuned so the planted population carries BOTH cases -
# measured 51% terminal_reached over n=120. The first attempt, (-1, 3), gave
# **0%**: every planted star had its terminal relaxation below the window. That
# would have taught the classifier that stars never flow, making
# `terminal_reached` a spurious star-vs-melt discriminator - the same shape of
# defect as the fixed-60-point density bug, a sampling artifact learned as
# physics. Re-measure this fraction if the range is ever touched.
STAR_TERMINAL_OFFSET_DECADES = (-3.0, 1.0)


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
        log_tau_max = _u(rng, BRANCHED_LOG_TAU_MAX)
        log_tau_c = log_tau_max - _u(rng, BRANCHED_TAU_C_OFFSET_DECADES)
        return np.array([_u(rng, BRANCHED_LOG_GN), log_tau_max, log_tau_c,
                         _u(rng, BRANCHED_N_E), _u(rng, BRANCHED_N_G)])
    if name == "star":
        Z = _u(rng, STAR_Z)
        # Place the TERMINAL time relative to the window's low edge, then back
        # out tau_e, because tau(1)/tau_e is a fixed function of Z alone.
        log_terminal = -OMEGA_DECADES[0] + _u(rng, STAR_TERMINAL_OFFSET_DECADES)
        log_tau_e = log_terminal - _star_terminal_decades(Z)
        return np.array([_u(rng, STAR_LOG_GN), Z, log_tau_e])
    raise ValueError(f"unknown class {name!r}")


def _star_terminal_decades(Z):
    """log10(tau(1)/tau_e) for a star of Z entanglements per arm.

    Depends only on Z (tau_e is a pure multiplicative time scale), so it can be
    evaluated once at tau_e = 1 and used to convert a desired terminal time
    into the tau_e that produces it. Ranges ~2.6 decades at Z=4 to ~8.6 at
    Z=60.
    """
    return float(np.log10(star_tau_of_s(1.0 - 1e-9, float(Z), 1.0)))


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
        lGN, ltau_max, ltau_c, n_e, n_g = theta
        return bsw_spectrum(w, 10.0**lGN, 10.0**ltau_max * tau_scale,
                            10.0**ltau_c * tau_scale, n_e, n_g)
    if name == "star":
        lGN, Z, ltau_e = theta
        # tau_e is the only time in the model - every tau(s) is proportional
        # to it - so an Arrhenius stack shifts it and the whole spectrum
        # translates rigidly in log omega, which is the physically right
        # behaviour for a melt.
        return star_spectrum(w, 10.0**lGN, Z, 10.0**ltau_e * tau_scale)
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
