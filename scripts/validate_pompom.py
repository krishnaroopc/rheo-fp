"""Validation script for rheofp.models.pompom (from xpp_pompom_fit.ipynb).

Verifies against the real target dataset: Pivokonsky, Zatloukal & Filip
(2006, J. Non-Newt. Fluid Mech. 135, 58), two LDPE melts at 200 C -
LDPE Escorene LD165BW1 ("E") and LDPE Bralen RB0323 ("B"). G'/G'' spectra
(their Fig. 2) are in data/pivo2006.npz; the published 10-mode Maxwell
spectrum and XPP nonlinear parameters (their Tables 2 and 3) are transcribed
below.

Scope note: only the *linear* regime is validated here (XPP reduces exactly
to multimode Maxwell in LVE - see rheofp/models/pompom.py docstring). The
paper's nonlinear parameters (q_i, lambda_b/lambda_s, alpha_i) were fit
against nonlinear flow data (extensional/shear viscosity, normal stress
coefficients - their Figs. 3-9), which this repo does not have digitized.
This script therefore checks (1) that fit_maxwell recovers the real measured
G'/G'' curves for both melts, and (2) that build_xpp_table() correctly
assembles the published nonlinear parameters onto those fitted modes. It does
NOT validate nonlinear XPP flow predictions.

Run directly: python scripts/validate_pompom.py
"""
import numpy as np
import matplotlib.pyplot as plt

from rheofp.io.data import load_npz
from rheofp.models.maxwell import maxwell_spectrum, fit_maxwell
from rheofp.models.pompom import build_xpp_table

# Table 2 - LDPE Escorene LD165BW1, 200 C. Columns: lambda_b,i (s), G_i (Pa),
# lambda_b,i/lambda_s,i, q_i, alpha_i (= 0.5/q_i, the paper's final choice).
TABLE2_ESCORENE = [
    (0.00154,   109430.0,   2.4, 1, 0.5000),
    (0.00633,    37352.6,   2.2, 1, 0.5000),
    (0.02602,    32409.3,   2.2, 2, 0.2500),
    (0.10686,    15251.2,   1.8, 3, 0.1667),
    (0.43891,    11081.2,   1.8, 4, 0.1250),
    (1.80281,     4835.09,  1.3, 5, 0.1000),
    (7.40488,     1986.65,  1.3, 6, 0.0833),
    (30.4149,      494.690, 1.3, 6, 0.0833),
    (124.927,      110.156, 1.2, 6, 0.0833),
    (513.127,       33.3765,1.2, 7, 0.0714),
]

# Table 3 - LDPE Bralen RB0323, 200 C. Same column layout.
TABLE3_BRALEN = [
    (0.00134,   121440.0,  3.4, 1, 0.5000),
    (0.0052,     35292.2,  2.8, 1, 0.5000),
    (0.02015,    33442.9,  2.6, 2, 0.2500),
    (0.07804,    19480.3,  1.8, 3, 0.1667),
    (0.3023,     11923.4,  1.8, 5, 0.1000),
    (1.17104,     5763.63, 1.3, 7, 0.0714),
    (4.53626,     2574.63, 1.3, 8, 0.0625),
    (17.5722,      800.865,1.2, 8, 0.0625),
    (68.0695,      213.412,1.1, 9, 0.0556),
    (263.681,       34.6864,1.1,9, 0.0556),
]

SAMPLES = {
    "E": ("LDPE Escorene LD165BW1", TABLE2_ESCORENE),
    "B": ("LDPE Bralen RB0323", TABLE3_BRALEN),
}

N_RESTARTS = 12
DECADE_TOL = 0.10  # looser than the substitute-dataset check: real digitized data is noisier


def main():
    dataset = load_npz("data/pivo2006.npz")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    all_pass = True

    for ax, (sample, (label, table)) in zip(axes, SAMPLES.items()):
        d = dataset[sample]
        omega, Gp_data, Gpp_data = d["omega"], d["Gp"], d["Gpp"]
        n_modes = len(table)

        print(f"\n=== {label} ({sample}) - {len(omega)} points, {n_modes} modes ===")
        fit = fit_maxwell(omega, Gp_data, Gpp_data, n_modes=n_modes,
                           n_restarts=N_RESTARTS, seed=42)
        g_fit, tau_fit = fit["G"], fit["tau"]
        print(f"Fit converged={fit['success']}  cost={fit['cost']:.3e}")

        Gp_fit, Gpp_fit = maxwell_spectrum(omega, g_fit, tau_fit)
        err_gp = np.abs(np.log10(Gp_fit) - np.log10(Gp_data)).mean()
        err_gpp = np.abs(np.log10(Gpp_fit) - np.log10(Gpp_data)).mean()
        print(f"Mean |log10 error| in G'  vs real data: {err_gp:.4f} decades")
        print(f"Mean |log10 error| in G'' vs real data: {err_gpp:.4f} decades")
        sample_pass = max(err_gp, err_gpp) < DECADE_TOL
        all_pass &= sample_pass
        print("PASS" if sample_pass else "WARN",
              f"- threshold {DECADE_TOL} decades")

        g_pub = np.array([r[1] for r in table])
        tau_pub = np.array([r[0] for r in table])
        q_pub = np.array([r[3] for r in table])
        ratio_pub = np.array([r[2] for r in table])
        alpha_pub = np.array([r[4] for r in table])
        rows = build_xpp_table(label, g_fit, tau_fit, use_published=True,
                                pub_q=q_pub, pub_ratio=ratio_pub, pub_alpha=alpha_pub)
        print("XPP parameter table (fitted G/tau + published nonlinear params):")
        for row in rows:
            print(row)

        w_plot = np.geomspace(omega.min(), omega.max(), 200)
        Gp_plot, Gpp_plot = maxwell_spectrum(w_plot, g_fit, tau_fit)
        Gp_pub, Gpp_pub = maxwell_spectrum(w_plot, g_pub, tau_pub)
        ax.loglog(omega, Gp_data, "o", ms=5, mfc="w", mew=1.2, label="G' data")
        ax.loglog(omega, Gpp_data, "^", ms=5, mfc="w", mew=1.2, label="G'' data")
        ax.loglog(w_plot, Gp_plot, "-", lw=2.0, label="G' fit (this repo)")
        ax.loglog(w_plot, Gpp_plot, "--", lw=2.0, label="G'' fit (this repo)")
        ax.loglog(w_plot, Gp_pub, ":", lw=1.2, color="k", label="G' published Maxwell")
        ax.loglog(w_plot, Gpp_pub, "-.", lw=1.2, color="k", label="G'' published Maxwell")
        ax.set_xlabel(r"$\omega$ (rad/s)")
        ax.set_ylabel("G', G'' (Pa)")
        ax.set_title(f"{label} - {'PASS' if sample_pass else 'WARN'}")
        ax.legend(fontsize=7)
        ax.grid(True, which="both", ls=":", alpha=0.4)

    print(f"\n{'ALL PASS' if all_pass else 'SOME WARN'} - real Pivokonsky (2006) LVE validation")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
