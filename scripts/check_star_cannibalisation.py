"""Cannibalisation check: does adding `star` to identify()'s bank cost anything?

PRE-REGISTERED PROTOCOL, same discipline as BSW (2026-09-03), wormlike_micelle
(2026-09-04) and the has_shoulder removal (2026-09-07):

  1. Generate N planted curves per existing class with a fixed seed.
  2. Score them through identify() with the CURRENT 9-model bank.
  3. Score the SAME curves (identical seeds) with the 10-model bank that adds
     `star`.
  4. Report per-class hit counts before and after. A class that loses correct
     answers has been cannibalised.
  5. Score planted STAR curves both ways - the new class must be reachable and
     must not already be absorbed by `branched`.
  6. Real data must stay 6/6.

The result is reported to the user BEFORE `STAR_MODELS` is wired into
`ALL_MODELS`. Nothing here mutates the shipped bank permanently; the 10-model
bank is patched in and removed within this process only.

Run: python scripts/check_star_cannibalisation.py [--n 30] [--restarts 12]

Why this matters here specifically (next-actions, star task): a star melt's
spectrum is BROAD, and `branched` is the 5-parameter BSW two-wedge spectrum,
which is also broad. The risk runs both ways - BSW may absorb star melts
(making the new class unreachable, the wormlike_micelle failure mode), or
`star` at k=3 may steal curves from `branched` on parsimony.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter

import numpy as np

from rheofp.data import synth
from rheofp.fitting import identify as ident
from rheofp.io.data import load_npz
from rheofp.models.star import STAR_MODELS

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


def planted_curves(name, n, seed):
    """n single cropped noisy curves of class `name`, reproducible by seed.

    Single curves (not stacks) because the bank is what is under test here,
    not the stack resolver - and a single cropped noisy curve is the hardest
    case, which is what the earlier checks used.
    """
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        ex = synth.make_example(rng, name, n_curves=1)
        w, Gp, Gpp, _ = ex["curves"][0]
        out.append((w, Gp, Gpp))
    return out


def score(curves, n_restarts):
    """Run identify() over curves, returning the list of predicted classes."""
    preds = []
    for w, Gp, Gpp in curves:
        r = ident.identify(w, Gp, Gpp, n_restarts=n_restarts)
        preds.append(r["best"])
    return preds


def with_star_bank():
    """Context-manager-ish patch: add `star` to the module-level bank."""
    original = ident.ALL_MODELS
    ident.ALL_MODELS = {**original, **STAR_MODELS}
    return original


def restore_bank(original):
    ident.ALL_MODELS = original


def real_data_hits(n_restarts):
    hits, total, detail = 0, 0, []
    for path, truth in REAL_TRUTH.items():
        ds = load_npz(path)
        for sample, expected in truth.items():
            rec = ds.get(sample)
            if rec is None:
                detail.append((sample, "MISSING", expected))
                total += 1
                continue
            r = ident.identify(rec["omega"], rec["Gp"], rec["Gpp"],
                               n_restarts=n_restarts)
            got = r["best"]
            total += 1
            hits += got == expected
            detail.append((sample, got, expected))
    return hits, total, detail


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30,
                    help="planted curves per class (default 30)")
    ap.add_argument("--restarts", type=int, default=12,
                    help="identify() restarts per candidate (default 12)")
    ap.add_argument("--seed", type=int, default=20260909)
    args = ap.parse_args(argv)

    existing = list(synth.ALL_CLASSES)
    print(f"Pre-registered cannibalisation check for `star`")
    print(f"  n={args.n} planted single curves per class, seed={args.seed}, "
          f"restarts={args.restarts}")
    print(f"  existing bank: {len(ident.ALL_MODELS)} candidates")
    print()

    # Same seeds for both banks -> identical curves, so any difference is the
    # bank and nothing else.
    curves = {c: planted_curves(c, args.n, args.seed + i)
              for i, c in enumerate(existing)}

    print("Scoring existing classes with the CURRENT bank...", flush=True)
    before = {c: score(curves[c], args.restarts) for c in existing}

    original = with_star_bank()
    try:
        print(f"Scoring the SAME curves with the +star bank "
              f"({len(ident.ALL_MODELS)} candidates)...", flush=True)
        after = {c: score(curves[c], args.restarts) for c in existing}

        # Planted stars, scored with the new bank (they are unreachable in the
        # old one by construction, but score them there too to show what
        # currently absorbs them).
        print("Scoring planted STAR curves...", flush=True)
        star_curves = planted_star_curves(args.n, args.seed + 999)
        star_after = score(star_curves, args.restarts)

        print("Real data with the +star bank...", flush=True)
        real_hits_after, real_total, real_detail_after = real_data_hits(args.restarts)
    finally:
        restore_bank(original)

    star_before = score(star_curves, args.restarts)
    print("Real data with the current bank...", flush=True)
    real_hits_before, _, real_detail_before = real_data_hits(args.restarts)

    # ---- report ----
    print()
    print("=" * 68)
    print("PER-CLASS HIT COUNTS (planted class recovered by identify)")
    print("=" * 68)
    print(f"{'class':<20} {'before':>8} {'after':>8} {'delta':>7}   stolen-by (after)")
    total_b = total_a = 0
    regressions = []
    for c in existing:
        b = sum(p == c for p in before[c])
        a = sum(p == c for p in after[c])
        total_b += b
        total_a += a
        stolen = Counter(p for p, q in zip(after[c], before[c])
                         if q == c and p != c)
        note = ", ".join(f"{k}x{v}" for k, v in stolen.most_common()) or "-"
        flag = "" if a >= b else "  <-- LOST"
        if a < b:
            regressions.append((c, b, a, note))
        print(f"{c:<20} {b:>8} {a:>8} {a-b:>+7}   {note}{flag}")
    n_tot = args.n * len(existing)
    print(f"{'OVERALL':<20} {total_b:>8} {total_a:>8} {total_a-total_b:>+7}"
          f"   ({total_b/n_tot:.3f} -> {total_a/n_tot:.3f})")

    print()
    print("=" * 68)
    print("PLANTED STAR CURVES")
    print("=" * 68)
    sb = Counter(star_before)
    sa = Counter(star_after)
    print(f"  with the current bank (star absent - what absorbs it):")
    for k, v in sb.most_common():
        print(f"      {k:<20} {v:>3}/{args.n}")
    print(f"  with the +star bank:")
    for k, v in sa.most_common():
        print(f"      {k:<20} {v:>3}/{args.n}")
    print(f"  star self-recovery: {sa.get('star', 0)}/{args.n}")

    print()
    print("=" * 68)
    print("REAL DATA (must stay 6/6)")
    print("=" * 68)
    for (s, gb, e), (_, ga, _) in zip(real_detail_before, real_detail_after):
        mark = "OK " if ga == e else "FAIL"
        change = "" if ga == gb else f"   CHANGED from {gb}"
        print(f"  {mark} {s:<16} expected {e:<16} got {ga}{change}")
    print(f"  before: {real_hits_before}/{real_total}   "
          f"after: {real_hits_after}/{real_total}")

    print()
    print("=" * 68)
    print("VERDICT")
    print("=" * 68)
    ok = True
    if regressions:
        ok = False
        print("  CANNIBALISATION DETECTED - these classes lost correct answers:")
        for c, b, a, note in regressions:
            print(f"    {c}: {b} -> {a}   (to: {note})")
    else:
        print("  No existing class lost a correct answer.")
    if real_hits_after < real_total:
        ok = False
        print(f"  REAL DATA REGRESSED: {real_hits_after}/{real_total}")
    else:
        print(f"  Real data holds at {real_hits_after}/{real_total}.")
    if sa.get("star", 0) == 0:
        ok = False
        print("  `star` is UNREACHABLE - absorbed by another class even when "
              "present in the bank.")
    else:
        print(f"  `star` is reachable ({sa.get('star', 0)}/{args.n} "
              f"self-recovery).")
    print()
    print("  => " + ("SAFE to wire into ALL_MODELS."
                     if ok else "DO NOT WIRE IN. Report to the user first."))
    return 0 if ok else 1


def planted_star_curves(n, seed):
    """Planted star curves. synth.py cannot generate `star` yet, so draw
    directly from the model's own parameter ranges and apply the SAME window
    cropping and noise the generator uses, so the comparison is like-for-like.
    """
    from rheofp.models.star import Z_BOUNDS, star_spectrum

    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        w = synth._omega_window(rng)
        G_N = 10.0 ** rng.uniform(4.5, 6.5)
        Z = rng.uniform(*Z_BOUNDS)
        # tau_e placed so the spectrum lands somewhere inside the window,
        # mirroring how sample_params anchors times to the generator window.
        tau_e = 10.0 ** rng.uniform(-7.0, -3.0)
        Gp, Gpp = star_spectrum(w, G_N, Z, tau_e)
        Gp, Gpp = synth._add_noise(rng, Gp, Gpp)
        out.append((w, Gp, Gpp))
    return out


if __name__ == "__main__":
    sys.exit(main())
