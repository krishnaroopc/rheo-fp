"""At how many restarts does EACH model's fit actually converge?

This is the measurement `scripts/check_restart_count.py` could not make. That
script asks whether the BANK-WIDE `N_RESTARTS = 12` can come down, which is one
global number necessarily set by the hardest search in the bank. This one
scores every model separately, so a per-model budget could be set on evidence.

>>> IT WAS RUN 2026-09-19 AND THE PER-MODEL BUDGET WAS VETOED. <<<
See `docs/per_model_restarts_preregistration.md` for the criteria (committed
before the numbers were read) and the outcome. The short version:

  - `reptation` needs 12 restarts on its own planted curves, and it is 96% of
    the cost (68.58 s of 71.42 s per call). So the one model that matters keeps
    its full budget and the formula saves 0.13 s of a 71 s call: 1.00x.
  - Even zeroing all nine other models entirely caps the saving at 1.04x.
  - The "cheap" k=3 models are NOT easy searches: `rouse_screened` needed all
    12 on one curve, `zimm` 8, `sticky_reptation` 12, `branched` 12. Cutting
    restarts bank-wide would have quietly damaged the two weakest classes in
    the bank. Do not do it on the intuition that k=3 is trivial.

The script is kept because it is the evidence for that verdict and because it
is the right instrument if the question is ever reopened (e.g. after the
forward model gets cheaper).

Run: uv run python scripts/measure_restart_convergence.py [--n 3] [--seed 17]
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np

from rheofp.data import synth
from rheofp.fitting import identify as ident

OUT_JSON = "docs/restart_convergence.json"

# rms must match the 12-restart answer this closely to count as converged.
RTOL = 1e-6
ARMS = [1, 2, 3, 4, 6, 8, 12]


def convergence_point(name, w, Gp, Gpp, arms=ARMS):
    """Smallest arm whose rms matches the max-arm rms. None if never."""
    ref = ident.fit_model(name, w, Gp, Gpp, n_restarts=max(arms))["rms_log"]
    row = {a: float(ident.fit_model(name, w, Gp, Gpp, n_restarts=a)["rms_log"])
           for a in arms}
    for a in arms:
        if abs(row[a] - ref) <= RTOL * max(ref, 1e-12):
            return a, row, float(ref)
    return None, row, float(ref)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3,
                    help="planted curves per class (default 3)")
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--out", default=OUT_JSON)
    args = ap.parse_args(argv)

    rng = np.random.default_rng(args.seed)
    results = {}

    print("=== convergence restart, per model, on its own planted curves ===")
    for cls in synth.ALL_CLASSES:
        convs, rows = [], []
        for _ in range(args.n):
            ex = synth.make_example(rng, cls, n_curves=1)
            w, Gp, Gpp, _ = ex["curves"][0]
            c, row, ref = convergence_point(cls, w, Gp, Gpp)
            convs.append(c)
            rows.append(row)
        results[cls] = {"conv": convs, "rms_by_arm": rows}
        print(f"  {cls:<18} converged at {convs}   "
              f"(None = never matched {max(ARMS)})", flush=True)

    print("\n=== cost of ONE fit at 12 restarts ===")
    ex = synth.make_example(np.random.default_rng(5), "branched", n_curves=1)
    w, Gp, Gpp, _ = ex["curves"][0]
    total = 0.0
    for name in ident.ALL_MODELS:
        t0 = time.time()
        ident.fit_model(name, w, Gp, Gpp, n_restarts=12)
        dt = time.time() - t0
        total += dt
        results.setdefault(name, {})["cost12_s"] = dt
        print(f"  {name:<18} {dt:8.2f} s", flush=True)
    print(f"  {'TOTAL':<18} {total:8.2f} s")

    # The pre-registered budget formula, applied for the record.
    print("\n=== pre-registered budget clip(2*worst_conv, 4, 12) ===")
    proj = 0.0
    for cls in synth.ALL_CLASSES:
        convs = [c for c in results[cls]["conv"] if c is not None]
        worst = max(convs) if len(convs) == len(results[cls]["conv"]) else 12
        budget = int(np.clip(2 * worst, 4, 12))
        cost = results.get(cls, {}).get("cost12_s", 0.0)
        proj += cost * budget / 12.0
        results[cls]["budget"] = budget
    print(f"  total at 12: {total:.2f} s   at budget: {proj:.2f} s   "
          f"speedup {total/proj if proj else float('nan'):.2f}x")
    print("  (veto threshold was 2x - see the pre-registration)")

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
