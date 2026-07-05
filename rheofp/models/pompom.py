"""XPP (eXtended Pom-Pom) linear-viscoelastic fitting for branched melts.

LVE VALIDATED against the real target: Pivokonsky, Zatloukal & Filip (2006,
J. Non-Newt. Fluid Mech. 135, 58), two LDPE melts at 200 C (data/pivo2006.npz,
see scripts/validate_pompom.py and tests/test_pompom.py). fit_maxwell
recovers both melts' measured G'/G'' to < 0.02 decades mean log10 error.

Scope: only the linear regime is validated (XPP reduces exactly to multimode
Maxwell in LVE, so forward/fit logic reuses rheofp.models.maxwell rather than
the notebook's local maxwell_Gstar/fit_maxwell duplicates - confirmed
identical formula by diff). The paper's nonlinear parameters (q_i,
lambda_b/lambda_s, alpha_i) were fit against nonlinear flow data
(extensional/shear viscosity, normal stress coefficients) that this repo does
not have digitized; build_xpp_table() assembles them from the paper's Tables
2/3 but true nonlinear-XPP flow prediction is not validated here.

Classifier scope decision: the product only ever ingests SAOS (LVE) data, and
XPP is indistinguishable from a generic multimode Maxwell fit in that regime
(its q_i/alpha_i/lambda_b/lambda_s are underdetermined by LVE data alone - the
paper itself needed nonlinear flow curves to pin them down). So this module is
NOT wired into rheofp.fitting.identify's model bank and is not a classifier
output class; branched melts are represented for classification purposes via
rheofp.models.maxwell.branched_spectrum (hierarchical double-reptation)
instead. This module stays as a validated reference/tool, e.g. for future
nonlinear-data workflows, not part of the SAOS-only pipeline.
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
