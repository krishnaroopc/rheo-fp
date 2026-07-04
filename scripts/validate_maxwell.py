"""Validation script for rheofp.models.maxwell (from batch1_maxwell_prony.ipynb).

Run directly: python scripts/validate_maxwell.py
Reproduces the original notebook's planted-parameter recovery checks and
plots via plt.show() only (no savefig, no saved notebook outputs).
"""
import numpy as np
import matplotlib.pyplot as plt

from rheofp.models.maxwell import (
    maxwell_spectrum, wlm_spectrum, fit_maxwell, fit_wlm,
    sticky_maxwell_stack, fit_sticky_stack,
)

W_MIN_DEC, W_MAX_DEC, N_PER_DEC = -2, 3, 12
OMEGA = np.logspace(W_MIN_DEC, W_MAX_DEC, int((W_MAX_DEC - W_MIN_DEC) * N_PER_DEC) + 1)

WLM_REF = dict(G0=30.0, tau_rep=30.0, tau_br=0.03, beta=0.8)
STICKY_REF = dict(G=[5000.0], tau_ref=[1.0], Ea=60e3, T_ref=298.15,
                   T_list=[278.15, 288.15, 298.15, 308.15, 318.15])


def _rel(a, b):
    return abs(a - b) / abs(b)


def main():
    # Single mode
    Gp, Gpp = maxwell_spectrum(OMEGA, [1000.0], [0.5])
    f1 = fit_maxwell(OMEGA, Gp, Gpp, n_modes=1)
    print("Single-mode Maxwell:")
    print(f"  G   true=1000.000 fit={f1['G'][0]:9.3f}  relerr={_rel(f1['G'][0],1000):.2e}")
    print(f"  tau true=   0.500 fit={f1['tau'][0]:9.3f}  relerr={_rel(f1['tau'][0],0.5):.2e}")

    # Three modes
    G3, t3 = np.array([2000., 500., 80.]), np.array([0.01, 0.3, 5.0])
    Gp3, Gpp3 = maxwell_spectrum(OMEGA, G3, t3)
    f3 = fit_maxwell(OMEGA, Gp3, Gpp3, n_modes=3, n_restarts=30, seed=3)
    print("\nThree-mode Prony:")
    for i in range(3):
        print(f"  mode {i}: G {G3[i]:7.1f}->{f3['G'][i]:7.1f}   tau {t3[i]:7.4f}->{f3['tau'][i]:7.4f}")
    print(f"  cost={f3['cost']:.2e}")

    # Wormlike micelle
    wp = WLM_REF
    Gp_w, Gpp_w = wlm_spectrum(OMEGA, wp["G0"], wp["tau_rep"], wp["tau_br"], wp["beta"])
    tau_dom = np.sqrt(wp["tau_rep"] * wp["tau_br"])
    fw = fit_wlm(OMEGA, Gp_w, Gpp_w, n_restarts=20)
    print("\nWormlike micelle (standard regime, G0~30 Pa, tau_R~1 s):")
    print(f"  G0      true={wp['G0']:7.3f}  fit={fw['G0']:7.3f}  relerr={_rel(fw['G0'],wp['G0']):.2e}")
    print(f"  tau_dom true={tau_dom:7.3f}  fit={fw['tau']:7.3f}  relerr={_rel(fw['tau'],tau_dom):.2e}")

    # Sticky-Maxwell stack
    sp = STICKY_REF
    stack = sticky_maxwell_stack(OMEGA, sp["G"], sp["tau_ref"], sp["Ea"], sp["T_list"], sp["T_ref"])
    sGp = [s[0] for s in stack]
    sGpp = [s[1] for s in stack]
    fs = fit_sticky_stack(OMEGA, sGp, sGpp, sp["T_list"], sp["T_ref"], n_modes=1)
    print("\nSticky-Maxwell stack (associating network / vitrimer, shared Ea):")
    print(f"  G       true={sp['G'][0]:8.2f}  fit={fs['G'][0]:8.2f}  relerr={_rel(fs['G'][0],sp['G'][0]):.2e}")
    print(f"  tau_ref true={sp['tau_ref'][0]:8.3f}  fit={fs['tau_ref'][0]:8.3f}  relerr={_rel(fs['tau_ref'][0],sp['tau_ref'][0]):.2e}")
    print(f"  Ea      true={sp['Ea']/1e3:8.2f}  fit={fs['Ea']/1e3:8.2f} kJ/mol  relerr={_rel(fs['Ea'],sp['Ea']):.2e}")

    fig, ax = plt.subplots(1, 3, figsize=(15, 4.2))

    ax[0].loglog(OMEGA, Gp, label="G' (1-mode)")
    ax[0].loglog(OMEGA, Gpp, "--", label="G'' (1-mode)")
    ax[0].loglog(OMEGA, Gp3, label="G' (3-mode)")
    ax[0].loglog(OMEGA, Gpp3, "--", label="G'' (3-mode)")
    ax[0].set_title("Maxwell / Prony")
    ax[0].set_xlabel(r"$\omega$ [rad/s]")
    ax[0].set_ylabel("modulus [Pa]")
    ax[0].legend(fontsize=8)
    ax[0].grid(True, which="both", alpha=.3)

    ax[1].loglog(OMEGA, Gp_w, "o", ms=3, label="G'")
    ax[1].loglog(OMEGA, Gpp_w, "s", ms=3, mfc="none", label="G''")
    ax[1].axvline(1 / tau_dom, color="k", lw=.6, ls=":")
    ax[1].set_title("Wormlike micelle (CPyCl/NaSal)")
    ax[1].set_xlabel(r"$\omega$ [rad/s]")
    ax[1].legend(fontsize=8)
    ax[1].grid(True, which="both", alpha=.3)

    for k, T in enumerate(sp["T_list"]):
        ax[2].loglog(OMEGA, sGp[k], color=plt.cm.viridis(k / len(sp["T_list"])),
                     label=f"{T-273.15:.0f} C")
    ax[2].set_title("Sticky-Maxwell G' vs T (Arrhenius)")
    ax[2].set_xlabel(r"$\omega$ [rad/s]")
    ax[2].legend(fontsize=7, title="G' only")
    ax[2].grid(True, which="both", alpha=.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
