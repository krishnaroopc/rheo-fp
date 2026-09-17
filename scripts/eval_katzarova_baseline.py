"""BASELINE: what the CURRENT system says about real bidisperse blends.

Measured with NO `blend` class anywhere - which is the shipped state - so this
is the "before" against which any future blend model must be scored. It runs
BOTH brains: identify()'s 10-model AICc bank and the 10-class network.

There is no pre-registration to score against yet, and that is deliberate.
This script exists to answer one factual question before any model is
designed: what does the product do TODAY when handed a blend? Writing the
predictions after seeing this is legitimate; writing them after seeing a
`blend` model's own results would not be.

THE SIX CURVES ARE TWO DIFFERENT TESTS:

  PS392 / PS206 / PS105   monodisperse. IN the taxonomy - these are ordinary
                          entangled linear melts and `reptation` is the right
                          answer. If the current bank gets these WRONG, that
                          is a finding about the bank, not about blends, and
                          it would undermine using them as a control later.

  HM / HL / ML            50/50 blends. NOT in the taxonomy. No candidate can
                          be right, so the question is only which wrong answer
                          is given and how loudly.

The second group is the interesting one, and the measured expectation from
the comb precedent (CLAUDE.md) is a CONFIDENT wrong answer: on 9 real combs
the none-of-the-above floor caught 6/9 but 2/9 came back at good fit quality
with no warning at all. Watch `low_confidence` and `abstain_p`, not the winner.

Run: uv run python scripts/eval_katzarova_baseline.py [--restarts 12]
     (add --no-neural to skip the network if checkpoints/rheonet.pt is absent)
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter

from rheofp.fitting import identify as ident
from rheofp.io.data import load_npz

NPZ = "data/katzarova2018.npz"
OUT_JSON = "docs/katzarova_baseline_2026-09-16.json"

# name -> (role, what a CORRECT answer would be, or None if unrepresentable)
ROLE = {
    "PS392": ("monodisperse", "reptation"),
    "PS206": ("monodisperse", "reptation"),
    "PS105": ("monodisperse", "reptation"),
    "HM":    ("blend 50/50", None),
    "HL":    ("blend 50/50", None),
    "ML":    ("blend 50/50", None),
}
MONO = [k for k, v in ROLE.items() if v[1] is not None]
BLENDS = [k for k, v in ROLE.items() if v[1] is None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restarts", type=int, default=None)
    ap.add_argument("--no-neural", action="store_true")
    ap.add_argument("--checkpoint", default="checkpoints/rheonet.pt")
    args = ap.parse_args()
    kw = {} if args.restarts is None else dict(n_restarts=args.restarts)

    assert "blend" not in ident.ALL_MODELS, (
        "a `blend` candidate is wired into the bank - this script measures the "
        "BASELINE and must run with it absent")
    print(f"bank ({len(ident.ALL_MODELS)} models): "
          f"{', '.join(sorted(ident.ALL_MODELS))}")

    use_neural = not args.no_neural and os.path.exists(args.checkpoint)
    model = norm = classes = None
    if use_neural:
        from rheofp.neural_report import explain_with_neural, load_checkpoint
        model, norm, classes = load_checkpoint(args.checkpoint)
        print(f"checkpoint {args.checkpoint}: {len(classes)} classes")
        print("NOTE no `blend` class on either side - the three blends below "
              "are out-of-distribution for BOTH brains.")
    else:
        print("running PHYSICS ONLY (no checkpoint)")
    print()

    data = load_npz(NPZ)
    rows, winners, kinds = [], Counter(), Counter()
    for name, (role, truth) in ROLE.items():
        d = data[name]
        res = ident.identify(d["omega"], d["Gp"], d["Gpp"], **kw)
        rank = res["ranking"]
        runner = rank[1] if len(rank) > 1 else None

        row = dict(
            sample=name, role=role, correct_answer=truth,
            physics=res["best"], weight=float(res["best_weight"]),
            rms=float(res["best_rms_log"]),
            runner_up=None if runner is None else runner["name"],
            delta=None if runner is None else float(runner["delta"]),
            low_confidence=bool(res["low_confidence"]),
            abstain=bool(res["abstain"]),
            terminal_reached=bool(res["features"].get("terminal_reached", False)),
            n_allowed=len(res["allowed"]),
        )
        print(f"{name:6s} [{role:12s}] physics -> {res['best']:16s} "
              f"w={row['weight']:.3f} rms={row['rms']:.4f}")
        print(f"                    runner-up {str(row['runner_up']):16s} "
              f"dAICc={row['delta']:7.1f}  low_conf={row['low_confidence']}  "
              f"terminal={row['terminal_reached']}")

        if use_neural:
            curves = [dict(omega=d["omega"], Gp=d["Gp"], Gpp=d["Gpp"],
                           T_K=float(d["T_K"]))]
            rep = explain_with_neural(res, curves, model=model, norm=norm,
                                      classes=classes)
            neural, agree = rep["neural"], rep["agreement"]
            row.update(
                neural=neural["winner"], neural_p=float(neural["p"]),
                abstain_p=float(neural["abstain_p"]),
                agreement=agree["kind"],
            )
            kinds[agree["kind"]] += 1
            print(f"                    neural   -> {neural['winner']:16s} "
                  f"p={neural['p']:.3f} abstain_p={neural['abstain_p']:.3f}"
                  f"   [{agree['kind'].upper()}]")

        rows.append(row)
        winners[res["best"]] += 1

    print("\n=== the three MONODISPERSE controls (these SHOULD be right) ===")
    n_ok = 0
    for r in rows:
        if r["correct_answer"] is None:
            continue
        ok = r["physics"] == r["correct_answer"]
        n_ok += ok
        print(f"  {r['sample']:6s} -> {r['physics']:16s} "
              f"{'OK' if ok else 'WRONG (wanted ' + r['correct_answer'] + ')'}"
              f"   rms={r['rms']:.4f}")
    print(f"  physics correct on {n_ok}/{len(MONO)}")
    print("  These are the VETO set for any future blend class: a blend model "
          "that wins here is winning by flexibility.")

    print("\n=== the three BLENDS (nothing can be right) ===")
    for r in rows:
        if r["correct_answer"] is not None:
            continue
        flag = ("flagged by the floor" if r["low_confidence"]
                else ">>> CONFIDENT AND WRONG, no warning <<<")
        print(f"  {r['sample']:6s} -> {r['physics']:16s} w={r['weight']:.3f} "
              f"rms={r['rms']:.4f}   {flag}")

    n_quiet = sum(1 for r in rows
                  if r["correct_answer"] is None and not r["low_confidence"])
    print(f"\n  {n_quiet}/{len(BLENDS)} blends wrong with NO quality warning.")

    print("\n=== all winners ===")
    for k, v in winners.most_common():
        print(f"  {k:18s} {v}")
    if kinds:
        print("\n=== two-brain agreement ===")
        for k, v in kinds.most_common():
            print(f"  {k:18s} {v}")

    with open(OUT_JSON, "w") as fh:
        json.dump(dict(bank=sorted(ident.ALL_MODELS),
                       checkpoint=args.checkpoint if use_neural else None,
                       rows=rows), fh, indent=2)
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    main()
