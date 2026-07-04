"""XPP (eXtended Pom-Pom) linear-viscoelastic fitting for branched melts.

NOT YET VALIDATED: awaiting real Pivokonsky, Zatloukal & Filip (2006,
J. Non-Newt. Fluid Mech. 135, 58) spectrum tables for the two LDPE melts at
200 C. Currently verifies only against a substitute Verbeeten et al. (2001)
Table III dataset (Lupolen 1810H, 150 C), reconstructed from its published
Maxwell spectrum. Treat any fit through this module as provisional until
real Pivokonsky data is wired in (see CLAUDE.md).

In the linear regime the XPP model reduces exactly to a multimode Maxwell
spectrum, so forward/fit logic reuses rheofp.models.maxwell rather than the
notebook's local maxwell_Gstar/fit_maxwell duplicates (confirmed identical
formula by diff).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def load_samples(filepath, sheet, samples, omega_hz=False):
    """Load {sample: dict(omega, Gp, Gpp)} from an xlsx sheet.

    Column 0 = omega (rad/s, or s^-1 if omega_hz=False per this notebook's
    original convention); columns matched by substring "<sample> G'" /
    "<sample> G''".
    """
    df = pd.read_excel(filepath, sheet_name=sheet, header=0)
    cols = list(df.columns)
    omega_raw = df.iloc[:, 0].dropna().to_numpy(float)
    omega_col = omega_raw * (2 * np.pi if omega_hz else 1.0)
    data = {}
    for sname in samples:
        gp_col = next((c for c in cols if sname in str(c)
                       and "G'" in str(c) and "''" not in str(c)), None)
        gpp_col = next((c for c in cols if sname in str(c) and "G''" in str(c)), None)
        if gp_col is None or gpp_col is None:
            continue
        gp = df[gp_col].dropna().to_numpy(float)
        gpp = df[gpp_col].dropna().to_numpy(float)
        n = min(len(omega_col), len(gp), len(gpp))
        data[sname] = dict(omega=omega_col[:n], Gp=gp[:n], Gpp=gpp[:n])
    return data


def build_xpp_table(sname, g_fit, tau_fit, nonlinear_params=None,
                     use_published=False, pub_q=None, pub_ratio=None, pub_alpha=None):
    """Combine fitted linear params {G0_i, tau_0b_i} with nonlinear params
    {q_i, tau_0b_i/tau_0s_i, alpha_i} into the full XPP parameter table.

    nonlinear_params: optional list of (q, ratio, alpha) tuples, one per mode.
    use_published + pub_*: verification-mode override using known-correct
    published values instead of guessed defaults.
    """
    N = len(g_fit)
    rows = []
    for i in range(N):
        if use_published:
            q, ratio, alpha = int(pub_q[i]), float(pub_ratio[i]), float(pub_alpha[i])
        elif nonlinear_params is not None and i < len(nonlinear_params):
            q, ratio, alpha = nonlinear_params[i]
        else:
            # defaults: q ramps 1..5, ratio=3, alpha=0.1/q
            q = max(1, min(5, 1 + i))
            ratio = 3.0
            alpha = round(0.1 / q, 3)

        tau_s = tau_fit[i] / ratio
        rows.append({
            "Mode": i + 1,
            "G0_i (Pa)": g_fit[i],
            "tau_0b_i (s)": tau_fit[i],
            "q_i": q,
            "nu_i = 2/q_i": 2 / q,
            "tau_0b/tau_0s": ratio,
            "tau_0s_i (s)": tau_s,
            "alpha_i": alpha,
        })
    return rows
