"""Can N_RESTARTS come down from 12? A pre-registered before/after check.

THE QUESTION. `identify()` fits every candidate with `N_RESTARTS = 12`
random-restart L-BFGS-B runs and keeps the best. That is roughly half of a
~88 s/curve call, and it is why the test suite now takes hours (test_report.py
alone ran 104 min; the whole identify()-heavy group ran 2h45m).

THE EVIDENCE THAT PROMPTED IT, and its limits. On Katzarova 2018's real
monodisperse polystyrenes the `reptation` fit converges by restart 2 -
restarts 3-12 cost 40-60 s each and change nothing:

    PS392   restarts  1 /  2 /  4 /  8 / 12   ->  rms 0.03154 every time, Z 28.90
    PS105   restarts  1                       ->  rms 0.02215, Z 9.64
                      2 /  4 /  8 / 12        ->  rms 0.02045, Z 9.40

That is n=2 curves of ONE model. `N_RESTARTS` is BANK-WIDE, and the
5-parameter models (`branched`, k=5; `comb`, k=5) have a harder search than
reptation's k=3 - they are the ones that might genuinely need the restarts.
Lowering it blind would be a science change wearing a speed change's clothes:
it could alter which class is reported, and that error would look like an
ordinary result. Hence this check rather than a one-line edit.

>>> PRE-REGISTERED CRITERION - write the outcome under OUTCOME below, and do
>>> NOT renegotiate this after seeing numbers. The tie-rule episode of
>>> 2026-09-17 (committed before its check, then rejected by it) is the
>>> precedent this protocol exists to avoid. Gate the change ON the check.

    ADOPT a lower value only if BOTH hold:
      P1  every class's winner is unchanged on n planted curves per class,
          at identical seeds, against the 12-restart reference. A single
          flipped winner fails P1 - the point is that the search is already
          converged, so ANY change means it was not.
      P2  the real-data benchmark scores the same as at 12 restarts
          (currently 6/6).
    If P1 fails at 4 but passes at 8, that is a real finding: report the
    lowest value that passes, do not force the largest saving.

Run:  uv run python scripts/check_restart_count.py --n 30 --candidates 4 2
      (add --classes zimm star ... to restrict; default is all ten)

Cost note: the reference arm at 12 restarts is the expensive one. --n 30 over
ten classes is ~300 identify() calls at ~88 s = several hours. Start with
--n 5 to smoke-test the harness, then run the real one.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter

from rheofp.data import synth
from rheofp.fitting import identify as ident
from rheofp.io.data import load_npz

OUT_JSON = "docs/restart_count_check.json"

# Same real-data benchmark the star/comb cannibalisation checks use, so the
# P2 number is comparable with those runs.
REAL_TRUTH = {
    "data/darby2022.npz": {
        "SY184_10-1": "cured_elastomer",
        "Solaris_1-1": "cured_elastomer",
        "EF0030_1-1": "cured_elastomer",
    },
    "data/tixier2004.npz": {"Tixier2004_gel": "critical_gel"},
    "data/pivo2006.npz": {"E": "branched", "B": "branched"},
}

REFERENCE_RESTARTS = ident.N_RESTARTS  # 12


def planted_curves(name, n, seed):
    """n single cropped noisy curves of class `name`, reproducible by seed.

    Single curves, not stacks: the bank is what is under test, and a single
    cropped noisy curve is the hardest case. Identical seeds across arms is
    what makes the comparison paired rather than two independent samples.
    """
    rng = __import__("numpy").random.default_rng(seed)
    out = []
    for _ in range(n):
        ex = synth.make_example(rng, name, n_curves=1)
        w, Gp, Gpp, _ = ex["curves"][0]
        out.append((w, Gp, Gpp))
    return out


def score(curves, n_restarts):
    return [ident.identify(w, Gp, Gpp, n_restarts=n_restarts)["best"]
            for w, Gp, Gpp in curves]


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
            got = ident.identify(rec["omega"], rec["Gp"], rec["Gpp"],
                                 n_restarts=n_restarts)["best"]
            total += 1
            hits += got == expected
            detail.append((sample, got, expected))
    return hits, total, detail


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30,
                    help="planted curves per class (default 30)")
    ap.add_argument("--candidates", type=int, nargs="+", default=[4, 2],
                    help="restart counts to test against the 12 reference")
    ap.add_argument("--classes", nargs="*", default=list(synth.ALL_CLASSES))
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--out", default=OUT_JSON)
    args = ap.parse_args(argv)

    arms = [REFERENCE_RESTARTS] + [c for c in args.candidates
                                   if c != REFERENCE_RESTARTS]
    print(f"reference = {REFERENCE_RESTARTS} restarts; "
          f"candidates = {arms[1:]}; n = {args.n}/class\n")

    # Identical curves for every arm - drawn once, per class.
    curves = {c: planted_curves(c, args.n, args.seed + i)
              for i, c in enumerate(args.classes)}

    preds = {arm: {} for arm in arms}
    timing = {}
    for arm in arms:
        t0 = time.time()
        for c in args.classes:
            preds[arm][c] = score(curves[c], arm)
            agree = sum(p == q for p, q in
                        zip(preds[arm][c], preds[arms[0]][c]))
            print(f"  restarts={arm:>2}  {c:<18} "
                  f"self={preds[arm][c].count(c):>3}/{args.n}  "
                  f"same-as-ref={agree:>3}/{args.n}", flush=True)
        timing[arm] = time.time() - t0
        print(f"  -> arm {arm} took {timing[arm]/60:.1f} min\n", flush=True)

    real = {}
    for arm in arms:
        hits, total, detail = real_data_hits(arm)
        real[arm] = {"hits": hits, "total": total, "detail": detail}
        print(f"real data @ {arm:>2} restarts: {hits}/{total}")

    # --- verdict against the pre-registered criterion ---
    print("\n=== P1 (every class's winner unchanged) ===")
    verdict = {}
    for arm in arms[1:]:
        flips = {}
        for c in args.classes:
            diff = [(i, a, b) for i, (a, b) in
                    enumerate(zip(preds[arms[0]][c], preds[arm][c])) if a != b]
            if diff:
                flips[c] = diff
        p1 = not flips
        p2 = real[arm]["hits"] == real[arms[0]]["hits"]
        verdict[arm] = {"P1": p1, "P2": p2, "flips": flips,
                        "speedup": (timing[arms[0]] / timing[arm]
                                    if timing[arm] else None)}
        print(f"  restarts={arm:>2}  P1={'PASS' if p1 else 'FAIL'}  "
              f"P2={'PASS' if p2 else 'FAIL'}  "
              f"speedup={verdict[arm]['speedup']:.2f}x")
        for c, diff in flips.items():
            got = Counter(b for _, _, b in diff)
            print(f"      {c}: {len(diff)} flipped -> {dict(got)}")

    passing = [a for a in arms[1:] if verdict[a]["P1"] and verdict[a]["P2"]]
    print("\n=== VERDICT ===")
    if passing:
        print(f"ADOPT N_RESTARTS = {min(passing)} "
              f"(lowest value passing both criteria)")
    else:
        print("KEEP N_RESTARTS = 12 - no candidate passed both criteria.")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"n": args.n, "seed": args.seed, "arms": arms,
                   "timing_s": timing, "real": real,
                   "verdict": {str(k): {kk: vv for kk, vv in v.items()
                                        if kk != "flips"}
                               for k, v in verdict.items()},
                   "flips": {str(k): v["flips"] for k, v in verdict.items()},
                   "preds": {str(k): v for k, v in preds.items()}},
                  fh, indent=2)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
