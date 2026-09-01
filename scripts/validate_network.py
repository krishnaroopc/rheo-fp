"""Validation script for rheofp.models.network (elastomer + critical gel).

  1. Planted-parameter recovery for both classes - the cured elastomer
     (3-param fractional Kelvin-Voigt) and the critical gel (2-param bare
     springpot), including the Tixier exponent range u = 0.5-0.75.
  2. Classifier routing - identify() picks the right class from planted
     spectra, and abstains on a single cured-elastomer curve.
  3. Melt counterexample - Likhtman-McLeish (2002) PS 6 with the terminal
     region truncated away, the classic way to make an entangled melt
     impersonate a rubber. The network classes must not steal it.
  4. REAL cured-elastomer data - Darby et al. (2022) Fig. 1a, three
     commercial silicones (Sylgard 184, Solaris, Ecoflex 00-30) digitized
     into data/darby2022.npz. Checks that fit_chasset_thirion recovers a
     G_inf consistent with the paper's tabulated low-frequency modulus
     (their Table 1) and that identify() routes each to cured_elastomer.
  5. REAL critical-gel data - Tixier et al. (2004) Fig. 2/4, a near-sol-gel-
     threshold end-linked PDMS network digitized into data/tixier2004.npz.
     Checks that fit_critical_gel recovers an exponent u in Tixier's measured
     range (0.69-0.75, NOT 0.5) and that identify() routes it to critical_gel.

Run directly: python scripts/validate_network.py
"""
import numpy as np
import matplotlib.pyplot as plt

from rheofp.io.data import load_npz
from rheofp.models.network import (
    chasset_thirion_spectrum, critical_gel_spectrum,
    fit_chasset_thirion, fit_critical_gel,
)
from rheofp.fitting.identify import identify, NETWORK_CLASSES

W = np.logspace(-3, 4, 60)
N_RESTARTS = 24
REL_TOL = 0.05  # planted-parameter recovery tolerance (fraction)

# Planted cases: (label, G_inf, c, m). G_inf = 0 marks a critical gel.
CURED_CASES = [
    ("cured elastomer (stiff)", 1.0e6, 2.0e4, 0.20),
    ("cured elastomer (weak)",  1.0e3, 5.0e3, 0.50),
]
GEL_CASES = [
    ("critical gel u=0.50 (Winter-Chambon)", 1.0e4, 0.50),
    ("critical gel u=0.69 (Tixier system I)", 3.0e2, 0.69),
    ("critical gel u=0.75 (Tixier system III)", 3.0e2, 0.75),
]

# Low-frequency cutoffs applied to the melt, hiding progressively more of the
# terminal region.
MELT_CUTOFFS = [1e-5, 1e-2, 1e-1, 1e0]

# Darby et al. (2022) Table 1: low-frequency (0.01 rad/s) shear storage
# modulus, Pa. The digitized Fig. 1a curves only reach down to 0.1 rad/s, so
# these are an out-of-window anchor - fitted G_inf should land near them, but
# an exact match is not expected (esp. for the soft, high-sol-fraction EF).
DARBY_TABLE1_PA = {
    "SY184_10-1": 620e3,
    "Solaris_1-1": 120e3,
    "EF0030_1-1": 27e3,
}
DARBY_GINF_TOL = 0.35  # fractional; loose - see the module/litreview caveats


def _rel(a, b):
    return abs(a - b) / abs(b)


def main():
    all_pass = True
    fig, axes = plt.subplots(1, 5, figsize=(23, 4.5))

    # --- 1a. cured elastomer recovery ---
    print("=== Planted-parameter recovery: cured elastomer ===")
    for label, G_inf, c, m in CURED_CASES:
        Gp, Gpp = chasset_thirion_spectrum(W, G_inf, c, m)
        fit = fit_chasset_thirion(W, Gp, Gpp, n_restarts=N_RESTARTS, seed=1)
        errs = [_rel(fit["G_inf"], G_inf), _rel(fit["c"], c), _rel(fit["m"], m)]
        ok = max(errs) < REL_TOL
        all_pass &= ok
        print(f"{'PASS' if ok else 'FAIL'} {label}: "
              f"G_inf {fit['G_inf']:.4g} (planted {G_inf:g}), "
              f"c {fit['c']:.4g} (planted {c:g}), "
              f"m {fit['m']:.4f} (planted {m:g}) | max rel err {max(errs):.2e}")
        axes[0].loglog(W, Gp, "-", lw=2, label=f"G' {label}")
        axes[0].loglog(W, Gpp, "--", lw=1.5, label=f"G'' {label}")

    # --- 1b. critical gel recovery ---
    print("\n=== Planted-parameter recovery: critical gel ===")
    for label, c, u in GEL_CASES:
        Gp, Gpp = critical_gel_spectrum(W, c, u)
        fit = fit_critical_gel(W, Gp, Gpp, n_restarts=N_RESTARTS, seed=3)
        errs = [_rel(fit["c"], c), _rel(fit["u"], u)]
        ok = max(errs) < REL_TOL
        all_pass &= ok
        tan_d = np.tan(np.pi * u / 2.0)
        print(f"{'PASS' if ok else 'FAIL'} {label}: "
              f"c {fit['c']:.4g} (planted {c:g}), u {fit['u']:.4f} "
              f"(planted {u:g}) | tan(delta) = {tan_d:.3f} flat in omega")
        axes[1].loglog(W, Gp, "-", lw=2, label=f"G' u={u}")
        axes[1].loglog(W, Gpp, "--", lw=1.5, label=f"G'' u={u}")

    # --- 2. classifier routing + abstention ---
    print("\n=== Classifier routing ===")
    Gp, Gpp = chasset_thirion_spectrum(W, 1.0e6, 2.0e4, 0.20)
    out1 = identify(W, Gp, Gpp)
    out4 = identify(W, Gp, Gpp, n_temperatures=4)
    ok = (out1["best"] == "cured_elastomer" and out1["abstain"]
          and not out4["abstain"])
    all_pass &= ok
    print(f"{'PASS' if ok else 'FAIL'} cured elastomer -> best={out1['best']} "
          f"(weight {out1['best_weight']:.3f})")
    print(f"     1 curve : abstain={out1['abstain']} <- {out1['abstain_reason']}")
    print(f"     T-stack : abstain={out4['abstain']} (4 temperatures)")
    for label, c, u in GEL_CASES:
        Gp, Gpp = critical_gel_spectrum(W, c, u)
        out = identify(W, Gp, Gpp)
        ok = out["best"] == "critical_gel" and not out["abstain"]
        all_pass &= ok
        print(f"{'PASS' if ok else 'FAIL'} {label} -> best={out['best']} "
              f"(weight {out['best_weight']:.3f}, abstain={out['abstain']})")

    # --- 3. melt counterexample ---
    print("\n=== Melt counterexample: Likhtman-McLeish (2002) PS 6, truncated ===")
    d = load_npz("data/likhtman_mcleish2002_fig10.npz")["PS 6"]
    w, mGp, mGpp = d["omega"], d["Gp"], d["Gpp"]
    axes[2].loglog(w, mGp, "o", ms=4, mfc="w", mew=1.0, label="G' PS 6")
    axes[2].loglog(w, mGpp, "^", ms=4, mfc="w", mew=1.0, label="G'' PS 6")
    for wmin in MELT_CUTOFFS:
        mask = w >= wmin
        out = identify(w[mask], mGp[mask], mGpp[mask])
        ok = out["best"] not in NETWORK_CLASSES
        all_pass &= ok
        print(f"{'PASS' if ok else 'FAIL'} wmin={wmin:.0e} ({mask.sum():2d} pts) "
              f"-> best={out['best']} (weight {out['best_weight']:.3f}), "
              f"flat decades={out['features']['flat_decades_lo']:.2f}")
        axes[2].axvline(wmin, color="k", ls=":", lw=0.8, alpha=0.5)

    # --- 4. real cured-elastomer data: Darby et al. (2022) ---
    print("\n=== Real cured-elastomer data: Darby et al. (2022) Fig. 1a ===")
    darby = load_npz("data/darby2022.npz")
    for name, s in darby.items():
        w, Gp, Gpp = s["omega"], s["Gp"], s["Gpp"]
        fit = fit_chasset_thirion(w, Gp, Gpp, n_restarts=N_RESTARTS, seed=1)
        Gp_f, Gpp_f = chasset_thirion_spectrum(w, fit["G_inf"], fit["c"], fit["m"])
        dlog = np.abs(np.log10(Gp_f) - np.log10(Gp)).mean()
        out = identify(w, Gp, Gpp)
        ginf_err = _rel(fit["G_inf"], DARBY_TABLE1_PA[name])
        ok = (out["best"] == "cured_elastomer" and ginf_err < DARBY_GINF_TOL
              and dlog < 0.05)
        all_pass &= ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: "
              f"G_inf {fit['G_inf']/1e3:6.1f} kPa vs Table 1 "
              f"{DARBY_TABLE1_PA[name]/1e3:.0f} kPa ({ginf_err:+.0%}), "
              f"m {fit['m']:.2f}, fit {dlog:.3f} dec, "
              f"-> {out['best']} (abstain={out['abstain']})")
        axes[3].loglog(w, Gp, "o", ms=4, label=f"G' {name}")
        axes[3].loglog(w, Gpp, "^", ms=4, mfc="w", label=f"G'' {name}")
        w_fit = np.geomspace(w.min(), w.max(), 100)
        gpf, gppf = chasset_thirion_spectrum(w_fit, fit["G_inf"], fit["c"], fit["m"])
        axes[3].loglog(w_fit, gpf, "-", lw=1, color="k", alpha=0.5)
        axes[3].loglog(w_fit, gppf, "--", lw=1, color="k", alpha=0.5)

    # --- 5. real critical-gel data: Tixier et al. (2004) ---
    print("\n=== Real critical-gel data: Tixier et al. (2004) Fig. 2/4 ===")
    tix = load_npz("data/tixier2004.npz")
    for name, s in tix.items():
        w, Gp, Gpp = s["omega"], s["Gp"], s["Gpp"]
        fit = fit_critical_gel(w, Gp, Gpp, n_restarts=N_RESTARTS, seed=1)
        Gp_f, Gpp_f = critical_gel_spectrum(w, fit["c"], fit["u"])
        dlog = max(np.abs(np.log10(Gp_f) - np.log10(Gp)).mean(),
                   np.abs(np.log10(Gpp_f) - np.log10(Gpp)).mean())
        out = identify(w, Gp, Gpp)
        # u must land in Tixier's measured range (their Table II: 0.69-0.75,
        # a little slack for digitizing scatter), and the class must win.
        ok = (out["best"] == "critical_gel" and 0.6 < fit["u"] < 0.85
              and dlog < 0.05)
        all_pass &= ok
        print(f"{'PASS' if ok else 'FAIL'} {name}: "
              f"u {fit['u']:.3f} (Tixier Table II: 0.69-0.75), "
              f"c {fit['c']:.2f} Pa, fit {dlog:.3f} dec, "
              f"-> {out['best']} (weight {out['best_weight']:.2f})")
        axes[4].loglog(w, Gp, "o", ms=5, label="G' (data)")
        axes[4].loglog(w, Gpp, "^", ms=5, mfc="w", label="G'' (data)")
        w_fit = np.geomspace(w.min(), w.max(), 100)
        gpf, gppf = critical_gel_spectrum(w_fit, fit["c"], fit["u"])
        axes[4].loglog(w_fit, gpf, "-", lw=1, color="k", alpha=0.5)
        axes[4].loglog(w_fit, gppf, "--", lw=1, color="k", alpha=0.5)

    for ax, title in zip(axes, ["Cured elastomer (planted)",
                                "Critical gel (planted)",
                                "Melt counterexample (real, truncated)",
                                "Darby 2022 silicones (real) + CT fit",
                                "Tixier 2004 gel (real) + springpot fit"]):
        ax.set_xlabel(r"$\omega$ (rad/s)")
        ax.set_ylabel("G', G'' (Pa)")
        ax.set_title(title)
        ax.legend(fontsize=7)
        ax.grid(True, which="both", ls=":", alpha=0.4)

    print(f"\n{'ALL PASS' if all_pass else 'SOME FAIL'} - planted-parameter + "
          f"routing + melt counterexample + Darby 2022 + Tixier 2004 real data")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
