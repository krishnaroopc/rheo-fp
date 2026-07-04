"""Validation script for rheofp.models.tube (from batch2_tube_models.ipynb).

figure10_likhtman_mcleish_fit.ipynb's tube-model code was confirmed
byte-for-byte identical to batch2's during migration and is not represented
separately - this script covers both notebooks' validation content.

Run directly: python scripts/validate_tube.py
"""
import numpy as np
import matplotlib.pyplot as plt

from rheofp.models.maxwell import branched_spectrum, fit_branched
from rheofp.models.tube import Z_of_sample, linear_melt_forward, valid_window


def _rel(a, b):
    return abs(a - b) / abs(b)


def main():
    # --- Validation 1: linear melt terminal slopes + valid-window physicality ---
    Ge, te, Mw = 2.0e5, 1e-3, 300_000.0
    Z = Z_of_sample(Mw, Ge)
    rng = np.random.default_rng(0)

    omega_full = np.logspace(-4, 1, 80)
    Gp, Gpp = linear_melt_forward(omega_full, Ge, te, Mw, nchains=60, rng=rng)
    lo = omega_full < 1e-2
    sGp = np.polyfit(np.log(omega_full[lo]), np.log(Gp[lo]), 1)[0]
    sGpp = np.polyfit(np.log(omega_full[lo]), np.log(Gpp[lo]), 1)[0]
    print(f"Linear melt (Z={Z:.1f}):")
    print(f"  terminal slopes: G'~w^{sGp:.2f} (expect 2), G''~w^{sGpp:.2f} (expect 1)")

    wlo, whi = valid_window(Ge, te, Mw)
    omega_valid = np.logspace(np.log10(wlo), np.log10(whi), 120)
    Gpv, Gppv = linear_melt_forward(omega_valid, Ge, te, Mw, nchains=80, rng=np.random.default_rng(1))
    print(f"  valid window [{wlo:.2e}, {whi:.2e}] rad/s:")
    print(f"    max G'  = {Gpv.max()/Ge:.2f} Ge")
    print(f"    max G'' = {Gppv.max()/Ge:.2f} Ge   (physical iff < 1)")
    assert 1.6 < sGp < 2.3 and 0.7 < sGpp < 1.2, "terminal slopes off"
    assert Gppv.max() < Ge, "G'' exceeds Ge in valid window - unphysical"
    print("  PASS - terminal slopes correct; G'' < Ge within valid window")

    # --- Validation 2: branched/LCB planted recovery ---
    ref = dict(Ge=1.0e5, tau_b=10.0, sigma=2.5)
    omega_b = np.logspace(-5, 3, 110)
    Gp_b, Gpp_b = branched_spectrum(omega_b, ref["Ge"], ref["tau_b"], ref["sigma"])
    fb = fit_branched(omega_b, Gp_b, Gpp_b, n_restarts=20, seed=2)
    print("\nBranched / LCB planted recovery:")
    print(f"  Ge:    true={ref['Ge']:.3e}  fit={fb['Ge']:.3e}  relerr={_rel(fb['Ge'],ref['Ge']):.2e}")
    print(f"  tau_b: true={ref['tau_b']:.3f}  fit={fb['tau_b']:.3f}  relerr={_rel(fb['tau_b'],ref['tau_b']):.2e}")
    print(f"  sigma: true={ref['sigma']:.3f}  fit={fb['sigma']:.3f}  relerr={_rel(fb['sigma'],ref['sigma']):.2e}")
    assert _rel(fb['Ge'], ref['Ge']) < 0.05 and _rel(fb['tau_b'], ref['tau_b']) < 0.15 and _rel(fb['sigma'], ref['sigma']) < 0.15
    assert Gp_b.max() / ref["Ge"] > 0.9, "branched should reach the plateau"
    print("  PASS - parameters recovered; full plateau reached")

    # --- Validation 3: physical discriminator - branched broader than linear ---
    omega = np.logspace(np.log10(wlo), np.log10(whi), 200)
    Gp_lin, Gpp_lin = linear_melt_forward(omega, Ge, te, Mw, nchains=80, rng=np.random.default_rng(1))
    tau_term = 1.0 / omega[np.argmax(Gpp_lin)]
    Gp_br, Gpp_br = branched_spectrum(omega, Ge, tau_term, sigma=2.5)

    def td_span(omega, Gp, Gpp):
        td = Gpp / np.maximum(Gp, 1e-300)
        r = omega[td > 1.0]
        return np.log10(r.max() / r.min()) if len(r) > 2 else 0.0

    s_lin, s_br = td_span(omega, Gp_lin, Gpp_lin), td_span(omega, Gp_br, Gpp_br)
    pk_lin, pk_br = Gpp_lin.max() / Ge, Gpp_br.max() / Ge
    print("\nDiscriminator (within linear valid window):")
    print(f"  tan(delta)>1 span:  linear={s_lin:.2f}  branched={s_br:.2f} decades")
    print(f"  G'' peak / Ge:      linear={pk_lin:.2f}  branched={pk_br:.2f}")
    assert s_br > s_lin, "branched must be more loss-dominated"
    assert pk_lin < 1 and pk_br < 1, "G'' must stay below Ge"
    print(f"  PASS - branched {s_br/s_lin:.1f}x broader terminal; both physical")

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.4))
    ax[0].loglog(omega, Gp_lin, color="#2563eb", lw=2, label="G' linear")
    ax[0].loglog(omega, Gpp_lin, "--", color="#dc2626", lw=2, label="G'' linear")
    ax[0].axhline(Ge, color="k", lw=.5, ls=":", label="$G_e$")
    ax[0].set_title("Linear melt (L-M, valid window)")
    ax[0].set_xlabel(r"$\omega$ [rad/s]")
    ax[0].set_ylabel("modulus [Pa]")
    ax[0].legend(fontsize=8)
    ax[0].grid(True, which="both", alpha=.3)

    ax[1].loglog(omega, Gp_lin, color="#2563eb", lw=1.5, label="G' linear")
    ax[1].loglog(omega, Gpp_lin, "--", color="#2563eb", lw=1.5, label="G'' linear")
    ax[1].loglog(omega, Gp_br, color="#16a34a", lw=1.5, label="G' branched")
    ax[1].loglog(omega, Gpp_br, "--", color="#16a34a", lw=1.5, label="G'' branched")
    ax[1].set_title("Linear vs branched (LCB broader)")
    ax[1].set_xlabel(r"$\omega$ [rad/s]")
    ax[1].legend(fontsize=8)
    ax[1].grid(True, which="both", alpha=.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
