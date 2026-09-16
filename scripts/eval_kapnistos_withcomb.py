"""The pre-registered decision measurement: wire `comb` in and count the cost.

Two halves, both required, neither meaningful alone:

  P1  do the real combs come back as `comb`? (docs/kapnistos2005_preregistration.md)
  P2  does the LINEAR CONTROL c6bb-PS stay non-comb? A veto on its own.
  P3  do MM1998's seven stars and Pryke's two SURVIVE? `star` must hold
      >= 5/7 on MM1998 AND keep its winning margins above dAICc 50.

P3 is the one that failed on 2026-09-14 (star 5/7 -> 4/7, margins 194-225 ->
7.6-27.4) and the reason the class is unwired. The baseline measured
2026-09-16 made the risk worse, not better: with `comb` ABSENT, `star` already
wins 6 of the 9 real combs at weight 1.000, so `comb` is not joining a ballot
where `star` is adjacent - it is joining one where `star` is the incumbent on
exactly these curves.

Nothing here mutates the shipped bank beyond this process; `comb` is patched
in and removed in a finally block.

Run: uv run python scripts/eval_kapnistos_withcomb.py [--restarts 12]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

import numpy as np

from rheofp.fitting import identify as ident
from rheofp.io.data import load_npz
from rheofp.models.comb import COMB_MODELS

KAPNISTOS = "data/kapnistos2005.npz"
OUT_JSON = "docs/kapnistos_withcomb_2026-09-16.json"
STAR_MARGIN_FLOOR = 50.0        # test_star.py's assertion; do NOT lower

ROLE = {
    "c6bb-PS": "LINEAR CONTROL", "c612-PS": "unentangled arms",
    "c622-PS": "unentangled arms", "c632-PS": "marginal",
    "c642-PS": "comb", "c652-PS": "comb",
    "lc3-PBd": "comb", "lc1-PBd": "comb", "lc2-PBd": "comb",
}
# P1 scores these six only; the two unentangled-arm samples are excluded by P5.
SCORED = ["c632-PS", "c642-PS", "c652-PS", "lc3-PBd", "lc1-PBd", "lc2-PBd"]

REAL_STARS = {
    "data/mm1998.npz": ["PI4_Ma11k", "PI4_Ma17k", "PI4_Ma36k", "PI4_Ma44k",
                        "PI4_Ma47k", "PI4_Ma95k", "PI4_Ma105k"],
    "data/pryke2002.npz": ["PBD3_Ma38k", "PBD3_Ma78k"],
}


def score(path, names, kw):
    """Winner + margin for each named curve in a dataset, current bank."""
    data = load_npz(path)
    out = {}
    for name in names:
        d = data[name]
        res = ident.identify(d["omega"], d["Gp"], d["Gpp"], **kw)
        rank = res["ranking"]
        runner = rank[1] if len(rank) > 1 else None
        out[name] = dict(
            best=res["best"], weight=float(res["best_weight"]),
            rms=float(res["best_rms_log"]),
            runner_up=None if runner is None else runner["name"],
            delta=None if runner is None else float(runner["delta"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--restarts", type=int, default=None)
    args = ap.parse_args()
    kw = {} if args.restarts is None else dict(n_restarts=args.restarts)

    assert "comb" not in ident.ALL_MODELS, "expected the shipped (unwired) bank"

    print("=== BEFORE: star curves on the shipped 10-model bank ===")
    before = {p: score(p, n, kw) for p, n in REAL_STARS.items()}
    for path, res in before.items():
        for nm, r in res.items():
            print(f"  {nm:12s} {r['best']:16s} dAICc={r['delta']:7.1f} "
                  f"over {r['runner_up']}")

    original = ident.ALL_MODELS
    try:
        ident.ALL_MODELS = {**original, **COMB_MODELS}
        print(f"\n>>> comb WIRED IN ({len(ident.ALL_MODELS)} candidates) <<<\n")

        print("=== P1/P2: the nine real Kapnistos combs ===")
        data = load_npz(KAPNISTOS)
        kap, winners = {}, Counter()
        for name, role in ROLE.items():
            d = data[name]
            res = ident.identify(d["omega"], d["Gp"], d["Gpp"], **kw)
            rank = res["ranking"]
            runner = rank[1] if len(rank) > 1 else None
            kap[name] = dict(
                role=role, best=res["best"], weight=float(res["best_weight"]),
                rms=float(res["best_rms_log"]),
                runner_up=None if runner is None else runner["name"],
                delta=None if runner is None else float(runner["delta"]),
                low_confidence=bool(res["low_confidence"]))
            winners[res["best"]] += 1
            print(f"  {name:9s} [{role:16s}] -> {res['best']:16s} "
                  f"w={kap[name]['weight']:.3f} rms={kap[name]['rms']:.4f} "
                  f"(2nd {str(kap[name]['runner_up']):14s} "
                  f"dAICc={kap[name]['delta']:.1f})")

        print("\n=== AFTER: the same star curves, comb on the ballot ===")
        after = {p: score(p, n, kw) for p, n in REAL_STARS.items()}
        for path, res in after.items():
            for nm, r in res.items():
                b = before[path][nm]
                flag = "" if r["best"] == b["best"] else "   <<< CHANGED"
                print(f"  {nm:12s} {b['best']:14s} -> {r['best']:14s} "
                      f"dAICc {b['delta']:7.1f} -> {r['delta']:7.1f}{flag}")

        # ---- verdicts ----
        n_comb = sum(1 for k in SCORED if kap[k]["best"] == "comb")
        p1 = n_comb >= 5
        ctrl = kap["c6bb-PS"]["best"]
        p2 = ctrl != "comb"

        mm = after["data/mm1998.npz"]
        star_hits = sum(1 for r in mm.values() if r["best"] == "star")
        star_margins = [r["delta"] for r in mm.values() if r["best"] == "star"]
        worst = min(star_margins) if star_margins else float("nan")
        p3 = star_hits >= 5 and worst > STAR_MARGIN_FLOOR

        print("\n" + "=" * 68)
        print(f"P1  combs -> `comb`      {n_comb}/6 of the scored samples"
              f"        {'PASS' if p1 else 'FAIL'}")
        print(f"P2  linear control       c6bb-PS -> {ctrl:16s}"
              f"   {'PASS' if p2 else 'FAIL (VETO)'}")
        print(f"P3  star survives        MM1998 {star_hits}/7, worst surviving "
              f"margin dAICc {worst:.1f}   {'PASS' if p3 else 'FAIL'}")
        print("=" * 68)
        print("  => " + ("SAFE to wire in." if (p1 and p2 and p3) else
                         "DO NOT WIRE IN. The pre-registration fixed this "
                         "in advance: if P1 passes and P3 fails, the answer "
                         "is not to wire it in anyway."))

        with open(OUT_JSON, "w") as fh:
            json.dump(dict(kapnistos=kap,
                           stars_before={p: r for p, r in before.items()},
                           stars_after={p: r for p, r in after.items()},
                           verdict=dict(P1=p1, P2=p2, P3=p3,
                                        n_comb=n_comb, control=ctrl,
                                        star_hits=star_hits, worst=worst)),
                      fh, indent=2)
        print(f"\nwrote {OUT_JSON}")
    finally:
        ident.ALL_MODELS = original
        assert "comb" not in ident.ALL_MODELS, "bank not restored!"
        print("bank restored (comb removed)")


if __name__ == "__main__":
    main()
