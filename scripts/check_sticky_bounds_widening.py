"""Does widening SR_BNDS / SREP_BNDS cost anything? Pre-registered check.

The oldest open item in next-actions, proposed 2026-09-07 and repeatedly
described there as "cheap and safe". This script is what makes that claim
testable rather than asserted, because the two sticker models carry k=4 - the
most flexible candidates in the bank - and freeing their bounds is exactly the
kind of change that silently steals curves from simpler classes.

WHY WIDENING WAS PROPOSED. scripts/diagnose_sticky_models.py (2026-09-07)
measured that the published bounds DEMONSTRABLY BIND on a real vitrimer:
freeing them improved sticky_rouse 0.203 -> 0.161 dec and sticky_reptation
0.390 -> 0.131 dec. Both then plateau far above BSW's 0.047, which is why the
user's decision was to keep the models and report the ambiguity rather than
replace them - but a bound that provably binds is still worth relieving on its
own merits, since it constrains every fit the model ever does, not just that
one curve.

The widened values are NOT invented here. They are the WIDE_SR / WIDE_SREP
bounds already used by the diagnosis script, minus its most extreme mode-count
ceilings - because that same diagnosis found sticky_reptation's Z "runs away to
any ceiling offered while its RMS stops moving: Z has become a nuisance
parameter buying nothing". Letting Z reach 2000 would buy nothing and cost
fitting time on every call, so the ceiling is raised to a level that relieves
binding without inviting runaway.

PRE-REGISTERED PROTOCOL, identical in shape to BSW (2026-09-03),
wormlike_micelle (2026-09-04), the has_shoulder removal (2026-09-07) and star
(2026-09-09):

  1. Generate N planted curves per class with fixed seeds.
  2. Score them through identify() with the CURRENT published bounds.
  3. Score the SAME curves (identical seeds) with the widened bounds.
  4. Report per-class hit counts before and after. A class that loses correct
     answers has been cannibalised.
  5. Real data must stay 6/6.

Nothing here mutates the shipped bounds permanently; they are patched in and
restored within this process only. The result goes to the user BEFORE
solutions.py is edited.

>>> PRE-REGISTERED EXPECTATION, written before running <<<

  * The two sticker classes should improve or hold. That is the point.
  * Every other class should be UNCHANGED or within noise. The sticker models
    are k=4, so AICc already penalises them; widening bounds does not change k,
    only the region the optimiser may search.
  * ACCEPT if: sticker classes do not regress, no other class loses more than
    ~1-2 curves, and real data stays 6/6.
  * REJECT if: any non-sticker class loses materially, or real data drops.
    "Cheap and safe" would then be simply false, and the bounds stay as they
    are - which is a perfectly good outcome for a check to produce.

Run: uv run python scripts/check_sticky_bounds_widening.py [--n 30] [--restarts 12]
"""
from __future__ import annotations

import argparse
from collections import Counter

import numpy as np

from rheofp.data import synth
from rheofp.fitting import identify as ident
from rheofp.io.data import load_npz
from rheofp.models import solutions

# Published bounds, for reference (solutions.py):
#   SR_BNDS   = [(0, 7), (0, 5), (-5, 1), (2, 150)]
#   SREP_BNDS = [(0, 8), (1, 6), (2, 200), (-2, 4)]
#
# Widened. Parameter order:
#   sticky_rouse     (Gs log, tau_s log, tau_R log, Nst modes)
#   sticky_reptation (Ge log, tau_st log, Z, tau_s log)
#
# Each change relieves a bound the diagnosis showed binding, without opening
# the runaway directions it also identified.
WIDE_SR = [(0, 9), (-3, 8), (-9, 4), (2, 1000)]
WIDE_SREP = [(0, 9), (-3, 9), (2, 600), (-6, 7)]

REAL_TRUTH = {
    "data/darby2022.npz": {
        "SY184_10-1": "cured_elastomer",
        "Solaris_1-1": "cured_elastomer",
        "EF0030_1-1": "cured_elastomer",
    },
    "data/tixier2004.npz": {"Tixier2004_gel": "critical_gel"},
    "data/pivo2006.npz": {"E": "branched", "B": "branched"},
}

STICKY = ("sticky_rouse", "sticky_reptation")


def planted_curves(name, n, seed):
    """n single cropped noisy curves of class `name`, reproducible by seed."""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        ex = synth.make_example(rng, name, n_curves=1)
        w, Gp, Gpp, _ = ex["curves"][0]
        out.append((w, Gp, Gpp))
    return out


def score(curves, n_restarts):
    return [ident.identify(w, Gp, Gpp, n_restarts=n_restarts)["best"]
            for w, Gp, Gpp in curves]


def widen_bounds():
    """Patch the widened bounds into identify()'s live bank.

    identify() reads ALL_MODELS, whose entries are (forward, p0, bounds, k)
    tuples built at import from solutions.MODELS. Rebuilding those two entries
    is what actually changes what the fitter may search - editing
    solutions.SR_BNDS alone would not, since the tuple already captured the
    old list.
    """
    original = ident.ALL_MODELS
    patched = dict(original)
    for name, new_bnds in (("sticky_rouse", WIDE_SR),
                           ("sticky_reptation", WIDE_SREP)):
        fwd, p0, _old, k = original[name]
        patched[name] = (fwd, p0, new_bnds, k)
    ident.ALL_MODELS = patched
    return original


def restore_bank(original):
    ident.ALL_MODELS = original


def real_data_hits(n_restarts):
    hits, total, detail = 0, 0, []
    for path, truth in REAL_TRUTH.items():
        ds = load_npz(path)
        for sample, expected in truth.items():
            rec = ds.get(sample)
            total += 1
            if rec is None:
                detail.append((sample, "MISSING", expected))
                continue
            got = ident.identify(rec["omega"], rec["Gp"], rec["Gpp"],
                                 n_restarts=n_restarts)["best"]
            hits += got == expected
            detail.append((sample, got, expected))
    return hits, total, detail


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--restarts", type=int, default=12)
    ap.add_argument("--seed", type=int, default=20260911)
    args = ap.parse_args(argv)

    classes = list(synth.ALL_CLASSES)
    print("Pre-registered check: widening SR_BNDS / SREP_BNDS")
    print(f"  n={args.n} planted single curves per class, seed={args.seed}, "
          f"restarts={args.restarts}")
    print(f"  bank: {len(ident.ALL_MODELS)} candidates, {len(classes)} classes")
    print(f"  SR_BNDS   {solutions.SR_BNDS}  ->  {WIDE_SR}")
    print(f"  SREP_BNDS {solutions.SREP_BNDS}  ->  {WIDE_SREP}")
    print()

    curves = {c: planted_curves(c, args.n, args.seed + i)
              for i, c in enumerate(classes)}

    print("Scoring with the CURRENT published bounds...", flush=True)
    before = {c: score(curves[c], args.restarts) for c in classes}
    print("Real data, current bounds...", flush=True)
    real_before, real_total, detail_before = real_data_hits(args.restarts)

    original = widen_bounds()
    try:
        print("Scoring the SAME curves with WIDENED bounds...", flush=True)
        after = {c: score(curves[c], args.restarts) for c in classes}
        print("Real data, widened bounds...", flush=True)
        real_after, _, detail_after = real_data_hits(args.restarts)
    finally:
        restore_bank(original)

    print()
    print("=" * 72)
    print("PER-CLASS HIT COUNTS (planted class recovered by identify)")
    print("=" * 72)
    print(f"{'class':<20} {'before':>7} {'after':>7} {'delta':>7}   "
          f"stolen-by (after)")
    tot_b = tot_a = 0
    regressions = []
    for c in classes:
        b = sum(p == c for p in before[c])
        a = sum(p == c for p in after[c])
        tot_b += b
        tot_a += a
        stolen = Counter(p for p, q in zip(after[c], before[c])
                         if q == c and p != c)
        note = ", ".join(f"{k}x{v}" for k, v in stolen.most_common()) or "-"
        flag = "  <-- LOST" if a < b else ""
        if a < b:
            regressions.append((c, b, a, note))
        print(f"{c:<20} {b:>7} {a:>7} {a-b:>+7}   {note}{flag}")

    n_tot = args.n * len(classes)
    print("-" * 72)
    print(f"{'OVERALL':<20} {tot_b:>7} {tot_a:>7} {tot_a-tot_b:>+7}   "
          f"({tot_b/n_tot:.3f} -> {tot_a/n_tot:.3f})")

    print()
    print("STICKER CLASSES (the ones this change is FOR)")
    for c in STICKY:
        b = sum(p == c for p in before[c])
        a = sum(p == c for p in after[c])
        print(f"  {c:<20} {b}/{args.n} -> {a}/{args.n}  ({a-b:+d})")

    print()
    print(f"REAL DATA  {real_before}/{real_total} -> {real_after}/{real_total}")
    for (s, g_b, exp), (_, g_a, _) in zip(detail_before, detail_after):
        change = "" if g_b == g_a else f"   CHANGED {g_b} -> {g_a}"
        mark = "ok " if g_a == exp else "MISS"
        print(f"  {mark} {s:<18} {g_a:<18} (expected {exp}){change}")

    print()
    print("=" * 72)
    print("VERDICT against the pre-registered rule")
    print("=" * 72)
    sticker_delta = sum(sum(p == c for p in after[c]) -
                        sum(p == c for p in before[c]) for c in STICKY)
    other_loss = sum(b - a for c, b, a, _ in
                     [(c, sum(p == c for p in before[c]),
                       sum(p == c for p in after[c]), None) for c in classes]
                     if c not in STICKY and a < b)
    print(f"  sticker classes net change : {sticker_delta:+d}")
    print(f"  non-sticker curves lost    : {other_loss}")
    print(f"  real data                  : {real_before} -> {real_after}"
          f" of {real_total}")
    ok = (sticker_delta >= 0 and other_loss <= 2
          and real_after >= real_before and real_after == real_total)
    print()
    if ok:
        print("  ACCEPT - widening is safe by the pre-registered criteria.")
    else:
        print("  REJECT - widening costs something. Leave the bounds alone;")
        print("  'cheap and safe' was an untested assertion and is now tested.")
    if regressions:
        print()
        print("  regressions:")
        for c, b, a, note in regressions:
            print(f"    {c}: {b} -> {a}   stolen by {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
