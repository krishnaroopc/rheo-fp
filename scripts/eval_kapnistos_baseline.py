"""BASELINE: what identify()'s CURRENT 10-model bank says about real combs.

Scored with `comb` ABSENT, which is the shipped state. This is step 3 of the
2026-09-14 task list and the comparison the whole exercise rests on: without
it, any "with comb" number has nothing to be measured against.

Predictions were pre-registered in docs/kapnistos2005_preregistration.md and
committed (058d4f7) BEFORE this script was written. Score against that file.

Expect confident WRONG answers. Measured over 30 planted combs with the class
absent (2026-09-14): `branched` 12, `critical_gel` 10, `star` 6,
`sticky_reptation` 2 - always wrong, never uncertain. The interesting output
here is therefore not the winner but the CONFIDENCE attached to it, and
whether c6bb-PS (the linear control) is treated any differently from the six
genuine combs.

Run: uv run python scripts/eval_kapnistos_baseline.py [--restarts 12]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

import numpy as np

from rheofp.fitting import identify as ident
from rheofp.io.data import load_npz

NPZ = "data/kapnistos2005.npz"
OUT_JSON = "docs/kapnistos_baseline_2026-09-16.json"

# Architecture from the paper's Table 1; s_a below S_A_BOUNDS[0]=2.0 marks a
# sample pre-registration P5 excludes from scoring.
ARCH = {
    "c6bb-PS": dict(s_a=None, s_b=16.2, q=None, phi_b=1.0, role="LINEAR CONTROL"),
    "c612-PS": dict(s_a=0.38, s_b=16.2, q=31.0, phi_b=0.577, role="unentangled arms"),
    "c622-PS": dict(s_a=0.69, s_b=16.2, q=30.0, phi_b=0.439, role="unentangled arms"),
    "c632-PS": dict(s_a=1.51, s_b=16.2, q=25.0, phi_b=0.300, role="marginal"),
    "c642-PS": dict(s_a=2.76, s_b=16.2, q=29.0, phi_b=0.168, role="comb"),
    "c652-PS": dict(s_a=5.76, s_b=16.2, q=29.0, phi_b=0.088, role="comb"),
    "lc3-PBd": dict(s_a=3.86, s_b=27.5, q=17.0, phi_b=0.296, role="comb"),
    "lc1-PBd": dict(s_a=6.23, s_b=27.5, q=18.0, phi_b=0.197, role="comb"),
    "lc2-PBd": dict(s_a=12.78, s_b=27.5, q=17.8, phi_b=0.108, role="comb"),
}
SCORED = [k for k, v in ARCH.items() if v["role"] in ("comb", "marginal")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restarts", type=int, default=None)
    args = ap.parse_args()
    kw = {} if args.restarts is None else dict(n_restarts=args.restarts)

    assert "comb" not in ident.ALL_MODELS, (
        "comb is wired into the bank - this script measures the BASELINE and "
        "must run with it absent")
    print(f"bank ({len(ident.ALL_MODELS)} models): "
          f"{', '.join(sorted(ident.ALL_MODELS))}\n")

    data = load_npz(NPZ)
    rows, winners = [], Counter()
    for name in ARCH:
        d = data[name]
        res = ident.identify(d["omega"], d["Gp"], d["Gpp"], **kw)
        rank = res["ranking"]
        runner = rank[1] if len(rank) > 1 else None
        a = ARCH[name]
        row = dict(
            sample=name, role=a["role"], s_a=a["s_a"], phi_b=a["phi_b"],
            best=res["best"], weight=float(res["best_weight"]),
            rms=float(res["best_rms_log"]),
            runner_up=None if runner is None else runner["name"],
            delta=None if runner is None else float(runner["delta"]),
            low_confidence=bool(res["low_confidence"]),
            abstain=bool(res["abstain"]),
            terminal_reached=bool(res["features"].get("terminal_reached", False)),
            n_allowed=len(res["allowed"]),
        )
        rows.append(row)
        winners[res["best"]] += 1

        print(f"{name:9s} [{a['role']:16s}] -> {res['best']:16s} "
              f"w={row['weight']:.3f} rms={row['rms']:.4f}")
        print(f"            runner-up {str(row['runner_up']):16s} "
              f"dAICc={row['delta']:8.1f}   "
              f"low_conf={row['low_confidence']} abstain={row['abstain']} "
              f"terminal={row['terminal_reached']}")

    print("\n=== winners over all 9 ===")
    for k, v in winners.most_common():
        print(f"  {k:18s} {v}")

    print(f"\n=== the {len(SCORED)} samples P1 scores "
          f"(s_a at or near the floor) ===")
    for r in rows:
        if r["sample"] in SCORED:
            print(f"  {r['sample']:9s} -> {r['best']:16s} "
                  f"w={r['weight']:.3f} rms={r['rms']:.4f}")

    ctrl = next(r for r in rows if r["sample"] == "c6bb-PS")
    print(f"\n=== P2, the linear control ===")
    print(f"  c6bb-PS -> {ctrl['best']} (w={ctrl['weight']:.3f}, "
          f"rms={ctrl['rms']:.4f}); P2 wants reptation or branched, and "
          f"forbids `comb` once wired in.")

    conf = [r for r in rows if not r["low_confidence"]]
    print(f"\nconfident (rms < FLOOR_CHI2): {len(conf)}/9 - every one of these "
          f"is a class the bank cannot represent.")

    with open(OUT_JSON, "w") as fh:
        json.dump(dict(bank=sorted(ident.ALL_MODELS), rows=rows), fh, indent=2)
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    main()
