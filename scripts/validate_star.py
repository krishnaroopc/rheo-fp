"""Validation script for rheofp.models.star (Milner-McLeish star melts).

  1. Forward physics against the paper's own analytic statements and figures -
     eq 24 collapsing onto eq 8 at alpha = 1, the Figure 2 potential ratio,
     the quoted log(tau(1)/tau_0) = 13.8 for the Figure 1 system, and the
     location of the eq-22 handoff from the early to the activated branch.
  2. Planted-parameter recovery - noiseless round trip, then under the 2%
     log-normal scatter synth.py uses for digitized figures.
  3. Identifiability of Z - the profile cost along Z with G_N and tau_e
     re-optimised, which is what shows Z is a genuine shape parameter and not
     degenerate with the tau_e time shift.
  4. The two window limits found while building the fitter: a low-Z spectrum
     loses Z when the plateau is cropped away, and past Z ~ 40 the loss
     modulus develops two peaks rather than one.

Run directly: python scripts/validate_star.py

STATUS: `star` is NOT in identify()'s bank yet - the cannibalisation check
against `branched` (BSW) has not been run. See .claude-notes/next-actions.md.
"""
import numpy as np
import matplotlib.pyplot as plt

from rheofp.models.star import (
    ALPHA_CR, fit_star, star_spectrum, tau_of_s, ueff, _tau_activated,
    _tau_early,
)

# Paper's Figure 1/5 system: 12-arm 1,4-polybutadiene, arm Mw 30 280,
# Me = 1815, with the literature values quoted in its section IV.
Z_FIG1 = 30280.0 / 1815.0
G_N_FIG1 = 1.25e6
TAU_E_FIG1 = 7.8e-6

PLANTED = [
    (1.25e6, 17.0, 7.8e-6),
    (5.0e5, 8.0, 1.0e-4),
    (2.0e6, 30.0, 1.0e-6),
    (8.0e5, 12.0, 3.0e-5),
]


def check_forward_physics():
    print("1. FORWARD PHYSICS vs the paper's own statements")
    s = np.linspace(0.0, 1.0, 201)
    eq8 = 15.0 * 17.0 * (s**2 - 2.0 * s**3 / 3.0) / 8.0
    print(f"   eq24 -> eq8 at alpha=1, max abs diff : "
          f"{np.abs(ueff(s, 17.0, 1.0) - eq8).max():.3e}")

    ratio = ueff(1.0, 17.0, ALPHA_CR) / (15.0 * 17.0 / 8.0)
    print(f"   Ueff(1)/U_PH(1) at alpha=4/3         : {ratio:.3f}  (Fig 2 ~0.26)")
    print(f"   Ueff(1)/U_PH(1) at alpha=1           : "
          f"{ueff(1.0, 17.0, 1.0) / (15.0 * 17.0 / 8.0):.3f}  (text: 1/3)")
    print(f"   Pearson-Helfand log10 exp[U(1)]      : "
          f"{(15.0 * 17.0 / 8.0) / np.log(10):.2f}  (paper: 13.8)")

    s = np.linspace(1e-6, 1.0 - 1e-9, 20000)
    early = _tau_early(s, Z_FIG1, TAU_E_FIG1)
    activated = _tau_activated(s, Z_FIG1, TAU_E_FIG1, ALPHA_CR)
    over = early > activated
    print(f"   eq22 handoff to activated branch at s: {s[np.argmax(over)]:.3f}"
          f"  (text: 1-s ~ (Ne/N)^1/2, i.e. s ~ 0.2)")

    w = np.logspace(-8, -5, 60)
    Gp, Gpp = star_spectrum(w, G_N_FIG1, Z_FIG1, TAU_E_FIG1)
    print(f"   terminal slopes G', G''              : "
          f"{np.polyfit(np.log10(w), np.log10(Gp), 1)[0]:.4f}, "
          f"{np.polyfit(np.log10(w), np.log10(Gpp), 1)[0]:.4f}  (want 2, 1)")

    w = np.logspace(-6, 6, 400)
    Gp, _ = star_spectrum(w, G_N_FIG1, Z_FIG1, TAU_E_FIG1)
    print(f"   G' plateau / G_N                     : {Gp.max() / G_N_FIG1:.3f}")


def check_recovery():
    print("\n2. PLANTED-PARAMETER RECOVERY")
    print(f"   {'G_N':>10} {'Z':>6} {'tau_e':>10} | {'G_N fit':>10} {'Z fit':>7}"
          f" {'tau_e fit':>10} | {'rms dec':>8}")
    for G_N, Z, tau_e in PLANTED:
        w = np.logspace(-3, 5, 60)
        Gp, Gpp = star_spectrum(w, G_N, Z, tau_e)
        keep = (Gp > Gp.max() * 1e-6) & (Gpp > Gpp.max() * 1e-6)
        got = fit_star(w[keep], Gp[keep], Gpp[keep], n_restarts=24, seed=1)
        fp, fq = star_spectrum(w[keep], got["G_N"], got["Z"], got["tau_e"])
        rms = np.sqrt(np.mean(np.concatenate(
            [np.log10(fp / Gp[keep]), np.log10(fq / Gpp[keep])]) ** 2))
        print(f"   {G_N:10.3g} {Z:6.1f} {tau_e:10.3g} | {got['G_N']:10.3g}"
              f" {got['Z']:7.2f} {got['tau_e']:10.3g} | {rms:8.4f}")

    print("\n   under 2% log-normal noise (median of 5 seeds):")
    for Z in (8.0, 17.0, 30.0):
        fits = []
        for seed in range(5):
            rng = np.random.default_rng(seed)
            w = np.logspace(-3, 5, 50)
            Gp, Gpp = star_spectrum(w, 1e6, Z, 1e-5)
            Gp = Gp * np.exp(rng.normal(0, 0.02, len(w)))
            Gpp = Gpp * np.exp(rng.normal(0, 0.02, len(w)))
            fits.append(fit_star(w, Gp, Gpp, n_restarts=24, seed=seed)["Z"])
        print(f"     Z true {Z:5.1f} -> fitted {np.median(fits):6.2f}"
              f"  ({100 * (np.median(fits) - Z) / Z:+.1f}%)")


def check_identifiability():
    """Profile the cost along Z with the two scale parameters re-optimised."""
    print("\n3. IS Z IDENTIFIABLE, OR DEGENERATE WITH tau_e?")
    w = np.logspace(-3, 5, 60)
    Gp, Gpp = star_spectrum(w, 1e6, 17.0, 1e-5)
    yp, ypp = np.log(Gp), np.log(Gpp)
    print(f"   {'Z':>6} {'best cost':>12}")
    for Zt in (12.0, 15.0, 16.0, 17.0, 18.0, 20.0, 25.0):
        best = np.inf
        for dg in (-0.5, 0.0, 0.5):
            for dt in (-0.5, 0.0, 0.5):
                from scipy.optimize import minimize

                def f(p):
                    a, b = star_spectrum(w, np.exp(p[0]), Zt, np.exp(p[1]))
                    r = np.concatenate([np.log(a) - yp, np.log(b) - ypp])
                    return 0.5 * r @ r

                r = minimize(f, [np.log(1e6) + dg, np.log(1e-5) + dt],
                             method="Nelder-Mead",
                             options=dict(maxiter=2000, xatol=1e-8, fatol=1e-12))
                best = min(best, r.fun)
        print(f"   {Zt:6.1f} {best:12.4e}")
    print("   A sharp minimum at the true Z means the spectrum SHAPE carries")
    print("   Z, so it does not trade off against the tau_e time shift.")


def check_window_limits():
    print("\n4. WINDOW LIMITS")
    rng = np.random.default_rng(0)
    w = np.logspace(-3, 2, 50)
    Gp, Gpp = star_spectrum(w, 1e6, 8.0, 1e-5)
    Gp = Gp * np.exp(rng.normal(0, 0.02, len(w)))
    Gpp = Gpp * np.exp(rng.normal(0, 0.02, len(w)))
    got = fit_star(w, Gp, Gpp, n_restarts=24, seed=0)
    print(f"   Z=8 with the plateau cropped away -> fitted Z = {got['Z']:.2f}")
    print("   (the profile minimum is still at 8; 2% noise moves it ~20%, so")
    print("    Z must not be reported from a terminal-only sweep)")

    w = np.logspace(-12, 6, 900)
    for Z in (17.0, 25.0, 40.0, 55.0):
        _, Gpp = star_spectrum(w, 1e6, Z, 1e-5)
        n = int((np.diff(np.sign(np.diff(Gpp))) < 0).sum())
        print(f"   Z={Z:5.1f}: {n} G'' {'maximum' if n == 1 else 'maxima'}")
    print("   Past Z ~ 40 the barrier splits the loss peak in two (converged")
    print("   for n_s 400..64000). Any 'one loss peak' feature will misread it.")


def plot_overview():
    w = np.logspace(-6, 6, 400)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for Z in (8.0, 17.0, 30.0, 45.0):
        Gp, Gpp = star_spectrum(w, 1e6, Z, 1e-5)
        line, = ax[0].loglog(w, Gp, label=f"Z = {Z:.0f}")
        ax[0].loglog(w, Gpp, "--", color=line.get_color())
        ax[1].loglog(w, Gpp / Gp, color=line.get_color(), label=f"Z = {Z:.0f}")
    ax[0].set(xlabel="omega [rad/s]", ylabel="G', G'' [Pa]",
              title="Star melt: G' (solid), G'' (dashed)")
    ax[1].set(xlabel="omega [rad/s]", ylabel="tan(delta)",
              title="Loss tangent")
    for a in ax:
        a.legend(fontsize=8)
        a.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    check_forward_physics()
    check_recovery()
    check_identifiability()
    check_window_limits()
    plot_overview()
