"""Validate the star class against REAL star-melt data (step 4).

Two datasets, and they answer different questions:

  data/mm1998.npz       Seven monodisperse FOUR-ARM polyisoprene stars,
                        Ma 11 400 - 105 000, Me = 5000 so Z = Ma/Me spans
                        2.3 - 21. Milner & McLeish (1998) Macromolecules 31,
                        7479, Figs 1/2 - THE THEORY'S OWN VALIDATION SET, where
                        the authors report excellent agreement at all seven arm
                        lengths with no adjustable parameters. Z is known
                        independently (GPC on the arm precursors), so this is
                        the quantitative test.

  data/santangelo1999.npz  Two SIX-ARM polyisobutylene stars (Z = 4 and 9 per
                        arm) plus a LINEAR control, Santangelo, Roland & Puskas
                        (1999) Macromolecules 32, 1972, Figs 1/2. The linear
                        control makes this the DISCRIMINATION test - a star
                        model that also claims linear melts has not earned the
                        class.

Run:  uv run python scripts/validate_star_real.py

Reports, per sample: the fitted Z against the known Z, the absolute fit
quality, and what identify() actually returns from the full 10-model bank.

READ THE RESULT THIS WAY. `identify()` returning "star" is the claim the class
makes to a user; the Z column is a stricter internal check and is NOT currently
a reportable output (see rheofp/models/star.py - Z runs high by 17-84% on
mm1998, and Z below 4 is outside Z_BOUNDS entirely). Santangelo is expected to
fail the Z check for a documented reason of its own: its window never reaches
terminal flow (measured slopes G' ~ 1.1, G'' ~ 0.55 against the 2.0/1.0 melt
limit - the paper's own Fig. 1 caption says omega^2 "is not attained ... due to
polydispersity"), and Z, being the spectrum-WIDTH parameter, absorbs the
truncation.
"""
import numpy as np

from rheofp.io.data import load_npz
from rheofp.models.star import fit_star, star_spectrum
from rheofp.fitting.identify import identify

N_RESTARTS = 16

MM1998 = "data/mm1998.npz"
SANTANGELO = "data/santangelo1999.npz"
ME_PI = 5000.0

# Santangelo Table 1: Ma/Me, with Me = 9400. None marks the linear control.
SANTANGELO_Z = {"S490": 9.0, "S217": 4.0, "L176": None}


def _fit_report(w, gp, gpp):
    r = fit_star(w, gp, gpp, n_restarts=N_RESTARTS)
    Gp, Gpp = star_spectrum(w, r["G_N"], r["Z"], r["tau_e"])
    rms = float(np.sqrt(np.mean(np.concatenate([
        np.log10(Gp / gp), np.log10(Gpp / gpp)]) ** 2)))
    return r, rms


def _terminal_slopes(w, gp, gpp, k=8):
    k = min(k, len(w) // 3)
    return (float(np.polyfit(np.log10(w[:k]), np.log10(gp[:k]), 1)[0]),
            float(np.polyfit(np.log10(w[:k]), np.log10(gpp[:k]), 1)[0]))


def main():
    print("=" * 72)
    print("MM1998 - seven four-arm polyisoprene stars (the theory's own set)")
    print("=" * 72)
    print(f"{'sample':14s} {'Z_true':>7s} {'Z_fit':>7s} {'err':>7s} "
          f"{'G_N kPa':>8s} {'rms':>7s}  identify()")
    data = load_npz(MM1998)
    errs, hits = [], 0
    for name, s in data.items():
        ma = float(name.split("Ma")[1].rstrip("k")) * 1000.0
        z_true = ma / ME_PI
        w, gp, gpp = s["omega"], s["Gp"], s["Gpp"]
        r, rms = _fit_report(w, gp, gpp)
        best = identify(w, gp, gpp, n_restarts=12)["best"]
        hits += best == "star"
        err = 100.0 * (r["Z"] - z_true) / z_true
        note = ""
        if z_true < 4.0:
            note = "  <- below Z_BOUNDS floor, cannot fit"
        else:
            errs.append(abs(err))
        print(f"{name:14s} {z_true:7.2f} {r['Z']:7.2f} {err:+6.0f}% "
              f"{r['G_N'] / 1e3:8.1f} {rms:7.4f}  {best}{note}")
    print(f"\n  identify() -> star on {hits}/{len(data)}")
    if errs:
        print(f"  median |Z error| (Z_true >= 4): {np.median(errs):.0f}%")

    print()
    print("=" * 72)
    print("Santangelo 1999 - six-arm PIB stars + a LINEAR control")
    print("=" * 72)
    print(f"{'sample':10s} {'truth':12s} {'Z_true':>7s} {'Z_fit':>7s} "
          f"{'rms':>7s}  {'slopes Gp/Gpp':>14s}  identify()")
    data = load_npz(SANTANGELO)
    for name, s in data.items():
        w, gp, gpp = s["omega"], s["Gp"], s["Gpp"]
        # The paper's Figs 1/2 run into the glass transition zone, which the
        # star model has no term for; keep the fit below it.
        m = w <= 1e3
        w, gp, gpp = w[m], gp[m], gpp[m]
        z_true = SANTANGELO_Z.get(name)
        r, rms = _fit_report(w, gp, gpp)
        best = identify(w, gp, gpp, n_restarts=12)["best"]
        s_gp, s_gpp = _terminal_slopes(w, gp, gpp)
        truth = "6-arm star" if z_true is not None else "LINEAR"
        zt = f"{z_true:7.2f}" if z_true is not None else f"{'-':>7s}"
        flag = ""
        if z_true is None and best == "star":
            flag = "  <- FALSE POSITIVE"
        print(f"{name:10s} {truth:12s} {zt} {r['Z']:7.2f} {rms:7.4f}  "
              f"{s_gp:6.2f}/{s_gpp:<7.2f}  {best}{flag}")
    print("\n  terminal slopes far from 2.0/1.0 mean the window never reached")
    print("  flow, so Z there is measuring the crop, not the molecule.")


if __name__ == "__main__":
    main()
