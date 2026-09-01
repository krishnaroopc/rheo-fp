"""Train the two-head SAOS classifier and report against the physics baseline.

    python scripts/train_classifier.py                    # 8000 examples, 40 epochs
    python scripts/train_classifier.py -n 40000 --epochs 80
    python scripts/train_classifier.py --data data/train.npz
    python scripts/train_classifier.py --no-baseline      # skip the AICc comparison

The AICc identifier baseline is the point of comparison that matters: the
neural model has to beat the validated physics it was built alongside, or it
is not earning its place in the pipeline.
"""
import argparse

import numpy as np
import torch

from rheofp.data.synth import generate
from rheofp.ml.dataset import examples_to_records, npz_to_records, split_records
from rheofp.ml.train import train, make_loaders, device_auto
from rheofp.ml.evaluate import (
    summarise, print_report, physics_baseline_accuracy,
)

DEFAULT_N = 8000
DEFAULT_CKPT = "checkpoints/rheonet.pt"
BASELINE_SAMPLE = 150


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", "--n-examples", type=int, default=DEFAULT_N)
    ap.add_argument("--data", help="load a saved .npz instead of generating")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--checkpoint", default=DEFAULT_CKPT)
    ap.add_argument("--no-baseline", action="store_true")
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()

    if args.data:
        print(f"loading {args.data}")
        records = npz_to_records(args.data)
    else:
        print(f"generating {args.n_examples} examples")
        records = examples_to_records(
            generate(args.n_examples, seed=args.seed))
    print(f"{len(records)} stacks, "
          f"{sum(len(r['curves']) for r in records)} curves")

    device = torch.device("cpu") if args.cpu else device_auto()
    model, history, test, norm = train(
        records, epochs=args.epochs, lr=args.lr, batch_size=args.batch_size,
        seed=args.seed, device=device, checkpoint=args.checkpoint)

    # rebuild the same test split for the detailed report
    _, _, test_loader, _ = make_loaders(records, batch_size=args.batch_size,
                                        seed=args.seed)
    baseline = None
    if not args.no_baseline:
        _, _, test_rec = split_records(records, seed=args.seed)
        print(f"\nrunning AICc physics baseline on "
              f"{min(BASELINE_SAMPLE, len(test_rec))} test stacks...")
        baseline = physics_baseline_accuracy(test_rec, n_max=BASELINE_SAMPLE,
                                             seed=args.seed)

    report = summarise(model, test_loader, device, physics_baseline=baseline)
    print_report(report)

    if baseline:
        delta = report["accuracy"] - baseline["accuracy"]
        verdict = "beats" if delta > 0 else "does NOT beat"
        print(f"\nthe model {verdict} the physics baseline "
              f"({report['accuracy']:.3f} vs {baseline['accuracy']:.3f}, "
              f"{delta:+.3f})")
        print("note: the baseline sees ONE curve; the model sees the whole "
              "stack. That advantage is the architecture working as designed.")


if __name__ == "__main__":
    main()
