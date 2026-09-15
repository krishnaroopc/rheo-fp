"""Cannibalisation check: does adding `comb` to identify()'s bank cost anything?

PRE-REGISTERED PROTOCOL, identical discipline to BSW (2026-09-03),
wormlike_micelle (2026-09-04), the has_shoulder removal (2026-09-07) and
`star` (2026-09-09):

  1. Generate N planted curves per existing class with a fixed seed.
  2. Score them through identify() with the CURRENT 10-model bank.
  3. Score the SAME curves (identical seeds) with the 11-model bank that adds
     `comb`.
  4. Report per-class hit counts before and after. A class that loses correct
     answers has been cannibalised.
  5. Score planted COMB curves both ways - the new class must be reachable and
     must not already be absorbed by `branched` or `star`.
  6. Real data must stay 6/6.

The result is reported to the user BEFORE `COMB_MODELS` is wired into
`ALL_MODELS`. Nothing here mutates the shipped bank permanently; the 11-model
bank is patched in and removed within this process only.

Run: python scripts/check_comb_cannibalisation.py [--n 30] [--restarts 12]

WHY THE RISK IS HIGHER HERE THAN IT WAS FOR `star`, and why this check is the
gate rather than a formality:

  * `comb` is a BROAD-SPECTRUM model at k=5 joining a ballot that already
    carries BSW (`branched`) at k=5. That is the closest match in both
    flexibility and parameter count the bank has ever had to absorb.
  * BSW silently absorbed 25/30 planted star melts before `star` existed - the
    documented "good fit of the WRONG class" failure. A comb's hierarchical
    two-feature spectrum is, if anything, closer to what BSW's two power-law
    wedges were designed to represent than a star's is.
  * The risk runs BOTH ways. `branched` may absorb combs (making the new class
    unreachable - the wormlike_micelle failure), or `comb`, having a genuine
    arm-plus-backbone structure, may steal real LCB melts from `branched`.
    Pivokonsky's two LDPE curves in the real-data set are the direct test of
    the second, and they are exactly the curves `branched` exists to get right.

A THIRD RISK SPECIFIC TO THIS CLASS: `comb` and `star` share arm-retraction
physics. A comb with a very short backbone is nearly a star, and `star`'s own
docstring records that it already sits in a degenerate cluster with zimm and
rouse_screened. Watch the star row specifically.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

import numpy as np

from rheofp.data import synth
from rheofp.fitting import identify as ident
from rheofp.io.data import load_npz
from rheofp.models.comb import (COMB_MODELS, Q_FIXED, comb_spectrum,
                                phi_b_from_architecture)

# Ground truth for the real literature curves, copied from
# scripts/eval_real_data.py so the two cannot silently drift apart.
REAL_TRUTH = {
    "data/darby2022.npz": {
        "SY184_10-1": "cured_elastomer",
        "Solaris_1-1": "cured_elastomer",
        "EF0030_1-1": "cured_elastomer",
    },
    "data/tixier2004.npz": {"Tixier2004_gel": "critical_gel"},
    "data/pivo2006.npz": {"E": "branched", "B": "branched"},
}

# >>> THE SECOND FLAW THAT MADE THIS SCRIPT LIE, 2026-09-14. <<<
# REAL_TRUTH above is the 6-curve benchmark, and it contains NO STAR CURVE.
# So "real data holds 6/6" was true and meaningless for a candidate whose
# whole risk was impersonating a star. The damage only appeared when MM1998's
# seven real four-arm polyisoprene stars were scored by hand afterwards:
# `star` 5/7 -> 4/7, with PI4_Ma47k flipped to `comb`.
#
# Any new candidate must be scored against the real data of the classes it is
# most likely to absorb, not only against the historical benchmark. These are
# curves whose architecture is known independently from synthesis.
REAL_CLASS_VALIDATION = {
    "data/mm1998.npz": {
        "PI4_Ma11k": "star", "PI4_Ma17k": "star", "PI4_Ma36k": "star",
        "PI4_Ma44k": "star", "PI4_Ma47k": "star",
        # Ma95k and Ma105k are KNOWN misses even without comb (branched wins;
        # their terminal zone is truncated). Listed so a change in them is
        # visible, but they were already wrong - see CLAUDE.md.
        "PI4_Ma95k": "star", "PI4_Ma105k": "star",
    },
    "data/pryke2002.npz": {"PBD3_Ma38k": "star", "PBD3_Ma78k": "star"},
}

# Planted-comb parameter ranges. s_a is bounded below at 4 for the same reason
# star.Z_BOUNDS is: under ~4 entanglements there is no retraction barrier worth
# the name and the architecture stops being detectable. s_b spans the
# well-entangled cross-bars ML1999 studied (its Table 2 fits land at 22-34).
COMB_S_A = (4.0, 16.0)
COMB_S_B = (15.0, 60.0)
COMB_LOG_G0 = (4.5, 6.5)
COMB_LOG_TAU_E = (-7.0, -3.0)
# phi_b is NOT drawn independently: it is fixed by the architecture as
# s_b / (s_b + 2 q s_a). Drawing it freely would plant molecules that cannot
# exist, and the self-recovery number would then mean nothing. A modest
# multiplicative jitter stands in for polydispersity and for the comb-vs-H
# ambiguity, both of which break the identity in real samples (ML1999's own
# Table 2 fits phi_b well away from the synthesis value on its less
# monodisperse samples).
COMB_PHI_B_JITTER = 0.15

# A class keeps its curves but its median winning margin falls below this
# fraction of what it was -> flagged as a MARGIN COLLAPSE and the verdict
# fails. 0.5 (a halving) is deliberately loose: on MM1998 the real collapse
# was 194->7.6, a ratio of 0.04, so anything remotely near this bound is
# already severe. Not tuned on the synthetic population.
MARGIN_COLLAPSE_RATIO = 0.5


def planted_curves(name, n, seed):
    """n single cropped noisy curves of class `name`, reproducible by seed.

    Single curves (not stacks) because the bank is what is under test here,
    not the stack resolver - and a single cropped noisy curve is the hardest
    case, which is what every earlier check used.
    """
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        ex = synth.make_example(rng, name, n_curves=1)
        w, Gp, Gpp, _ = ex["curves"][0]
        out.append((w, Gp, Gpp))
    return out


def planted_comb_curves(n, seed):
    """Planted comb curves.

    synth.py cannot generate `comb` yet (closing that gap is the step AFTER
    this check passes, exactly as it was for `star`), so draw directly from the
    model's own ranges and apply the SAME window cropping and noise the
    generator uses, so the comparison is like-for-like.
    """
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        w = synth._omega_window(rng)
        s_a = rng.uniform(*COMB_S_A)
        s_b = rng.uniform(*COMB_S_B)
        phi_b = phi_b_from_architecture(s_a, s_b, q=Q_FIXED)
        phi_b *= 1.0 + rng.uniform(-COMB_PHI_B_JITTER, COMB_PHI_B_JITTER)
        phi_b = float(np.clip(phi_b, 0.05, 0.95))
        G_0 = 10.0 ** rng.uniform(*COMB_LOG_G0)
        tau_e = 10.0 ** rng.uniform(*COMB_LOG_TAU_E)
        Gp, Gpp = comb_spectrum(w, G_0, s_a, s_b, phi_b, tau_e)
        Gp, Gpp = synth._add_noise(rng, Gp, Gpp)
        out.append((w, Gp, Gpp))
    return out


def score(curves, n_restarts):
    """Run identify() over curves, returning (predicted class, margin) pairs.

    >>> THE MARGIN IS NOT DECORATION - ITS ABSENCE IS WHY THIS SCRIPT LIED. <<<
    The first version of this function returned bare class names, so the
    report could only answer "did the winner change?". On 2026-09-14 it
    reported `star` 30/30 unchanged and the check was read as safe. Wiring
    `comb` in then cost `star` a real-data sample (MM1998 5/7 -> 4/7) and
    collapsed the surviving winning margins from dAICc 194-225 down to
    7.6-27.4 - a competitor moving from "no support whatsoever" to "live
    contender" while the winner never changed, i.e. entirely invisible here.

    `margin` is the winner's dAICc to the runner-up: how decisively the call
    was made. A class can keep every curve and still be gutted.
    """
    out = []
    for w, Gp, Gpp in curves:
        r = ident.identify(w, Gp, Gpp, n_restarts=n_restarts)
        ranking = r.get("ranking") or []
        margin = float(ranking[1]["delta"]) if len(ranking) > 1 else float("inf")
        out.append((r["best"], margin))
    return out


def preds_of(scored):
    return [name for name, _ in scored]


def margin_summary(scored, cls):
    """Median winning margin over the curves this class actually won."""
    kept = [m for name, m in scored if name == cls and np.isfinite(m)]
    return float(np.median(kept)) if kept else float("nan")


def with_comb_bank():
    """Patch `comb` into the module-level bank. Reversed in a finally block."""
    original = ident.ALL_MODELS
    ident.ALL_MODELS = {**original, **COMB_MODELS}
    return original


def restore_bank(original):
    ident.ALL_MODELS = original


def real_data_hits(n_restarts, truth_map=None):
    """Score real curves, carrying the winning MARGIN alongside the label.

    `truth_map` defaults to the 6-curve benchmark; pass REAL_CLASS_VALIDATION
    to score the per-class real data instead. Both are run by main() - see the
    comment on REAL_CLASS_VALIDATION for why the benchmark alone is not enough.
    """
    truth_map = REAL_TRUTH if truth_map is None else truth_map
    hits, total, detail = 0, 0, []
    for path, truth in truth_map.items():
        ds = load_npz(path)
        for sample, expected in truth.items():
            rec = ds.get(sample)
            if rec is None:
                detail.append((sample, "MISSING", expected, float("nan")))
                total += 1
                continue
            r = ident.identify(rec["omega"], rec["Gp"], rec["Gpp"],
                               n_restarts=n_restarts)
            got = r["best"]
            ranking = r.get("ranking") or []
            margin = (float(ranking[1]["delta"]) if len(ranking) > 1
                      else float("inf"))
            total += 1
            hits += got == expected
            detail.append((sample, got, expected, margin))
    return hits, total, detail


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30,
                    help="planted curves per class (default 30)")
    ap.add_argument("--restarts", type=int, default=12,
                    help="identify() restarts per candidate (default 12)")
    ap.add_argument("--seed", type=int, default=20260914)
    args = ap.parse_args(argv)

    existing = list(synth.ALL_CLASSES)
    print("Pre-registered cannibalisation check for `comb`")
    print(f"  n={args.n} planted single curves per class, seed={args.seed}, "
          f"restarts={args.restarts}")
    print(f"  existing bank: {len(ident.ALL_MODELS)} candidates")
    print()

    # Same seeds for both banks -> identical curves, so any difference is the
    # bank and nothing else.
    curves = {c: planted_curves(c, args.n, args.seed + i)
              for i, c in enumerate(existing)}
    comb_curves = planted_comb_curves(args.n, args.seed + 999)

    print("Scoring existing classes with the CURRENT bank...", flush=True)
    before = {c: score(curves[c], args.restarts) for c in existing}

    print("Scoring planted COMB curves with the CURRENT bank "
          "(what absorbs them today)...", flush=True)
    comb_before = score(comb_curves, args.restarts)

    print("Real data with the current bank...", flush=True)
    real_hits_before, real_total, real_detail_before = real_data_hits(
        args.restarts)
    print("Real data OF THE AT-RISK CLASSES, current bank...", flush=True)
    risk_hits_before, risk_total, risk_detail_before = real_data_hits(
        args.restarts, REAL_CLASS_VALIDATION)

    original = with_comb_bank()
    try:
        print(f"Scoring the SAME curves with the +comb bank "
              f"({len(ident.ALL_MODELS)} candidates)...", flush=True)
        after = {c: score(curves[c], args.restarts) for c in existing}

        print("Scoring planted COMB curves with the +comb bank...", flush=True)
        comb_after = score(comb_curves, args.restarts)

        print("Real data with the +comb bank...", flush=True)
        real_hits_after, _, real_detail_after = real_data_hits(args.restarts)

        print("Real data OF THE AT-RISK CLASSES, +comb bank...", flush=True)
        risk_hits_after, _, risk_detail_after = real_data_hits(
            args.restarts, REAL_CLASS_VALIDATION)
    finally:
        restore_bank(original)

    # ---- report ----
    print()
    print("=" * 72)
    print("PER-CLASS HIT COUNTS (planted class recovered by identify)")
    print("=" * 72)
    print(f"{'class':<20} {'before':>7} {'after':>6} {'d':>4} "
          f"{'margin b':>9} {'margin a':>9} {'ratio':>6}   stolen-by (after)")
    total_b = total_a = 0
    regressions = []
    margin_losses = []
    for c in existing:
        pb, pa = preds_of(before[c]), preds_of(after[c])
        b = sum(p == c for p in pb)
        a = sum(p == c for p in pa)
        total_b += b
        total_a += a
        mb = margin_summary(before[c], c)
        ma = margin_summary(after[c], c)
        ratio = (ma / mb) if (np.isfinite(mb) and mb > 0
                              and np.isfinite(ma)) else float("nan")
        stolen = Counter(p for p, q in zip(pa, pb) if q == c and p != c)
        note = ", ".join(f"{k}x{v}" for k, v in stolen.most_common()) or "-"
        flag = ""
        if a < b:
            regressions.append((c, b, a, note))
            flag = "  <-- LOST"
        elif np.isfinite(ratio) and ratio < MARGIN_COLLAPSE_RATIO:
            margin_losses.append((c, mb, ma, ratio))
            flag = "  <-- MARGIN"
        print(f"{c:<20} {b:>7} {a:>6} {a-b:>+4} {mb:>9.1f} {ma:>9.1f} "
              f"{ratio:>6.2f}   {note}{flag}")
    n_tot = args.n * len(existing)
    print(f"{'OVERALL':<20} {total_b:>7} {total_a:>6} {total_a-total_b:>+4}"
          f"   ({total_b/n_tot:.3f} -> {total_a/n_tot:.3f})")
    print()
    print("  'margin' = median dAICc from the winner to the runner-up, over the")
    print("  curves that class actually won. A class can keep EVERY curve and")
    print("  still be gutted - that is what this column exists to catch, and")
    print("  its absence is why the 2026-09-14 check reported `star` 30/30")
    print("  unchanged while real-data margins fell from 194-225 to 7.6-27.4.")

    print()
    print("=" * 72)
    print("PLANTED COMB CURVES")
    print("=" * 72)
    cb = Counter(preds_of(comb_before))
    ca = Counter(preds_of(comb_after))
    print("  with the current bank (comb absent - what absorbs it):")
    for k, v in cb.most_common():
        print(f"      {k:<20} {v:>3}/{args.n}")
    print("  with the +comb bank:")
    for k, v in ca.most_common():
        print(f"      {k:<20} {v:>3}/{args.n}")
    print(f"  comb self-recovery: {ca.get('comb', 0)}/{args.n}")

    print()
    print("=" * 72)
    print("REAL DATA (must stay 6/6)")
    print("=" * 72)
    for (s, gb, e, mb), (_, ga, _, ma) in zip(real_detail_before,
                                              real_detail_after):
        mark = "OK " if ga == e else "FAIL"
        change = "" if ga == gb else f"   CHANGED from {gb}"
        print(f"  {mark} {s:<16} expected {e:<16} got {ga:<16} "
              f"margin {mb:>7.1f} -> {ma:>7.1f}{change}")
    print(f"  before: {real_hits_before}/{real_total}   "
          f"after: {real_hits_after}/{real_total}")

    # The real data of the classes this candidate is most likely to absorb.
    # REAL_TRUTH above has no star curve; this is what caught the damage.
    print()
    print("=" * 72)
    print("REAL DATA OF THE CLASSES MOST AT RISK (the check that was missing)")
    print("=" * 72)
    for (s, gb, e, mb), (_, ga, _, ma) in zip(risk_detail_before,
                                              risk_detail_after):
        mark = "OK " if ga == e else "FAIL"
        change = "" if ga == gb else f"   CHANGED from {gb}"
        print(f"  {mark} {s:<16} expected {e:<16} got {ga:<16} "
              f"margin {mb:>7.1f} -> {ma:>7.1f}{change}")
    print(f"  before: {risk_hits_before}/{risk_total}   "
          f"after: {risk_hits_after}/{risk_total}")

    print()
    print("=" * 72)
    print("VERDICT")
    print("=" * 72)
    ok = True
    if regressions:
        ok = False
        print("  CANNIBALISATION DETECTED - these classes lost correct answers:")
        for c, b, a, note in regressions:
            print(f"    {c}: {b} -> {a}   (to: {note})")
    else:
        print("  No existing class lost a correct answer.")
    if margin_losses:
        ok = False
        print(f"  MARGIN COLLAPSE (kept the curves, lost the certainty - "
              f"median dAICc fell below {MARGIN_COLLAPSE_RATIO:.0%}):")
        for c, mb, ma, ratio in margin_losses:
            print(f"    {c}: {mb:.1f} -> {ma:.1f}  ({ratio:.2f}x)")
    else:
        print("  No class suffered a margin collapse.")
    if real_hits_after < real_total:
        ok = False
        print(f"  REAL DATA REGRESSED: {real_hits_after}/{real_total}")
    else:
        print(f"  Real data holds at {real_hits_after}/{real_total}.")
    if risk_hits_after < risk_hits_before:
        ok = False
        print(f"  >>> AT-RISK REAL DATA REGRESSED: {risk_hits_before}"
              f"/{risk_total} -> {risk_hits_after}/{risk_total} <<<")
        print("      This is the check whose ABSENCE let the 2026-09-14 run")
        print("      report `comb` as safe while it cost `star` MM1998 5/7->4/7.")
    else:
        print(f"  At-risk real data holds at {risk_hits_after}/{risk_total}.")
    if ca.get("comb", 0) == 0:
        ok = False
        print("  `comb` is UNREACHABLE - absorbed by another class even when "
              "present in the bank.")
    else:
        print(f"  `comb` is reachable ({ca.get('comb', 0)}/{args.n} "
              f"self-recovery).")
    print()
    print("  => " + ("SAFE to wire into ALL_MODELS."
                     if ok else "DO NOT WIRE IN. Report to the user first."))
    print()
    print("  NOTE: a passing verdict is necessary, not sufficient. Read the")
    print("  per-class table for EXACT TIES (a class losing curves to `comb`")
    print("  at identical rms is a tie, not a loss - see the star check, where")
    print("  zimm 23->21 turned out to be two exact ties at dAICc 0.07/0.00).")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
