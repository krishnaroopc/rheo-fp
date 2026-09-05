"""Regime-aware model identification for SAOS spectra.

Canonical source: solution_identifier.ipynb. Pipeline: permissive
signature-feature pre-filter -> multi-restart L-BFGS-B fit in log space ->
AICc ranking with Akaike weights -> none-of-the-above floor via FLOOR_CHI2.
Lesson learned in the original notebook: aggressive pre-filter pruning caused
misclassification; keep the pre-filter permissive and let AICc resolve.

The candidate bank merges four families: the polymer-solution models
(Zimm/Rouse/reptation and their sticky variants), the crosslinked-network
models (cured elastomer, critical gel), the branched / long-chain-branched
melt model (a BSW spectrum, e.g. for LDPE), and the wormlike micelle. A
permanent network cannot flow, so observing terminal relaxation inside the
window is the one robust contraindication that hard-discards the network
candidates.

The bank must cover EVERY class rheofp.data.synth can generate. It briefly did
not: wormlike_micelle was generated and learnable by the neural head but had no
registry entry here, so identify() could not emit it at any cost. Two things
went wrong as a result, and both are worth not repeating. The physics baseline
was scored on a pool containing that class, so ~1/9 of its exam was
unanswerable and its published accuracy was structurally depressed. Worse, a
wormlike micelle handed to the 8-model bank came back as "branched" at Akaike
weight 1.000 with a 0.05-decade residual - BSW's five parameters fit a
near-single-Maxwell shape comfortably, so the FLOOR_CHI2 none-of-the-above
floor never fired. A missing class does not present as low confidence; it
presents as a confident wrong answer from whichever candidate is most flexible.

"branched" and "wormlike_micelle" are emitted only at regime level
(Terminal/liquid-like) per the frozen taxonomy - they are model-only classes.
They sit in the bank so AICc can actually adjudicate a broad LCB-like or a
narrow micellar terminal spectrum instead of defaulting to whatever fits least
badly.

Abstention: a cured elastomer and a high-Mw entangled melt are genuinely
indistinguishable from a single SAOS curve whose terminal relaxation lies
below the window - both show only a flat G' plateau. Resolving that needs a
temperature stack (the melt's terminal time shifts into the window on
heating; a true network's plateau does not). identify() therefore abstains
rather than committing; see melt_rubber_ambiguous().

Two entry points:
  identify(w, Gp, Gpp)  - one curve. Abstains on the melt-vs-rubber question.
  identify_stack(stack) - the architecture's native set-based input. Adds
      resolve_melt_vs_network(), which settles that question from evidence a
      single curve cannot carry, and either lifts the abstention or overturns
      a network call the stack disproves.
"""
from __future__ import annotations

import numpy as np

from rheofp.models.solutions import MODELS
from rheofp.models.network import NETWORK_MODELS, tan_delta_spread
from rheofp.models.maxwell import BRANCHED_MODELS, WLM_MODELS
from rheofp.fitting.optimize import multi_restart_fit

N_RESTARTS = 12
FLOOR_CHI2 = 0.15  # normalized RMS log-residual above which we flag low confidence
RNG_SEED = 0

# Full candidate bank: solution family + crosslinked-network family +
# branched / LCB melt + wormlike micelle. This must stay in step with
# rheofp.data.synth.ALL_CLASSES - a class the generator can produce but the
# bank cannot emit is unanswerable, not merely hard (there is a test).
ALL_MODELS = {**MODELS, **NETWORK_MODELS, **BRANCHED_MODELS, **WLM_MODELS}

# Names belonging to the Solid/gel-like regime, for regime-level reporting.
NETWORK_CLASSES = frozenset(NETWORK_MODELS)
# Model-only classes: emitted at regime level only, never as a fine label.
MODEL_ONLY_CLASSES = frozenset(BRANCHED_MODELS) | frozenset(WLM_MODELS)

# --- abstention thresholds (melt-vs-rubber) ---
# |dlog10 G'/dlog10 w| below this counts as "flat" when measuring plateau width.
FLAT_SLOPE_TOL = 0.15
# Temperatures required before a stack is considered able to resolve the
# melt-vs-rubber ambiguity at all. Two points define a shift; fewer cannot.
MIN_STACK_TEMPERATURES = 2

# --- stack-level resolver (melt-vs-network across temperature) ---
# Horizontal shift, in decades, that the stack must span before the spectrum
# counts as "moving with temperature". This is the T-shift-coverage threshold
# the design called for. Grounding: a melt with Ea ~ 60 kJ/mol over a 40 K
# spread shifts ~1.4 decades, while a permanent network's plateau does not
# move at all - so 0.5 sits an order of magnitude clear of network noise and
# well below any real melt's shift.
SHIFT_DECADES_MIN = 0.5
# Widest shift searched when aligning two temperatures.
SHIFT_SEARCH_DECADES = 5.0
# Fraction of the narrower curve that must overlap after shifting for the
# alignment residual to mean anything.
MIN_OVERLAP_FRACTION = 0.35
# A horizontal shift can only be measured against structure in tan(delta). A
# critical gel's loss tangent is frequency-INDEPENDENT by construction, so its
# alignment objective is flat and every shift fits equally well - the fit is
# degenerate, not zero. Curves whose log10 tan(delta) varies by less than this
# carry no alignment information and must be reported as such.
MIN_TAN_DELTA_STRUCTURE = 0.15


def signature_features(w, Gp, Gpp):
    """Extract regime-discriminating features from the raw spectrum.
    Returns (features dict, allowed candidate name set)."""
    lw = np.log10(w)
    lGp = np.log10(np.clip(Gp, 1e-30, None))
    lGpp = np.log10(np.clip(Gpp, 1e-30, None))

    def local_slope(lx, ly, frac=0.3):
        n = max(2, int(len(lx) * frac))
        return np.polyfit(lx[:n], ly[:n], 1)[0]

    slope_Gp_lo = local_slope(lw, lGp)
    slope_Gpp_lo = local_slope(lw, lGpp)

    n = len(w)
    a, b = n // 3, 2 * n // 3
    lGstar = np.log10(np.sqrt(Gp**2 + Gpp**2))
    mid_exp = np.polyfit(lw[a:b], lGstar[a:b], 1)[0] if b > a + 1 else np.nan

    # --- plateau test ---
    # A genuine entanglement plateau is a region where G' is flat AND well
    # above G'' (loss tangent < 1) that spans a meaningful width in w, AND
    # is bounded on the low-w side by a terminal crossover inside the window.
    # Finite-mode saturation of an unentangled spectrum also flattens G' at
    # the top of the window, so width + a G'' dip separate a real plateau
    # from that artifact.
    tan_d = Gpp / np.clip(Gp, 1e-30, None)
    flat = np.abs(np.gradient(lGp, lw)) < 0.15
    plateau_mask = flat & (tan_d < 1.0)

    dsign = np.diff(np.sign(np.diff(Gpp)))
    max_idx = np.where(dsign < 0)[0] + 1
    min_idx = np.where(dsign > 0)[0] + 1
    n_maxima = len(max_idx)
    has_dip = False
    if n_maxima >= 2 and len(min_idx) >= 1:
        lo, hi = max_idx[0], max_idx[-1]
        has_dip = np.any((min_idx > lo) & (min_idx < hi))

    nedge = max(1, n // 12)
    interior_plateau = plateau_mask.copy()
    interior_plateau[:nedge] = False
    interior_plateau[-nedge:] = False
    if interior_plateau.any():
        idx = np.where(interior_plateau)[0]
        plateau_width = lw[idx].max() - lw[idx].min()
        spectrum_above = idx.max() < (n - nedge - 1)
    else:
        plateau_width, spectrum_above = 0.0, False
    terminal_reached = (slope_Gp_lo > 1.4) and (slope_Gpp_lo > 0.7)
    has_plateau = (plateau_width >= 1.0) and spectrum_above

    # --- sticker / second-shoulder test ---
    # An associating system shows a second G'' maximum (the sticker peak)
    # separated from the terminal peak by an interior dip.
    has_shoulder = (n_maxima >= 2) and has_dip

    # --- network-family features ---
    # A critical gel has a frequency-INDEPENDENT loss tangent; anything with a
    # characteristic time in the window does not. A cured elastomer instead
    # shows a flat G' running to the bottom of the window with tan(delta) << 1.
    td_spread = tan_delta_spread(w, Gp, Gpp)
    lo_flat = np.abs(np.gradient(lGp, lw)) < FLAT_SLOPE_TOL
    n_lo = max(2, len(w) // 3)
    flat_decades_lo = (np.ptp(lw[:n_lo][lo_flat[:n_lo]])
                       if lo_flat[:n_lo].sum() >= 2 else 0.0)
    median_tan_d = float(np.median(tan_d))

    feats = {
        "slope_Gp_lo": slope_Gp_lo,
        "slope_Gpp_lo": slope_Gpp_lo,
        "mid_exp": mid_exp,
        "has_plateau": has_plateau,
        "has_shoulder": has_shoulder,
        "terminal_reached": terminal_reached,
        "tan_delta_spread": td_spread,
        "flat_decades_lo": float(flat_decades_lo),
        "median_tan_delta": median_tan_d,
    }

    # Permissive pre-filter: only hard-discard a model when a robust feature
    # strongly contraindicates it; otherwise keep it and let AICc rank.
    allowed = set(ALL_MODELS.keys())

    wide_plateau = plateau_width >= 1.0
    confident_entangled = wide_plateau and terminal_reached and spectrum_above

    if confident_entangled:
        allowed -= {"zimm", "rouse_screened"}
    if not wide_plateau:
        allowed.discard("reptation")
    if not has_shoulder:
        allowed -= {"sticky_rouse", "sticky_reptation"}
    # A permanently crosslinked network cannot flow: terminal relaxation inside
    # the window rules out both network classes. This is the only robust
    # contraindication for them - everything else is left to AICc.
    if terminal_reached:
        allowed -= NETWORK_CLASSES
    if not allowed:
        allowed = set(ALL_MODELS.keys())
    return feats, allowed


def _log_residual(theta, forward, w, Gp, Gpp):
    try:
        mp, mpp = forward(w, theta)
    except Exception:
        return 1e6
    mp = np.clip(mp, 1e-30, None)
    mpp = np.clip(mpp, 1e-30, None)
    r = np.concatenate([
        np.log10(mp) - np.log10(np.clip(Gp, 1e-30, None)),
        np.log10(mpp) - np.log10(np.clip(Gpp, 1e-30, None)),
    ])
    sse = np.sum(r * r)
    return sse if np.isfinite(sse) else 1e6


def _loss_tangent_curve(w, Gp, Gpp):
    """(log10 omega, log10 tan delta) for one spectrum.

    tan(delta) is a ratio of moduli, so the vertical shift factor b_T cancels
    exactly. Aligning stacks on tan(delta) therefore needs only a horizontal
    shift - no simultaneous b_T fit, and no assumption about how the plateau
    scales with temperature.
    """
    w = np.asarray(w, float)
    tan_d = np.asarray(Gpp, float) / np.clip(np.asarray(Gp, float), 1e-30, None)
    return np.log10(w), np.log10(np.clip(tan_d, 1e-30, None))


def _alignment_residual(lw_ref, ltd_ref, lw, ltd, shift):
    """Mean squared log tan(delta) mismatch after shifting one curve by `shift`
    decades in omega. Returns inf when the curves barely overlap."""
    lws = lw + shift
    lo, hi = max(lw_ref.min(), lws.min()), min(lw_ref.max(), lws.max())
    if hi <= lo:
        return np.inf
    if (hi - lo) < MIN_OVERLAP_FRACTION * min(np.ptp(lw_ref), np.ptp(lws)):
        return np.inf
    grid = np.linspace(lo, hi, 40)
    a = np.interp(grid, lw_ref, ltd_ref)
    b = np.interp(grid, lws, ltd)
    return float(np.mean((a - b) ** 2))


def shift_factor(ref, cur, max_decades=SHIFT_SEARCH_DECADES, n_scan=401):
    """Horizontal shift log10(a_T), in decades, aligning `cur` onto `ref`.

    Each argument is a (omega, Gp, Gpp) triple. Coarse scan plus a parabolic
    refinement - the objective is a smooth 1-D curve, so this is both cheaper
    and more robust than a gradient fit that can stall on a flat tan(delta).
    Returns (shift_decades, residual); the shift is NaN when the curves never
    overlap enough to compare, OR when tan(delta) is too flat to align against
    - a critical gel has a frequency-independent loss tangent, so every shift
    fits it equally well and any single answer would be an artifact of the
    search grid rather than a measurement.
    """
    lw_ref, ltd_ref = _loss_tangent_curve(*ref)
    lw, ltd = _loss_tangent_curve(*cur)

    if (np.ptp(ltd_ref) < MIN_TAN_DELTA_STRUCTURE
            or np.ptp(ltd) < MIN_TAN_DELTA_STRUCTURE):
        return float("nan"), float("inf")

    grid = np.linspace(-max_decades, max_decades, n_scan)
    costs = np.array([_alignment_residual(lw_ref, ltd_ref, lw, ltd, s) for s in grid])
    if not np.isfinite(costs).any():
        return float("nan"), float("inf")

    k = int(np.argmin(costs))
    best, cost = float(grid[k]), float(costs[k])
    # parabolic refinement against the two neighbours, when they are usable
    if 0 < k < len(grid) - 1:
        c0, c1, c2 = costs[k - 1], costs[k], costs[k + 1]
        if np.isfinite(c0) and np.isfinite(c2):
            denom = c0 - 2 * c1 + c2
            if denom > 0:
                step = 0.5 * (c0 - c2) / denom
                if abs(step) <= 1.0:
                    best += step * (grid[1] - grid[0])
    return best, cost


def resolve_melt_vs_network(stack):
    """Decide melt vs permanent network from a temperature stack.

    `stack` is a sequence of dicts with keys omega, Gp, Gpp and T_K (as
    produced by rheofp.io.data). Two independent pieces of evidence, in
    priority order:

      1. Terminal relaxation observed at ANY temperature -> melt. A permanent
         network cannot flow at any temperature, so a single observation of
         G' ~ omega^2 settles it outright.
      2. Otherwise, how far the spectrum SHIFTS across the stack. Heating walks
         a melt's relaxation spectrum along the frequency axis; a crosslinked
         network's plateau stays put. A span of at least SHIFT_DECADES_MIN
         decades means the spectrum is moving, so it is a melt.

    Returns a dict with the verdict ("melt", "network" or "ambiguous"), the
    measured shift span, and the per-temperature detail behind it.
    """
    entries = []
    for s in stack:
        T = float(s.get("T_K", np.nan))
        feats, _ = signature_features(np.asarray(s["omega"], float),
                                      np.asarray(s["Gp"], float),
                                      np.asarray(s["Gpp"], float))
        entries.append({"T_K": T, "terminal_reached": bool(feats["terminal_reached"]),
                        "spectrum": (s["omega"], s["Gp"], s["Gpp"])})

    n_T = len({e["T_K"] for e in entries if np.isfinite(e["T_K"])})
    terminal_at = [e["T_K"] for e in entries if e["terminal_reached"]]

    if terminal_at:
        return {"verdict": "melt", "reason": "terminal relaxation observed in window",
                "shift_decades": float("nan"), "terminal_at": terminal_at,
                "n_temperatures": n_T, "shifts": []}

    if n_T < MIN_STACK_TEMPERATURES:
        return {"verdict": "ambiguous",
                "reason": f"needs >= {MIN_STACK_TEMPERATURES} temperatures, got {n_T}",
                "shift_decades": float("nan"), "terminal_at": [],
                "n_temperatures": n_T, "shifts": []}

    # Align every curve onto the coldest one; the span of shifts is how far the
    # spectrum travels across the stack.
    known = sorted((e for e in entries if np.isfinite(e["T_K"])), key=lambda e: e["T_K"])
    ref = known[0]["spectrum"]
    shifts = []
    for e in known:
        s, cost = shift_factor(ref, e["spectrum"])
        shifts.append({"T_K": e["T_K"], "shift_decades": s, "residual": cost})

    finite = [d["shift_decades"] for d in shifts if np.isfinite(d["shift_decades"])]
    if len(finite) < MIN_STACK_TEMPERATURES:
        # Either the windows barely overlap, or tan(delta) is too flat to align
        # against. The latter is the critical-gel case: its loss tangent is
        # frequency-independent, so no shift is measurable even in principle.
        flat = any(np.ptp(_loss_tangent_curve(*e["spectrum"])[1])
                   < MIN_TAN_DELTA_STRUCTURE for e in known)
        return {"verdict": "ambiguous",
                "reason": ("loss tangent is frequency-independent - no feature "
                           "to measure a temperature shift against"
                           if flat else
                           "curves do not overlap enough to align"),
                "shift_decades": float("nan"), "terminal_at": [],
                "n_temperatures": n_T, "shifts": shifts}

    span = float(np.ptp(finite))
    moving = span >= SHIFT_DECADES_MIN
    return {
        "verdict": "melt" if moving else "network",
        "reason": (f"spectrum shifts {span:.2f} decades across the stack"
                   if moving else
                   f"spectrum is T-invariant ({span:.2f} decades, "
                   f"under {SHIFT_DECADES_MIN})"),
        "shift_decades": span,
        "terminal_at": [],
        "n_temperatures": n_T,
        "shifts": shifts,
    }


def melt_rubber_ambiguous(feats, best_name, n_temperatures=1):
    """Is a cured-elastomer call actually indistinguishable from a melt?

    A permanent network and a high-Mw entangled melt whose terminal time lies
    below the measured window produce the same flat plateau. No single-curve
    statistic separates them - the melt's missing terminal relaxation is
    missing evidence, not evidence of absence - so the honest answer from one
    curve is always "ambiguous". A temperature stack resolves it (heating
    walks a melt's terminal relaxation into the window; a network's plateau
    stays put), which is why n_temperatures, not a flatness threshold, is what
    lifts the abstention.

    feats["flat_decades_lo"] is reported alongside so the caller can see how
    much plateau the call rests on, but it deliberately does NOT gate the
    abstention: more decades of flatness raise confidence without ever
    reaching proof.
    """
    if best_name != "cured_elastomer":
        return False
    if feats["terminal_reached"]:
        return False
    return n_temperatures < MIN_STACK_TEMPERATURES


def fit_model(name, w, Gp, Gpp, seed=RNG_SEED, n_restarts=N_RESTARTS):
    forward, p0, bnds, k = ALL_MODELS[name]
    best = multi_restart_fit(
        lambda theta: _log_residual(theta, forward, w, Gp, Gpp),
        bnds, n_restarts, seed=seed, x0_first=p0,
    )
    n_data = 2 * len(w)
    sse = best.fun
    aic = n_data * np.log(sse / n_data) + 2 * k
    bic = n_data * np.log(sse / n_data) + k * np.log(n_data)
    aicc = aic + (2 * k * (k + 1)) / max(1, (n_data - k - 1))
    rms = np.sqrt(sse / n_data)
    return {
        "name": name, "params": best.x, "sse": sse,
        "aic": aic, "bic": bic, "aicc": aicc, "rms_log": rms, "k": k,
    }


def identify(w, Gp, Gpp, floor_chi2=FLOOR_CHI2, seed=RNG_SEED, n_restarts=N_RESTARTS,
             n_temperatures=1):
    """Full pipeline. Returns ranked results + features + confidence.

    n_temperatures: how many temperatures the sample was measured at. Only a
    stack (>= MIN_STACK_TEMPERATURES) can resolve the melt-vs-rubber
    ambiguity; with a single curve a cured-elastomer call is returned with
    abstain=True.
    """
    feats, allowed = signature_features(w, Gp, Gpp)

    results = [fit_model(name, w, Gp, Gpp, seed=seed, n_restarts=n_restarts)
               for name in ALL_MODELS if name in allowed]
    results.sort(key=lambda r: r["aicc"])

    aicc_min = results[0]["aicc"]
    for r in results:
        r["delta"] = r["aicc"] - aicc_min
    Z = sum(np.exp(-0.5 * r["delta"]) for r in results)
    for r in results:
        r["weight"] = np.exp(-0.5 * r["delta"]) / Z

    best = results[0]
    low_confidence = best["rms_log"] > floor_chi2
    abstain = melt_rubber_ambiguous(feats, best["name"], n_temperatures)
    return {
        "features": feats,
        "allowed": sorted(allowed),
        "ranking": results,
        "best": best["name"],
        "best_weight": best["weight"],
        "best_rms_log": best["rms_log"],
        "low_confidence": low_confidence,
        # Head 1 abstains; head 2 (best) always still emits a model, per the
        # frozen two-head architecture.
        "abstain": abstain,
        "abstain_reason": ("cured elastomer vs high-Mw melt: no terminal "
                           "relaxation in window and no temperature stack"
                           if abstain else None),
    }


def identify_stack(stack, floor_chi2=FLOOR_CHI2, seed=RNG_SEED, n_restarts=N_RESTARTS):
    """Identify from a temperature stack - the architecture's native input.

    `stack` is a sequence of dicts with omega, Gp, Gpp and T_K. Runs the
    single-curve pipeline on the coldest curve (its window is the one most
    likely to hide a melt's terminal relaxation, so it is the hardest case),
    then lets resolve_melt_vs_network() settle the melt-vs-rubber ambiguity
    that a single curve cannot.

    The stack only ever LIFTS an abstention or overturns a class it can
    disprove; it never invents confidence the single-curve fit did not have.
    """
    known = [s for s in stack if np.isfinite(float(s.get("T_K", np.nan)))]
    ordered = sorted(known, key=lambda s: float(s["T_K"])) or list(stack)
    ref = ordered[0]

    out = identify(ref["omega"], ref["Gp"], ref["Gpp"], floor_chi2=floor_chi2,
                   seed=seed, n_restarts=n_restarts,
                   n_temperatures=len({float(s.get("T_K", np.nan)) for s in known}))
    resolution = resolve_melt_vs_network(stack)
    out["stack"] = resolution

    if out["best"] in NETWORK_CLASSES and resolution["verdict"] == "melt":
        # The stack disproves the single-curve call: a permanent network cannot
        # flow, and cannot walk along the frequency axis with temperature.
        out["abstain"] = True
        out["abstain_reason"] = (
            "temperature stack contradicts the network fit - "
            + resolution["reason"])
    elif out["best"] == "cured_elastomer" and resolution["verdict"] == "network":
        out["abstain"] = False
        out["abstain_reason"] = None
    elif resolution["verdict"] == "ambiguous" and out["best"] == "cured_elastomer":
        out["abstain"] = True
        out["abstain_reason"] = ("cured elastomer vs high-Mw melt: "
                                 + resolution["reason"])
    return out
