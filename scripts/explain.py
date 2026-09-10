"""Explain an identify() result for one measured spectrum - the CLI wrapper.

    python scripts/explain.py data/tixier2004.npz
    python scripts/explain.py data/pivo2006.npz --sample E
    python scripts/explain.py data/tixier2004.npz --why-not cured_elastomer
    python scripts/explain.py data/darby2022.npz --stack     # all samples as a T stack
    python scripts/explain.py data/mm1998.npz --sample PI4_Ma95k --neural

--neural adds the trained network as a SECOND, independent opinion and reports
whether the two methods agree. That agreement is a better confidence signal
than either one's own certainty: the network's abstention is trained only
against its own errors on the synthetic distribution, and AICc's weight reaches
1.000 even when the true class is absent from the bank entirely, but the two
share no machinery, so a divergence is information neither can produce alone.

Reads .npz (rheofp.io.data convention) or .xlsx (column 0 = omega, paired
"<sample> G' (Pa)" / "<sample> G'' (Pa)" columns).
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

from rheofp.fitting.identify import identify, identify_stack, ALL_MODELS
from rheofp.io.data import load_npz, load_xlsx
from rheofp.report import (
    explain, format_report, contest, format_contest,
)


def load_any(path, omega_hz=False):
    if str(path).lower().endswith(".xlsx"):
        return load_xlsx(path, omega_hz=omega_hz)
    return load_npz(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="npz or xlsx file of SAOS data")
    ap.add_argument("--sample", default=None,
                    help="which sample in the file (default: the first)")
    ap.add_argument("--why-not", default=None, metavar="CLASS",
                    help="contest mode: make the case for this class instead")
    ap.add_argument("--stack", action="store_true",
                    help="treat every sample in the file as one temperature "
                         "stack of a single material")
    ap.add_argument("--omega-hz", action="store_true",
                    help="input frequency column is Hz, not rad/s")
    ap.add_argument("--restarts", type=int, default=12)
    ap.add_argument("--neural", action="store_true",
                    help="also run the trained network as a second, "
                         "independent opinion and report whether the two "
                         "methods AGREE - a better confidence signal than "
                         "either one's own certainty")
    ap.add_argument("--checkpoint", default=None,
                    help="path to the trained checkpoint (default: "
                         "checkpoints/rheonet.pt); implies --neural")
    args = ap.parse_args(argv)

    data = load_any(args.path, omega_hz=args.omega_hz)
    if not data:
        ap.error(f"no samples found in {args.path}")

    if args.why_not and args.why_not not in ALL_MODELS:
        ap.error(f"unknown class {args.why_not!r}; known: {sorted(ALL_MODELS)}")

    want_neural = args.neural or args.checkpoint is not None

    if args.stack:
        stack = [dict(omega=s["omega"], Gp=s["Gp"], Gpp=s["Gpp"],
                      T_K=float(s.get("T_K", np.nan))) for s in data.values()]
        if not any(np.isfinite(s["T_K"]) for s in stack):
            print("WARNING: no T_K on any sample - the stack resolver needs "
                  "temperatures to measure a shift, and will report that it "
                  "cannot.\n", file=sys.stderr)
        out = identify_stack(stack, n_restarts=args.restarts)
        w = stack[0]["omega"]; Gp = stack[0]["Gp"]; Gpp = stack[0]["Gpp"]
        curves = stack
        label = f"{args.path} ({len(stack)} curves as one T stack)"
    else:
        name = args.sample if args.sample is not None else next(iter(data))
        if name not in data:
            ap.error(f"sample {name!r} not in {args.path}; "
                     f"have: {sorted(data)}")
        s = data[name]
        w, Gp, Gpp = s["omega"], s["Gp"], s["Gpp"]
        out = identify(w, Gp, Gpp, n_restarts=args.restarts)
        curves = [dict(omega=w, Gp=Gp, Gpp=Gpp,
                       T_K=float(s.get("T_K", np.nan)))]
        label = f"{args.path} :: {name}"

    print(f"\n{label}   ({len(w)} points, "
          f"{np.log10(w.max() / w.min()):.1f} decades)\n")
    rep = explain(out, w=w, Gp=Gp, Gpp=Gpp)
    print(format_report(rep))

    if want_neural:
        # Imported here so the AICc path stays usable with no torch and no
        # checkpoint - checkpoints/ is gitignored and does not travel.
        from rheofp.neural_report import (
            DEFAULT_CHECKPOINT, explain_with_neural, format_neural,
        )
        ckpt = args.checkpoint or DEFAULT_CHECKPOINT
        try:
            rep = explain_with_neural(out, curves, checkpoint=ckpt, base=rep)
        except FileNotFoundError:
            print(f"\n(no checkpoint at {ckpt} - skipping the neural column. "
                  f"It is gitignored and reproducible:\n"
                  f"    uv run python scripts/train_classifier.py "
                  f"-n 16000 --epochs 55)", file=sys.stderr)
        else:
            print(format_neural(rep))

    if args.why_not:
        print()
        print(format_contest(contest(w, Gp, Gpp, args.why_not, result=out,
                                     n_restarts=args.restarts)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
