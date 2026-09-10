"""Does the two brains AGREEING actually predict being right?

The real-data evidence for the agreement signal is n=7 (Milner-McLeish 1998's
star set, where agreement separates the AICc hits from the AICc misses
perfectly). That is a strong indication and much too small to rest a claim on.
This script puts a number on it against planted synthetic curves, where the
truth is known by construction.

The claim under test, pre-registered so the result cannot be read after the
fact as whatever it happens to be:

    P(correct | the two methods agree)  >>  P(correct | they disagree)

"correct" is scored for EACH brain separately against the planted label, and
the interesting quantity is how much the agreement flag moves each one. A
signal that only says "the network was right when the network was confident"
is worth nothing extra - the network's own probability already says that. The
point of agreement is that it is INDEPENDENT of either self-confidence, so the
comparison to beat is the network's own top-class probability as a gate.

    uv run python scripts/measure_agreement.py -n 20
    uv run python scripts/measure_agreement.py -n 60 --restarts 12

Note this measures the AICc side on ONE curve per example (identify() is a
single-curve method) while the network reads that same single curve, so both
brains see identical data here - which is the fair comparison for this
question, and is NOT how the headline 0.923-vs-0.907 numbers were produced.
"""
from __future__ import annotations

import argparse
import collections

import numpy as np

from rheofp.data.synth import FINE_CLASSES, make_example
from rheofp.fitting.identify import identify
from rheofp.neural_report import agreement, load_checkpoint, neural_column, predict


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", type=int, default=20,
                    help="planted curves per class (default 20)")
    ap.add_argument("--restarts", type=int, default=8)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--checkpoint", default=None)
    args = ap.parse_args(argv)

    model, norm, classes = load_checkpoint(
        args.checkpoint) if args.checkpoint else load_checkpoint()
    rng = np.random.default_rng(args.seed)

    rows = []
    for cls in FINE_CLASSES:
        for i in range(args.n):
            ex = make_example(rng, cls, n_curves=1)
            w, gp, gpp, _ = ex["curves"][0]
            out = identify(w, gp, gpp, n_restarts=args.restarts)
            probs, abstain_p = predict(model, norm, classes,
                                       [dict(omega=w, Gp=gp, Gpp=gpp)])
            neural = neural_column(probs, classes, abstain_p)
            agr = agreement(out["ranking"][0]["name"], neural, out["ranking"])
            rows.append({
                "true": cls,
                "phys": out["ranking"][0]["name"],
                "neur": neural["winner"],
                "p": neural["p"],
                "abstain": abstain_p,
                "kind": agr["kind"],
            })
        print(f"  {cls:18s} done ({args.n})", flush=True)

    n = len(rows)
    print(f"\n{n} planted curves, {args.n}/class, seed {args.seed}\n")

    # Headline: does the flag move accuracy, and by how much, for each brain.
    print(f"{'group':<22s}{'n':>6s}{'phys acc':>10s}{'neural acc':>12s}"
          f"{'either right':>14s}")
    print("-" * 64)
    groups = [("agree (any kind)", lambda r: r["kind"].startswith("agree")),
              ("  agree (exact)", lambda r: r["kind"] == "agree"),
              ("  agree_degenerate", lambda r: r["kind"] == "agree_degenerate"),
              ("disagree (any)", lambda r: r["kind"].startswith("disagree")),
              ("  disagree_ranked", lambda r: r["kind"] == "disagree_ranked"),
              ("  disagree (sharp)", lambda r: r["kind"] == "disagree"),
              ("ALL", lambda r: True)]
    for label, pred in groups:
        sub = [r for r in rows if pred(r)]
        if not sub:
            print(f"{label:<22s}{0:>6d}{'-':>10s}{'-':>12s}{'-':>14s}")
            continue
        pa = np.mean([r["phys"] == r["true"] for r in sub])
        na = np.mean([r["neur"] == r["true"] for r in sub])
        ea = np.mean([r["true"] in (r["phys"], r["neur"]) for r in sub])
        print(f"{label:<22s}{len(sub):>6d}{pa:>10.3f}{na:>12.3f}{ea:>14.3f}")

    # The comparison that decides whether agreement earns its place: is it
    # better than simply trusting the network's own confidence? Matched on
    # coverage - compare each gate at the fraction of curves it keeps.
    agree_mask = np.array([r["kind"].startswith("agree") for r in rows])
    neur_ok = np.array([r["neur"] == r["true"] for r in rows])
    p_top = np.array([r["p"] for r in rows])
    abst = np.array([r["abstain"] for r in rows])
    cov = agree_mask.mean()
    print(f"\nGATE COMPARISON at matched coverage ({cov:.1%} of curves kept)")
    print("-" * 64)
    print(f"  keep where the two AGREE      : "
          f"neural acc {neur_ok[agree_mask].mean():.3f}")
    if 0 < cov < 1:
        thr = np.quantile(p_top, 1 - cov)
        m = p_top >= thr
        print(f"  keep top {cov:.0%} by network p    : "
              f"neural acc {neur_ok[m].mean():.3f}   (p >= {thr:.3f})")
        thr_a = np.quantile(abst, cov)
        m_a = abst <= thr_a
        print(f"  keep top {cov:.0%} by abstention   : "
              f"neural acc {neur_ok[m_a].mean():.3f}   (abstain <= {thr_a:.3f})")
    print("\n  Agreement is only worth reporting if it competes with these -")
    print("  it is INDEPENDENT of both, which the others cannot claim.")

    # Where the disagreements are, so a per-class pattern is visible.
    dis = collections.Counter(
        (r["true"], r["phys"], r["neur"]) for r in rows
        if r["kind"].startswith("disagree"))
    if dis:
        print(f"\nMOST COMMON DISAGREEMENTS  (true -> phys / neural)")
        print("-" * 64)
        for (t, p, ne), c in dis.most_common(12):
            who = "neural" if ne == t else ("phys" if p == t else "NEITHER")
            print(f"  {c:3d}x  {t:<18s} {p:<18s} {ne:<18s}  right: {who}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
