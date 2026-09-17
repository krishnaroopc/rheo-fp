"""Cannibalisation check for the noise-aware tie rule.

Pre-registered in docs/tie_rule_preregistration.md (commit 7856d10), BEFORE
the rule was implemented. This script measures P2-P5; P1 (the Katzarova
monodisperse curves) is scored separately because those fits cost ~2-4 min
each under the Likhtman-McLeish bank entry.

WHAT IS UNDER TEST IS A SCORING RULE, NOT A BANK ENTRY. So the toggle here is
`identify.TIE_SCATTER_FLOOR`-independent: the rule is disabled by monkey-
patching `_apply_tie_rule` to a no-op, which is exactly what the code did
before it existed. Same curves, same seeds, same fits either way - the ONLY
difference is whether a within-scatter pair is re-ordered.

Protocol and thresholds are inherited from check_comb_cannibalisation.py,
including the correction that made that script honest: score BY HOW MUCH, not
merely whether the winner changed, and score the real data OF THE CLASSES MOST
AT RISK, not only the historical 6-curve benchmark.

Run: uv run python scripts/check_tie_rule.py [--n 30] [--restarts 12]
"""
from __future__ import annotations

import argparse
from collections import Counter

import numpy as np

from rheofp.data import synth
from rheofp.fitting import identify as ident

from check_comb_cannibalisation import (  # noqa: E402
    MARGIN_COLLAPSE_RATIO, REAL_CLASS_VALIDATION, REAL_TRUTH,
    margin_summary, planted_curves, preds_of,
)

# P5's pre-registered bound: the rule must change the winner on under 5% of
# synthetic curves, and is REJECTED above 10%. A rule that fires often has
# replaced AICc rather than guarding it.
P5_TARGET = 0.05
P5_REJECT = 0.10


def score_both(curves, n_restarts):
    """Fit each curve ONCE; return (off, on) scored lists.

    The tie rule re-orders a ranking - it never changes a fit. So running
    identify() twice would pay the (now dominant) Likhtman-McLeish fitting
    cost twice to compare two orderings of identical numbers, and would also
    admit the possibility of the two passes differing for some reason OTHER
    than the rule. Fitting once and applying the rule to the stored ranking is
    both cheaper and a stricter comparison.

    identify() applies the rule internally, so the returned ranking is the
    "on" answer; the "off" answer is recovered as the AICc-minimal entry,
    which is what the code returned before the rule existed.
    """
    off, on = [], []
    for w, Gp, Gpp in curves:
        r = ident.identify(w, Gp, Gpp, n_restarts=n_restarts)
        ranking = r["ranking"]
        on_margin = (float(ranking[1]["delta"]) if len(ranking) > 1
                     else float("inf"))
        on.append((r["best"], on_margin))
        by_aicc = sorted(ranking, key=lambda x: x["aicc"])
        off_margin = (by_aicc[1]["aicc"] - by_aicc[0]["aicc"]
                      if len(by_aicc) > 1 else float("inf"))
        off.append((by_aicc[0]["name"], float(off_margin)))
    return off, on


def real_data_both(n_restarts, truth_map):
    """As score_both, over a real-data truth map."""
    from rheofp.io.data import load_npz
    hits_b = hits_a = total = 0
    det_b, det_a = [], []
    for path, truth in truth_map.items():
        ds = load_npz(path)
        for sample, expected in truth.items():
            rec = ds.get(sample)
            total += 1
            if rec is None:
                det_b.append((sample, "MISSING", expected, float("nan")))
                det_a.append((sample, "MISSING", expected, float("nan")))
                continue
            r = ident.identify(rec["omega"], rec["Gp"], rec["Gpp"],
                               n_restarts=n_restarts)
            ranking = r["ranking"]
            ma = (float(ranking[1]["delta"]) if len(ranking) > 1
                  else float("inf"))
            by_aicc = sorted(ranking, key=lambda x: x["aicc"])
            mb = (by_aicc[1]["aicc"] - by_aicc[0]["aicc"]
                  if len(by_aicc) > 1 else float("inf"))
            gb, ga = by_aicc[0]["name"], r["best"]
            hits_b += gb == expected
            hits_a += ga == expected
            det_b.append((sample, gb, expected, float(mb)))
            det_a.append((sample, ga, expected, ma))
            print(f"    {sample:<16} {gb:<18} -> {ga:<18}"
                  f"{'  CHANGED' if gb != ga else ''}", flush=True)
    return (hits_b, hits_a, total, det_b, det_a)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--restarts", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20260917)
    args = ap.parse_args(argv)

    classes = list(synth.ALL_CLASSES)
    print("Cannibalisation check: noise-aware tie rule")
    print(f"  n={args.n} planted single curves per class, seed={args.seed}, "
          f"restarts={args.restarts}")
    print(f"  bank: {len(ident.ALL_MODELS)} candidates (UNCHANGED by this rule)")
    print()

    curves = {c: planted_curves(c, args.n, args.seed + i)
              for i, c in enumerate(classes)}

    before, after = {}, {}
    for c in classes:
        print(f"  scoring {c}...", flush=True)
        before[c], after[c] = score_both(curves[c], args.restarts)

    print("Real data (6-curve benchmark)...", flush=True)
    real_b, real_a, real_total, real_detail_b, real_detail_a = real_data_both(
        args.restarts, REAL_TRUTH)
    print("Real data of at-risk classes (stars)...", flush=True)
    risk_b, risk_a, risk_total, risk_detail_b, risk_detail_a = real_data_both(
        args.restarts, REAL_CLASS_VALIDATION)

    # ---- P4: per-class cannibalisation ----
    print()
    print("=" * 72)
    print("P4  PER-CLASS HIT COUNTS (rule off -> on)")
    print("=" * 72)
    print(f"{'class':<20} {'off':>5} {'on':>5} {'d':>4} "
          f"{'margin off':>11} {'margin on':>10} {'ratio':>6}   changed-to")
    tot_b = tot_a = 0
    regressions, margin_losses = [], []
    for c in classes:
        pb, pa = preds_of(before[c]), preds_of(after[c])
        b = sum(p == c for p in pb)
        a = sum(p == c for p in pa)
        tot_b += b
        tot_a += a
        mb, ma = margin_summary(before[c], c), margin_summary(after[c], c)
        ratio = (ma / mb) if (np.isfinite(mb) and mb > 0
                              and np.isfinite(ma)) else float("nan")
        stolen = Counter(p for p, q in zip(pa, pb) if q == c and p != c)
        note = ", ".join(f"{k}x{v}" for k, v in stolen.most_common()) or "-"
        flag = ""
        if a < b - 1:
            regressions.append((c, b, a, note))
            flag = "  <-- LOST >1"
        elif a < b:
            flag = "  <-- lost 1 (within budget)"
        elif np.isfinite(ratio) and ratio < MARGIN_COLLAPSE_RATIO:
            margin_losses.append((c, mb, ma, ratio))
            flag = "  <-- MARGIN"
        print(f"{c:<20} {b:>5} {a:>5} {a-b:>+4} {mb:>11.1f} {ma:>10.1f} "
              f"{ratio:>6.2f}   {note}{flag}")
    n_tot = args.n * len(classes)
    acc_b, acc_a = tot_b / n_tot, tot_a / n_tot
    print(f"{'OVERALL':<20} {tot_b:>5} {tot_a:>5} {tot_a-tot_b:>+4}"
          f"   ({acc_b:.3f} -> {acc_a:.3f})")

    # ---- P5: how often does it fire ----
    n_changed = sum(pb != pa
                    for c in classes
                    for pb, pa in zip(preds_of(before[c]), preds_of(after[c])))
    frac = n_changed / n_tot
    print()
    print("=" * 72)
    print("P5  HOW OFTEN THE RULE CHANGES THE WINNER")
    print("=" * 72)
    print(f"  {n_changed}/{n_tot} synthetic curves = {frac:.1%}  "
          f"(target < {P5_TARGET:.0%}, reject > {P5_REJECT:.0%})")

    # ---- P2 / P3: real data ----
    def show(title, detail_b, detail_a):
        print()
        print("=" * 72)
        print(title)
        print("=" * 72)
        print(f"{'sample':<16} {'truth':<18} {'off':<18} {'on':<18} margin")
        for (s, gb, exp, mb), (_, ga, _, ma) in zip(detail_b, detail_a):
            flag = "" if gb == ga else "  <-- CHANGED"
            print(f"{s:<16} {exp:<18} {gb:<18} {ga:<18} "
                  f"{mb:>6.1f}->{ma:<6.1f}{flag}")

    show("P2  6-CURVE BENCHMARK", real_detail_b, real_detail_a)
    print(f"  {real_b}/{real_total} -> {real_a}/{real_total}")
    show("P3  REAL DATA OF AT-RISK CLASSES (stars)", risk_detail_b,
         risk_detail_a)
    print(f"  {risk_b}/{risk_total} -> {risk_a}/{risk_total}")

    # ---- verdict against the pre-registered criteria ----
    print()
    print("=" * 72)
    print("VERDICT against docs/tie_rule_preregistration.md")
    print("=" * 72)
    fails = []
    if real_a < real_total:
        fails.append(f"P2 FAILED: benchmark {real_a}/{real_total}, must be 6/6")
    if risk_a < risk_b:
        fails.append(f"P3 FAILED: at-risk real data {risk_b} -> {risk_a}")
    if regressions:
        fails.append("P4 FAILED: " + ", ".join(
            f"{c} {b}->{a}" for c, b, a, _ in regressions))
    if acc_a < acc_b:
        fails.append(f"P4 FAILED: overall accuracy {acc_b:.3f} -> {acc_a:.3f}")
    if frac > P5_REJECT:
        fails.append(f"P5 FAILED: rule fires on {frac:.1%}, reject above "
                     f"{P5_REJECT:.0%}")
    if margin_losses:
        print("  NOTE margin collapse (not itself a rejection criterion "
              "for this rule, but recorded):")
        for c, mb, ma, ratio in margin_losses:
            print(f"    {c}: {mb:.1f} -> {ma:.1f} (x{ratio:.2f})")
    if fails:
        print("  REJECTED. The rule must be reverted.")
        for f in fails:
            print(f"    {f}")
    else:
        print("  P2-P5 PASS. (P1 is scored separately - see the Katzarova run.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
