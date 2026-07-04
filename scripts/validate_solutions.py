"""Validation script for rheofp.models.solutions + rheofp.fitting.identify
(from solution_identifier.ipynb).

Run directly: python scripts/validate_solutions.py
"""
import numpy as np
import matplotlib.pyplot as plt

from rheofp.models.solutions import MODELS
from rheofp.fitting.identify import identify

TRUTH = {
    "zimm":             [2.0, 0.5, 30],
    "rouse_screened":   [2.5, 0.5, 40],
    "reptation":        [3.5, 2.0, 25],
    "sticky_rouse":     [3.0, 2.0, -1.0, 30],
    "sticky_reptation": [3.5, 4.0, 20, 1.5],
}


def run_verification():
    w = np.logspace(-3, 4, 60)
    print("VERIFICATION  (synthetic truth -> identifier output)\n" + "=" * 60)
    correct = 0
    results = {}
    for true_name, theta in TRUTH.items():
        Gp, Gpp = MODELS[true_name][0](w, np.array(theta, float))
        out = identify(w, Gp, Gpp)
        results[true_name] = (w, Gp, Gpp, out)
        hit = out["best"] == true_name
        correct += int(hit)
        print(f"[{'OK  ' if hit else 'MISS'}] truth={true_name:18s} -> best={out['best']:18s} "
              f"w={out['best_weight']:.2f} rms_log={out['best_rms_log']:.3f}")
        top3 = ", ".join(f"{r['name']}({r['weight']:.2f})" for r in out["ranking"][:3])
        print(f"        allowed={out['allowed']}")
        print(f"        top: {top3}\n")
    print(f"recovered {correct}/{len(TRUTH)} regimes")
    return results


def main():
    results = run_verification()

    fig, axes = plt.subplots(1, len(TRUTH), figsize=(4 * len(TRUTH), 3.6), sharey=False)
    for ax, (name, (w, Gp, Gpp, out)) in zip(axes, results.items()):
        ax.loglog(w, Gp, "o", ms=3, label="G'")
        ax.loglog(w, Gpp, "s", ms=3, mfc="none", label="G''")
        ax.set_title(f"{name}\nbest={out['best']}")
        ax.set_xlabel(r"$\omega$ [rad/s]")
        ax.legend(fontsize=7)
        ax.grid(True, which="both", alpha=.3)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
