"""P7: what the NETWORK says about real combs, and whether the brains agree.

The network has never seen a comb. `synth.py` does not generate the class and
the shipped checkpoint is 10-class, so every one of these nine curves is
out-of-distribution for it. That is exactly the situation the project has
recorded as its blind spot: abstention is trained against the model's own
errors on the synthetic distribution, so a LOW abstain_p here is not evidence
of anything.

Pre-registration P7 (docs/kapnistos2005_preregistration.md, committed 058d4f7
before any fit): the two brains DISAGREE on a majority, >= 5/9. Agreement on a
confident wrong class would instead be the "good fit of the WRONG class" mode.

Requires checkpoints/rheonet.pt, which is per-machine and gitignored.

Run: uv run python scripts/eval_kapnistos_neural.py [--restarts 12]
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter

import numpy as np

from rheofp.fitting import identify as ident
from rheofp.io.data import load_npz
from rheofp.neural_report import (DEFAULT_CHECKPOINT, explain_with_neural,
                                  load_checkpoint)

NPZ = "data/kapnistos2005.npz"
OUT_JSON = "docs/kapnistos_neural_2026-09-16.json"

ROLE = {
    "c6bb-PS": "LINEAR CONTROL", "c612-PS": "unentangled arms",
    "c622-PS": "unentangled arms", "c632-PS": "marginal",
    "c642-PS": "comb", "c652-PS": "comb",
    "lc3-PBd": "comb", "lc1-PBd": "comb", "lc2-PBd": "comb",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restarts", type=int, default=None)
    ap.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT)
    args = ap.parse_args()
    kw = {} if args.restarts is None else dict(n_restarts=args.restarts)

    if not os.path.exists(args.checkpoint):
        raise SystemExit(f"{args.checkpoint} not found - per-machine, retrain "
                         f"or run this on a PC that has it.")
    assert "comb" not in ident.ALL_MODELS, "measure the baseline with comb absent"

    model, norm, classes = load_checkpoint(args.checkpoint)
    print(f"checkpoint {args.checkpoint}: {len(classes)} classes "
          f"({', '.join(classes)})")
    print("NOTE `comb` is not among them - every curve below is OOD for the "
          "network.\n")

    data = load_npz(NPZ)
    rows, kinds, n_probs = [], Counter(), Counter()
    for name, role in ROLE.items():
        d = data[name]
        curves = [dict(omega=d["omega"], Gp=d["Gp"], Gpp=d["Gpp"],
                       T_K=float(d["T_K"]))]
        res = ident.identify(d["omega"], d["Gp"], d["Gpp"], **kw)
        rep = explain_with_neural(res, curves, model=model, norm=norm,
                                  classes=classes)
        neural, agree = rep["neural"], rep["agreement"]

        row = dict(
            sample=name, role=role,
            physics=res["best"], physics_weight=float(res["best_weight"]),
            physics_rms=float(res["best_rms_log"]),
            neural=neural["winner"], neural_p=float(neural["p"]),
            neural_ranked=[(r["name"], float(r["p"])) for r in neural["ranked"]],
            abstain_p=float(neural["abstain_p"]),
            agreement=agree["kind"],
            delta=None if agree.get("delta") is None else float(agree["delta"]),
        )
        rows.append(row)
        kinds[agree["kind"]] += 1
        n_probs[neural["winner"]] += 1

        print(f"{name:9s} [{role:16s}]")
        print(f"     physics {row['physics']:16s} w={row['physics_weight']:.3f} "
              f"rms={row['physics_rms']:.4f}")
        print(f"     neural  {row['neural']:16s} p={row['neural_p']:.3f} "
              f"abstain_p={row['abstain_p']:.3f}   "
              + "  ".join(f"{n}:{p:.2f}" for n, p in row["neural_ranked"][1:]))
        print(f"     -> {agree['kind'].upper()}"
              + ("" if row["delta"] is None
                 else f" (network's class is dAICc {row['delta']:.1f} on the "
                      f"physics side)"))

    n_dis = sum(v for k, v in kinds.items() if k.startswith("disagree"))
    print(f"\n=== agreement over 9 ===")
    for k, v in kinds.most_common():
        print(f"  {k:18s} {v}")
    print(f"\nP7 predicted >= 5/9 disagreements; measured {n_dis}/9 -> "
          f"{'HELD' if n_dis >= 5 else 'FAILED'}")

    print("\n=== what the network reaches for, lacking `comb` ===")
    for k, v in n_probs.most_common():
        print(f"  {k:18s} {v}")

    agreed_conf = [r for r in rows
                   if r["agreement"] == "agree" and r["abstain_p"] < 0.1]
    if agreed_conf:
        print(f"\n>>> {len(agreed_conf)} curve(s) where both brains agree "
              f"CONFIDENTLY on a class that cannot be right (no comb in "
              f"either): the good-fit-of-the-WRONG-class mode, which no "
              f"confidence score flags.")
        for r in agreed_conf:
            print(f"      {r['sample']:9s} both say {r['physics']}")

    with open(OUT_JSON, "w") as fh:
        json.dump(dict(checkpoint=args.checkpoint, classes=list(classes),
                       rows=rows), fh, indent=2)
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    main()
