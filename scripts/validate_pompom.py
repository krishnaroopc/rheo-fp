"""Validation script for rheofp.models.pompom (from xpp_pompom_fit.ipynb).

*** NOT YET VALIDATED ***
Awaiting real Pivokonsky, Zatloukal & Filip (2006, J. Non-Newt. Fluid Mech.
135, 58) spectrum tables for two LDPE melts at 200 C. This script currently
verifies only against a substitute Verbeeten et al. (2001) Table III dataset
(Lupolen 1810H, 150 C), reconstructed from its published Maxwell spectrum.
Treat any result here as provisional.

Run directly: python scripts/validate_pompom.py
"""
import numpy as np
import matplotlib.pyplot as plt

from rheofp.models.maxwell import maxwell_spectrum, fit_maxwell
from rheofp.models.pompom import build_xpp_table

# Verbeeten (2001) Table III - Lupolen 1810H LDPE, T_r = 150 C. Exact as
# published; nu_i = 2/q_i throughout.
#  i   G0_i (Pa)          lambda_0b_i (s)    q_i  lambda_0b/lambda_0s  alpha_i
PUB = [
    (2.1662e+04, 1.0000e-01, 1, 3.5, 0.350),
    (9.9545e+03, 6.3096e-01, 2, 3.0, 0.300),
    (3.7775e+03, 3.9811e+00, 3, 2.8, 0.250),
    (9.6955e+02, 2.5119e+01, 7, 2.8, 0.200),
    (1.1834e+02, 1.5849e+02, 8, 1.5, 0.100),
    (4.1614e+00, 1.0000e+03, 37, 1.5, 0.005),
]

N_MODES = 6
N_RESTARTS = 8


def main():
    g_pub = np.array([r[0] for r in PUB])
    tau_pub = np.array([r[1] for r in PUB])
    q_pub = np.array([r[2] for r in PUB])
    ratio_pub = np.array([r[3] for r in PUB])
    alpha_pub = np.array([r[4] for r in PUB])

    print("Verbeeten (2001) Table III - Lupolen 1810H, 150 C (substitute dataset)")
    print(f"  Modes    : {len(g_pub)}")
    print(f"  GN0      : {g_pub.sum():.4g} Pa")

    omega_ref = np.geomspace(1e-3, 1e2, 50)
    Gp_ref, Gpp_ref = maxwell_spectrum(omega_ref, g_pub, tau_pub)

    fit = fit_maxwell(omega_ref, Gp_ref, Gpp_ref, n_modes=N_MODES, n_restarts=N_RESTARTS, seed=42)
    g_fit, tau_fit = fit["G"], fit["tau"]
    print(f"\nFit converged={fit['success']}  cost={fit['cost']:.3e}")

    w_test = np.geomspace(1e-3, 1e2, 200)
    Gp_fit_v, Gpp_fit_v = maxwell_spectrum(w_test, g_fit, tau_fit)
    Gp_pub_v, Gpp_pub_v = maxwell_spectrum(w_test, g_pub, tau_pub)
    err_gp = np.abs(np.log10(Gp_fit_v) - np.log10(Gp_pub_v)).mean()
    err_gpp = np.abs(np.log10(Gpp_fit_v) - np.log10(Gpp_pub_v)).mean()
    print(f"Mean |log10 error| in G'  : {err_gp:.4f}  decades")
    print(f"Mean |log10 error| in G'' : {err_gpp:.4f}  decades")
    if max(err_gp, err_gpp) < 0.05:
        print("PASS - LVE fit recovers published spectrum to < 0.05 decades")
    else:
        print("WARN - residual > 0.05 decades; increase N_RESTARTS or check bounds")

    rows = build_xpp_table("Lupolen 1810H", g_fit, tau_fit, use_published=True,
                            pub_q=q_pub, pub_ratio=ratio_pub, pub_alpha=alpha_pub)
    print("\nXPP parameter table (verification mode):")
    for row in rows:
        print(row)

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.loglog(omega_ref, Gp_ref, "o", ms=6, mfc="w", mew=1.4, label="G' data")
    ax.loglog(omega_ref, Gpp_ref, "^", ms=6, mfc="w", mew=1.4, label="G'' data")
    ax.loglog(w_test, Gp_fit_v, "-", lw=2.0, label="G' fit")
    ax.loglog(w_test, Gpp_fit_v, "--", lw=2.0, label="G'' fit")
    ax.set_xlabel(r"$\omega$ (rad/s)")
    ax.set_ylabel("G', G'' (Pa)")
    ax.set_title("XPP LVE fit - NOT YET VALIDATED (substitute dataset)")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", ls=":", alpha=0.4)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
