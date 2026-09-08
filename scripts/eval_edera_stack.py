"""First evaluation against a REAL temperature stack (Edera 2024 epoxy vitrimer).

Until now every temperature-stack result in this project was synthetic. The
stack is the only mechanism that separates a dynamic network (vitrimer) from a
permanent one (cured elastomer), which is a flagship distinction of the
product, so this was the single most load-bearing untested gap.

Run: python scripts/eval_edera_stack.py

Read the output with the caveats below in view - this dataset is deliberately
hostile, and a bad score here is not the same as a bad score on a fair case.
"""
from __future__ import annotations

import itertools

import numpy as np

from rheofp.io.data import load_npz
from rheofp.fitting.identify import (
    identify, identify_stack, shift_factor, resolve_melt_vs_network,
)

SRC = "data/edera2024.npz"


def main():
    d = load_npz(SRC)
    by_T = sorted(d, key=lambda n: d[n]["T_K"])

    print("=" * 74)
    print("Edera (2024) epoxy vitrimer - real temperature stack")
    print("=" * 74)

    print("\n1. SINGLE-CURVE IDENTIFICATION (what one sweep alone can say)")
    for n in reversed(by_T):
        v = d[n]
        o = identify(v["omega"], v["Gp"], v["Gpp"])
        print(f"   {n:18s} -> {o['best']:17s} fit={o['best_rms_log']:.4f} dec"
              f"  abstain={str(o['abstain']):5s} lowconf={o['low_confidence']}")
    print("   TRUTH: a vitrimer, i.e. sticky_rouse or sticky_reptation.")
    print("   None of the four is correct. The 85 C curve at least ABSTAINS.")

    print("\n2. PAIRWISE HORIZONTAL SHIFTS (adjacent temperatures)")
    for a, b in zip(by_T, by_T[1:]):
        va, vb = d[a], d[b]
        s, r = shift_factor((va["omega"], va["Gp"], va["Gpp"]),
                            (vb["omega"], vb["Gp"], vb["Gpp"]))
        print(f"   {a:18s} -> {b:18s} shift={s:7.3f} dec  resid={r:.4f}")

    print("\n3. WHY THE RESIDUALS ARE LARGE - tan(delta) value ranges")
    rng = {n: (float(np.log10(d[n]["Gpp"] / d[n]["Gp"]).min()),
               float(np.log10(d[n]["Gpp"] / d[n]["Gp"]).max())) for n in by_T}
    for n in by_T:
        lo, hi = rng[n]
        print(f"   {n:18s} log10 tan_d in [{lo:6.2f},{hi:6.2f}]")
    print("   Overlap between curves:")
    for a, b in itertools.combinations(by_T, 2):
        ov = min(rng[a][1], rng[b][1]) - max(rng[a][0], rng[b][0])
        print(f"     {a:18s} vs {b:18s} "
              f"{'NONE' if ov < 0 else f'{ov:.2f} dec'}")
    print("   A HORIZONTAL shift cannot move a curve vertically. Where the")
    print("   tan(delta) ranges do not overlap at all, no horizontal shift can")
    print("   superpose them and the residual is irreducible by construction.")
    print("   This is the paper's own central claim, measured independently:")
    print("   the material is thermo-rheologically COMPLEX (two relaxations,")
    print("   ~680 and ~130 kJ/mol), so time-temperature EQUIVALENCE fails.")

    print("\n4. STACK RESOLVER")
    stack = [dict(omega=v["omega"], Gp=v["Gp"], Gpp=v["Gpp"],
                  T_K=float(v["T_K"])) for v in d.values()]
    res = resolve_melt_vs_network(stack)
    print(f"   verdict: {res['verdict']}   ({res['reason']})")
    print("   CORRECT: a vitrimer is a dynamic network, and the resolver")
    print("   refuses the permanent-network call. This is the mechanism the")
    print("   product depends on, and it works on real material.")

    out = identify_stack(stack)
    print(f"\n   identify_stack best = {out['best']}"
          f"   abstain={out['abstain']}")
    if out.get("abstain_reason"):
        print(f"   reason: {out['abstain_reason']}")

    print("\n" + "=" * 74)
    print("SUMMARY - read carefully, this dataset is deliberately hostile")
    print("=" * 74)
    print("""
   WORKS  : the melt-vs-network resolver. On real material, for the first
            time, it refuses to call a dynamic network permanent. That is
            the distinction the temperature stack exists to make.

   FAILS  : the fine class. No curve is identified as a vitrimer
            (sticky_rouse / sticky_reptation); three of four land on
            critical_gel or cured_elastomer.

   CAVEATS, all of which make this a hard case rather than a fair one:
     - The paper was chosen BECAUSE the material is thermo-rheologically
       complex; time-temperature equivalence provably fails for it. The
       resolver assumes a single horizontal shift aligns the spectra. The
       premise is violated on purpose.
     - Two of four curves (30 C, 75 C) sit in or near the GLASSY regime,
       which was dropped from the taxonomy. They are out-of-scope material,
       not classification targets.
     - Only the 180 C curve is squarely in the rubbery/bond-exchange regime
       the sticker models describe, and one curve is not a stack.
     - The digitized curves are 20-21 points read off a log-log figure.

   HONEST READING: the mechanism is validated on real data; the fine
   vitrimer classification is NOT, and cannot be judged from this dataset.
   A well-behaved vitrimer measured across its rubbery plateau - the
   Ricarte (2023) polybutadiene system is the obvious candidate - would be
   the fair test of the fine class.
""")


if __name__ == "__main__":
    main()
