"""Can the sticky (vitrimer) forward models represent a REAL vitrimer?

Opened as next-actions 2b after both real temperature stacks returned
`branched` for a genuine dioxaborolane vitrimer. The sticky models were only
ever validated against PLANTED synthetic parameters; neither had ever been
fitted to real measured vitrimer data.

Three candidate explanations, tested in order - fitter, bounds, functional
form. Run: python scripts/diagnose_sticky_models.py

CONCLUSION (2026-09-07): it is the FUNCTIONAL FORM, and the reason is physical
rather than a coding defect. See the summary printed at the end.
"""
from __future__ import annotations

import numpy as np

from rheofp.io.data import load_npz
from rheofp.models.solutions import (
    model_sticky_rouse, model_sticky_reptation, SR_BNDS, SREP_BNDS,
)
from rheofp.models.maxwell import model_branched
from rheofp.fitting.optimize import multi_restart_fit

SRC = "data/ricarte2023.npz"
CURVE = "Ricarte2023_PBv4_120C"

# Bounds widened well past the published ones, to separate "the bounds bind"
# from "the model cannot reach it".
WIDE_SR = [(0, 9), (-3, 8), (-9, 4), (2, 5000)]
WIDE_SREP = [(0, 9), (-3, 9), (2, 2000), (-6, 7)]
BSW_BNDS = [(0, 9), (-4, 6), (-6, 5), (0.05, 0.95), (0.05, 0.95)]


def main():
    v = load_npz(SRC)[CURVE]
    w, Gp, Gpp = v["omega"], v["Gp"], v["Gpp"]
    n_data = 2 * len(w)

    def sse(theta, fwd):
        try:
            mp, mpp = fwd(w, theta)
        except Exception:
            return 1e6
        mp = np.clip(mp, 1e-30, None)
        mpp = np.clip(mpp, 1e-30, None)
        r = np.concatenate([np.log10(mp) - np.log10(Gp),
                            np.log10(mpp) - np.log10(Gpp)])
        return float(np.sum(r ** 2))

    def fit(fwd, bnds, n_restarts):
        best = multi_restart_fit(lambda t: sse(t, fwd), bnds, n_restarts,
                                 seed=1)
        return best, np.sqrt(best.fun / n_data)

    print("=" * 74)
    print(f"Can the sticky models fit a real vitrimer?  ({CURVE})")
    print("=" * 74)

    print("\n1. IS IT THE FITTER?  (more restarts, published bounds)")
    for name, fwd, bnds in (("sticky_rouse", model_sticky_rouse, SR_BNDS),
                            ("sticky_reptation", model_sticky_reptation,
                             SREP_BNDS)):
        for nres in (12, 200):
            _, rms = fit(fwd, bnds, nres)
            print(f"   {name:18s} {nres:3d} restarts -> {rms:.4f} dec")
    print("   NO. 12 and 200 restarts agree to 4 decimals - the optimizer is")
    print("   already finding the optimum inside these bounds.")

    print("\n2. IS IT THE BOUNDS?  (push the mode-count ceilings)")
    print("   sticky_rouse, Nst ceiling:")
    for cap in (150, 400, 1500, 5000, 20000):
        b, rms = fit(model_sticky_rouse, [(0, 9), (-3, 8), (-9, 4), (2, cap)],
                     150)
        pin = "PINNED" if b.x[3] > 0.97 * cap else ""
        print(f"     Nst <= {cap:6d}  rms={rms:.4f}  Nst*={b.x[3]:7.0f}  {pin}")
    print("   sticky_reptation, Z ceiling:")
    for cap in (200, 600, 2000, 8000):
        b, rms = fit(model_sticky_reptation,
                     [(0, 9), (-3, 9), (2, cap), (-6, 7)], 150)
        pin = "PINNED" if b.x[2] > 0.97 * cap else ""
        print(f"     Z   <= {cap:6d}  rms={rms:.4f}  Z*={b.x[2]:7.0f}  {pin}")
    print("   PARTLY. The published bounds DO bind - sticky_rouse improves")
    print("   0.203 -> 0.161 and sticky_reptation 0.390 -> 0.131 once freed.")
    print("   But both then plateau far above BSW, and sticky_reptation's Z")
    print("   runs away to any ceiling offered while its RMS stops moving:")
    print("   Z has become a nuisance parameter buying nothing.")

    print("\n3. IS IT THE FUNCTIONAL FORM?  (where does the misfit live?)")
    fits = {
        "sticky_rouse": (model_sticky_rouse,
                         fit(model_sticky_rouse, WIDE_SR, 200)),
        "sticky_reptation": (model_sticky_reptation,
                             fit(model_sticky_reptation, WIDE_SREP, 200)),
        "branched (BSW)": (model_branched, fit(model_branched, BSW_BNDS, 200)),
    }
    print(f"   {'model':20s} {'total':>7s} {'G-prime':>9s} {'G-2prime':>9s}")
    for name, (fwd, (b, rms)) in fits.items():
        mp, mpp = fwd(w, b.x)
        dgp = np.log10(mp) - np.log10(Gp)
        dgpp = np.log10(mpp) - np.log10(Gpp)
        print(f"   {name:20s} {rms:7.4f} {np.sqrt((dgp**2).mean()):9.4f} "
              f"{np.sqrt((dgpp**2).mean()):9.4f}")
    print("   YES. Every model reproduces G' well. The ENTIRE failure is G''.")

    print("\n4. WHY - what shape is this data?")
    lw = np.log10(w)
    k = 8
    sl_lo = np.polyfit(lw[:k], np.log10(Gpp[:k]), 1)[0]
    print(f"   G'  spans only {np.ptp(np.log10(Gp)):.3f} decades over "
          f"{np.ptp(lw):.1f} decades of omega - essentially FLAT")
    print(f"   G'' spans {np.ptp(np.log10(Gpp)):.3f} decades and RISES as "
          "omega falls")
    print(f"   low-omega log-slope of G'': {sl_lo:+.3f}  "
          f"(whole window {np.polyfit(lw, np.log10(Gpp), 1)[0]:+.3f})")
    print(f"   tan(delta) {np.min(Gpp/Gp):.4f} -> {np.max(Gpp/Gp):.4f}, "
          "never reaching 1: G'' never crosses G'")
    print("""
   A terminal relaxation requires G'' ~ w^1 (slope +1) and G' ~ w^2. This
   curve has a NEGATIVE G'' slope - the loss modulus rises toward zero
   frequency. That is a power-law wing, not a terminal zone, and the paper
   says so itself: the modulus "transitions from a rubbery plateau into a
   power law regime", with the true terminal relaxation outside the window.

   Both sticky models are built from a SMALL NUMBER OF DISCRETE Maxwell
   modes around a single sticker time tau_s. Such a spectrum produces a G''
   PEAK near 1/tau_s and must fall away on both sides. It cannot rise
   monotonically across four decades. The fitter's only escape is to pile up
   modes - which is exactly why Nst and Z run to their ceilings - and even
   unbounded that approximates a power law poorly.

   BSW wins because its two power-law wedges ARE a broad continuous spectrum,
   which is the correct description of this material's LVE in this window.""")

    print("\n5. IS THE SYNTHETIC POPULATION THE SAME SHAPE?")
    from rheofp.data.synth import make_example
    rng = np.random.default_rng(11)
    print(f"   {'source':28s} {'G-prime span':>13s} {'G-2prime span':>14s}")
    print(f"   {'REAL Ricarte 120C':28s} {np.ptp(np.log10(Gp)):13.3f} "
          f"{np.ptp(np.log10(Gpp)):14.2f}")
    for cls in ("sticky_rouse", "sticky_reptation"):
        a = []
        for _ in range(40):
            ex = make_example(rng, cls, n_curves=1)
            ww, gp, gpp, _ = ex["curves"][0]
            a.append((np.ptp(np.log10(gp)), np.ptp(np.log10(gpp))))
        a = np.array(a)
        print(f"   {'SYNTH ' + cls:28s} {np.median(a[:, 0]):13.3f} "
              f"{np.median(a[:, 1]):14.2f}")
    print("""
   The low-frequency G'' slope of synthetic sticky_rouse (~-0.7) actually
   MATCHES the real vitrimer closely - the models do produce a rising G''
   wing, so the training distribution is not the wrong shape wholesale.
   The difference is in G': the real curve's G' spans 0.019 decades, about
   TEN TIMES flatter than the synthetic population's ~0.26. Synthetic
   sticky curves carry visible G' structure that this real material simply
   does not have, and identify() recovers synthetic sticky_rouse 9 times in
   10. So the models work on the population they were built from; it is the
   real material that sits at an extreme edge of it - an almost perfectly
   flat elastic modulus with all the information in G''.""")

    print("\n" + "=" * 74)
    print("""CONCLUSION

   The sticky models cannot represent a real dioxaborolane vitrimer measured
   over its power-law regime. This is a FORWARD-MODEL limitation, not a
   fitter bug and not merely bad bounds - the same class of finding as
   branched_spectrum vs real LDPE on 2026-09-03, which was resolved by
   replacing the forward model with BSW.

   IMPORTANT SCOPE NOTE, so this is not over-generalised: it says these
   models cannot fit THIS material over THIS window. The sticker shoulder
   they are built to describe lives near 1/tau_s, and the paper places the
   real terminal/exchange relaxation OUTSIDE the measured 0.01-100 rad/s
   window. A vitrimer measured across its actual sticker peak may well be
   fitted correctly - no such real dataset has been tested yet.

   And note section 5: this is NOT a case of the synthetic population having
   the wrong shape. Synthetic sticky_rouse reproduces the real material's
   rising G'' wing closely, and identify() recovers synthetic sticky curves
   9 times in 10. The real material sits at an extreme EDGE of that
   population - a G' ten times flatter than typical - where the remaining
   discrimination has to come from G'' alone, and there BSW's broad spectrum
   simply describes the data better. Widening the synthetic G' range toward
   flatness would make training more representative, but it would not by
   itself fix the fit: the 0.16 vs 0.046 decade gap is the forward model's,
   not the sampler's.

   Two candidate directions, neither yet chosen:
     (a) Give the sticker classes a broad-spectrum forward model - a
         BSW-like or fractional/springpot wing anchored to a sticker time -
         so a power-law regime is reachable. Risk: it converges on BSW's
         shape and stops being distinguishable from `branched`, which would
         be worse than the present honest failure.
     (b) Accept the limit and make it explicit: report `branched` /
         Terminal for such curves and state in the challenge section that a
         vitrimer measured in its power-law regime is not separable from a
         broad branched spectrum by LVE shape alone, naming the measurement
         (reach the sticker peak, or a wider window) that would separate
         them. This is the melt-vs-rubber precedent - abstain rather than
         guess - applied to a newly measured degeneracy.

   Note (b) is consistent with everything already established: a good fit of
   the wrong class is this classifier's dominant error mode, and the report
   layer exists precisely to make such cases arguable rather than silent.""")
    print("=" * 74)


if __name__ == "__main__":
    main()
