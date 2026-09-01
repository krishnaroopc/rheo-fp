"""Generate a synthetic SAOS training set and write it to .npz.

Draws labelled stacks from every validated forward model (see
rheofp/data/synth.py for the sampling design), writes the canonical npz
layout, and prints a class balance plus an identifier round-trip check on a
subsample - a cheap smoke test that the generated population is actually
separable by the physics we already trust.

  python scripts/generate_dataset.py                       # 2000 examples
  python scripts/generate_dataset.py -n 20000 -o data/train.npz
  python scripts/generate_dataset.py -n 500 --xlsx out.xlsx   # human backdoor

xlsx export is a human sanity-check backdoor only (CLAUDE.md): it is capped,
never part of an automated path, and should not be committed.
"""
import argparse

import numpy as np

from rheofp.data.synth import (
    generate, to_npz_dataset, class_counts, ALL_CLASSES, FINE_CLASSES,
)
from rheofp.io.data import save_npz

DEFAULT_N = 2000
DEFAULT_OUT = "data/synthetic_train.npz"
ROUNDTRIP_SAMPLE = 40      # examples checked against identify()
XLSX_MAX_SAMPLES = 200     # the backdoor is for eyeballing, not for bulk export


def roundtrip_check(examples, n=ROUNDTRIP_SAMPLE, seed=0):
    """Fraction of single-curve fine-class examples the identifier recovers."""
    from rheofp.fitting.identify import identify

    rng = np.random.default_rng(seed)
    pool = [e for e in examples if e["label"] in FINE_CLASSES]
    if not pool:
        return None, 0
    picks = rng.choice(len(pool), size=min(n, len(pool)), replace=False)
    hits = 0
    for i in picks:
        ex = pool[int(i)]
        w, Gp, Gpp, _ = ex["curves"][0]
        if identify(w, Gp, Gpp, n_restarts=6)["best"] == ex["label"]:
            hits += 1
    return hits / len(picks), len(picks)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", "--n-examples", type=int, default=DEFAULT_N)
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--classes", nargs="*", default=list(ALL_CLASSES))
    ap.add_argument("--xlsx", metavar="PATH",
                    help="also write an xlsx for human inspection (capped, "
                         "not for bulk export)")
    ap.add_argument("--no-check", action="store_true",
                    help="skip the identifier round-trip check")
    args = ap.parse_args()

    examples = generate(args.n_examples, classes=args.classes, seed=args.seed)

    n_curves = sum(len(e["curves"]) for e in examples)
    stacks = sum(1 for e in examples if len(e["curves"]) > 1)
    print(f"\n{len(examples)} examples, {n_curves} curves "
          f"({stacks} are temperature stacks)")
    print("class balance:")
    for k, v in class_counts(examples).items():
        print(f"  {k:<20s} {v:5d}")

    dataset = to_npz_dataset(examples)
    save_npz(args.out, dataset)
    print(f"\nwrote {args.out}  ({len(dataset)} samples)")

    if args.xlsx:
        from rheofp.io.export_xlsx import export_npz_to_xlsx
        capped = dict(list(dataset.items())[:XLSX_MAX_SAMPLES])
        if len(capped) < len(dataset):
            tmp = args.out.replace(".npz", "_xlsxsubset.npz")
            save_npz(tmp, capped)
            export_npz_to_xlsx(tmp, args.xlsx)
            print(f"wrote {args.xlsx} (first {XLSX_MAX_SAMPLES} samples only)")
        else:
            export_npz_to_xlsx(args.out, args.xlsx)
            print(f"wrote {args.xlsx}")

    if not args.no_check:
        frac, n = roundtrip_check(examples, seed=args.seed)
        if frac is not None:
            print(f"\nidentifier round-trip: {frac:.0%} of {n} single curves "
                  f"recovered their planted class")
            print("  (confusions are expected - Zimm/Rouse differ only in "
                  "exponent, and gel/elastomer are nested models)")


if __name__ == "__main__":
    main()
