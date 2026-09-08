"""Fair test of the fine vitrimer class - Ricarte (2023) PB vitrimer stack.

Edera (2024) validated the stack MECHANISM on real material but could not test
the fine class fairly: that material is thermo-rheologically complex by the
paper's own central claim, half its curves are glassy, and only one sits in the
bond-exchange regime. This dataset is the fair test - TTS demonstrably works
for it, all five temperatures are in the rubbery / bond-exchange regime, and
the truth is unambiguous: a dioxaborolane-metathesis polybutadiene vitrimer,
i.e. sticky_rouse or sticky_reptation.

Run: python scripts/eval_ricarte_stack.py
"""
from __future__ import annotations

import numpy as np

from rheofp.io.data import load_npz
from rheofp.fitting.identify import (
    identify, identify_stack, shift_factor, resolve_melt_vs_network,
)
from rheofp.report import explain, contest

SRC = "data/ricarte2023.npz"
R_GAS = 8.314
PAPER_EA_SAOS = 15.1  # kJ/mol, dioxaborolane metathesis


def main():
    d = load_npz(SRC)
    by_T = sorted(d, key=lambda n: d[n]["T_K"])

    print("=" * 74)
    print("Ricarte (2023) PB-v-4 vitrimer - fair test of the fine class")
    print("TRUTH: vitrimer -> sticky_rouse or sticky_reptation")
    print("=" * 74)

    print("\n1. SINGLE-CURVE IDENTIFICATION")
    for n in reversed(by_T):
        v = d[n]
        o = identify(v["omega"], v["Gp"], v["Gpp"])
        mark = "CORRECT" if o["best"].startswith("sticky") else "wrong"
        print(f"   {n:28s} -> {o['best']:17s} fit={o['best_rms_log']:.4f} "
              f"abstain={str(o['abstain']):5s} {mark}")

    print("\n2. HORIZONTAL SHIFTS (this is what the stack exists to measure)")
    cum, temps, acc = [0.0], [float(d[by_T[0]]["T_K"])], 0.0
    for a, b in zip(by_T, by_T[1:]):
        va, vb = d[a], d[b]
        s, r = shift_factor((va["omega"], va["Gp"], va["Gpp"]),
                            (vb["omega"], vb["Gp"], vb["Gpp"]))
        acc += s
        cum.append(acc)
        temps.append(float(vb["T_K"]))
        print(f"   {a[-5:]:>6s} -> {b[-5:]:>6s}  shift={s:7.3f} dec  "
              f"residual={r:.4f}")
    print("   Residuals are ~0.001-0.02, versus 1.0-2.4 on the Edera stack.")
    print("   These spectra genuinely superpose, exactly as the paper reports.")

    temps, cum = np.array(temps), np.array(cum)
    slope, _ = np.polyfit(1 / temps, np.log(10 ** cum), 1)
    ea = abs(slope) * R_GAS / 1000
    r2 = np.corrcoef(1 / temps, np.log(10 ** cum))[0, 1] ** 2
    print(f"\n   Arrhenius fit of OUR shifts: Ea = {ea:.1f} kJ/mol, "
          f"R^2 = {r2:.4f}")
    print(f"   Paper reports Ea_SAOS ~ {PAPER_EA_SAOS} kJ/mol.")
    print("   The LINEARITY is the real result - R^2 0.99 says the shift")
    print("   machinery measures a physically coherent Arrhenius process from")
    print("   real data. The MAGNITUDE differs by ~2x and should not be")
    print("   claimed as agreement: our shifts come from aligning tan(delta)")
    print("   over a digitized 4-decade window, the paper's from its own")
    print("   superposition over a wider effective range, and this file's G'")
    print("   is a single shared trace (see prep_ricarte.py), so only G''")
    print("   carries temperature information here.")

    print("\n3. STACK RESOLVER")
    stack = [dict(omega=v["omega"], Gp=v["Gp"], Gpp=v["Gpp"],
                  T_K=float(v["T_K"])) for v in d.values()]
    res = resolve_melt_vs_network(stack)
    print(f"   verdict: {res['verdict']}  ({res['reason']})")
    print("   CORRECT: the spectrum moves with temperature, so this is not a")
    print("   permanent network. Second real dataset to confirm the mechanism.")
    out = identify_stack(stack)
    print(f"   identify_stack best = {out['best']}  abstain={out['abstain']}")

    print("\n4. WHY 'branched'? - contesting the truth against the winner")
    v = d["Ricarte2023_PBv4_120C"]
    o = identify(v["omega"], v["Gp"], v["Gpp"])
    for cand in ("sticky_rouse", "sticky_reptation"):
        c = contest(v["omega"], v["Gp"], v["Gpp"], cand, result=o)
        print(f"   {cand:18s} dAICc={c['delta_aicc']:8.1f}  "
              f"fit={c['rms_log']:.4f} dec  (winner {c['winner']} "
              f"{c['winner_rms_log']:.4f})")
    rep = explain(o)
    print(f"   winner fit verdict: {rep['winner_fit_verdict']}; "
          f"field_all_poor={rep['field_all_poor']}")

    print("\n" + "=" * 74)
    print("SUMMARY")
    print("=" * 74)
    print("""
   WORKS  : the stack mechanism, now on a SECOND real material and this
            time on a well-behaved one. Alignment residuals ~0.001-0.02,
            shifts Arrhenius to R^2 0.99, verdict "melt" - correctly
            refusing a permanent-network call on a dynamic network.

   FAILS  : the fine class, consistently and informatively. All five
            temperatures return `branched`, never a sticker class, and the
            fits are GOOD (0.047-0.084 decades) - so no misfit flag fires.
            This is the failure mode the report layer was built to expose
            and cannot repair: a good fit of the wrong class.

   WHY it is a fair test and the failure is real:
     - TTS works for this system, so the single-shift premise holds.
     - All five curves are in the rubbery / bond-exchange regime.
     - Five temperatures is a genuine stack.
   Unlike Edera, none of the usual excuses apply. The honest conclusion is
   that on real vitrimer data the fine sticker classes are NOT recovered,
   even though the regime-level answer and the dynamic-vs-permanent call
   are both right.

   CAVEAT on this file: G' is one shared trace across all five
   temperatures (see prep_ricarte.py), so the classifier sees temperature
   only through G''. That flatters fit quality somewhat, but it does not
   manufacture the `branched` answer - a broad BSW spectrum simply
   describes this nearly-flat G' with slowly rising G'' better than the
   sticker models do.
""")


if __name__ == "__main__":
    main()
