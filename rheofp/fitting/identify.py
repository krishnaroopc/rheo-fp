"""Regime-aware model identification for polymer-solution SAOS spectra.

Canonical source: solution_identifier.ipynb. Pipeline: permissive
signature-feature pre-filter -> multi-restart L-BFGS-B fit in log space ->
AICc ranking with Akaike weights -> none-of-the-above floor via FLOOR_CHI2.
Lesson learned in the original notebook: aggressive pre-filter pruning caused
misclassification; keep the pre-filter permissive and let AICc resolve.
"""
from __future__ import annotations

import numpy as np

from rheofp.models.solutions import MODELS
from rheofp.fitting.optimize import multi_restart_fit

N_RESTARTS = 12
FLOOR_CHI2 = 0.15  # normalized RMS log-residual above which we flag low confidence
RNG_SEED = 0


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

    feats = {
        "slope_Gp_lo": slope_Gp_lo,
        "slope_Gpp_lo": slope_Gpp_lo,
        "mid_exp": mid_exp,
        "has_plateau": has_plateau,
        "has_shoulder": has_shoulder,
        "terminal_reached": terminal_reached,
    }

    # Permissive pre-filter: only hard-discard a model when a robust feature
    # strongly contraindicates it; otherwise keep it and let AICc rank.
    allowed = set(MODELS.keys())

    wide_plateau = plateau_width >= 1.0
    confident_entangled = wide_plateau and terminal_reached and spectrum_above

    if confident_entangled:
        allowed -= {"zimm", "rouse_screened"}
    if not wide_plateau:
        allowed.discard("reptation")
    if not has_shoulder:
        allowed -= {"sticky_rouse", "sticky_reptation"}
    if not allowed:
        allowed = set(MODELS.keys())
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


def fit_model(name, w, Gp, Gpp, seed=RNG_SEED, n_restarts=N_RESTARTS):
    forward, p0, bnds, k = MODELS[name]
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


def identify(w, Gp, Gpp, floor_chi2=FLOOR_CHI2, seed=RNG_SEED, n_restarts=N_RESTARTS):
    """Full pipeline. Returns ranked results + features + confidence."""
    feats, allowed = signature_features(w, Gp, Gpp)

    results = [fit_model(name, w, Gp, Gpp, seed=seed, n_restarts=n_restarts)
               for name in MODELS if name in allowed]
    results.sort(key=lambda r: r["aicc"])

    aicc_min = results[0]["aicc"]
    for r in results:
        r["delta"] = r["aicc"] - aicc_min
    Z = sum(np.exp(-0.5 * r["delta"]) for r in results)
    for r in results:
        r["weight"] = np.exp(-0.5 * r["delta"]) / Z

    best = results[0]
    low_confidence = best["rms_log"] > floor_chi2
    return {
        "features": feats,
        "allowed": sorted(allowed),
        "ranking": results,
        "best": best["name"],
        "best_weight": best["weight"],
        "best_rms_log": best["rms_log"],
        "low_confidence": low_confidence,
    }
