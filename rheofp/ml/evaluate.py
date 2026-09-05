"""Evaluation for RheoNet: confusion, abstention curves, physics baseline.

Accuracy alone hides what matters here. A classifier that confuses Zimm with
Rouse (they differ only in a power-law exponent) is behaving reasonably; one
that confuses a critical gel with an entangled melt is not. So the confusion
matrix is reported in full, and the abstention head is judged on whether
declining to answer actually buys accuracy on what remains.
"""
from __future__ import annotations

import numpy as np
import torch

from rheofp.ml.dataset import CLASSES, REGIMES
from rheofp.data.synth import CLASS_REGIME


@torch.no_grad()
def predict(model, loader, device):
    """Run the model over a loader, returning raw arrays."""
    model.eval()
    logits, abstain, labels, regimes, n_curves = [], [], [], [], []
    for batch in loader:
        out = model(batch["x"].to(device), batch["summary"].to(device),
                    batch["mask"].to(device))
        logits.append(out["class_logits"].cpu().numpy())
        abstain.append(torch.sigmoid(out["abstain_logit"]).cpu().numpy())
        labels.append(batch["label"].numpy())
        regimes.append(batch["regime"].numpy())
        n_curves.append(batch["mask"].sum(dim=1).numpy())
    return {
        "logits": np.concatenate(logits),
        "abstain": np.concatenate(abstain),
        "label": np.concatenate(labels),
        "regime": np.concatenate(regimes),
        "n_curves": np.concatenate(n_curves),
    }


def confusion_matrix(pred, true, n=len(CLASSES)):
    m = np.zeros((n, n), dtype=int)
    for t, p in zip(true, pred):
        m[t, p] += 1
    return m


def per_class_accuracy(cm):
    support = cm.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        acc = np.where(support > 0, np.diag(cm) / np.maximum(support, 1), np.nan)
    return acc, support


def abstention_curve(pred, true, abstain_score, fractions=None):
    """Accuracy on the retained set as more of the least-confident is dropped.

    This is the only honest test of an abstention head: if declining to answer
    on the 20% it is least sure about does not raise accuracy on the rest, the
    score carries no information.
    """
    fractions = fractions if fractions is not None else np.linspace(0, 0.5, 11)
    order = np.argsort(abstain_score)          # most confident first
    rows = []
    for f in fractions:
        keep = order[:max(1, int(round((1 - f) * len(order))))]
        rows.append({"abstained": float(f),
                     "coverage": len(keep) / len(order),
                     "accuracy": float((pred[keep] == true[keep]).mean())})
    return rows


def accuracy_by_stack_size(pred, true, n_curves):
    """Does a temperature stack actually help? It should."""
    rows = []
    for n in sorted(set(int(v) for v in n_curves)):
        sel = n_curves == n
        rows.append({"n_curves": n, "n": int(sel.sum()),
                     "accuracy": float((pred[sel] == true[sel]).mean())})
    return rows


# Class pairs that are near-inseparable from a SAOS spectrum by construction,
# not by any defect in the model. Zimm and Rouse differ only in the bead-spring
# mode-spacing exponent (1.8 vs 2.0); once the window is cropped and noised
# their log-slope distributions overlap almost entirely (measured: 1.05 +/-
# 0.70 vs 1.08 +/- 0.69). The cured elastomer and critical gel are nested
# models. Collapsing each pair gives the accuracy a user actually experiences
# when the fine distinction is not physically recoverable.
AMBIGUOUS_PAIRS = (("zimm", "rouse_screened"),
                   ("cured_elastomer", "critical_gel"))


def merged_pair_accuracy(pred, true, pairs=AMBIGUOUS_PAIRS):
    """Accuracy when each physically-degenerate pair is treated as one class.

    Reported alongside the strict number so a collapse onto one member of a
    genuinely ambiguous pair is not mistaken for a broader failure.
    """
    group = {c: c for c in CLASSES}
    for a, b in pairs:
        group[b] = a
    gp = np.array([group[CLASSES[i]] for i in pred])
    gt = np.array([group[CLASSES[i]] for i in true])
    return float((gp == gt).mean())


def pair_confusions(cm, pairs=AMBIGUOUS_PAIRS):
    """How much of the error mass sits inside each known-degenerate pair."""
    idx = {c: i for i, c in enumerate(CLASSES)}
    total_err = cm.sum() - np.trace(cm)
    rows = []
    for a, b in pairs:
        ia, ib = idx[a], idx[b]
        within = int(cm[ia, ib] + cm[ib, ia])
        rows.append({"pair": f"{a} <-> {b}", "errors": within,
                     "share_of_all_errors": (within / total_err
                                             if total_err else 0.0)})
    return rows


def regime_accuracy_from_fine(pred, true):
    """Even a wrong fine class can land in the right regime - worth knowing,
    since the taxonomy reports regime-level labels for model-only classes."""
    r = {c: CLASS_REGIME[c] for c in CLASSES}
    pr = np.array([r[CLASSES[i]] for i in pred])
    tr = np.array([r[CLASSES[i]] for i in true])
    return float((pr == tr).mean())


def format_confusion(cm, classes=CLASSES, max_name=16):
    """Text confusion matrix, rows = truth."""
    head = " " * (max_name + 2) + " ".join(f"{c[:6]:>6s}" for c in classes)
    lines = [head]
    for i, c in enumerate(classes):
        row = " ".join(f"{v:6d}" for v in cm[i])
        lines.append(f"{c[:max_name]:<{max_name}s}  {row}")
    return "\n".join(lines)


def summarise(model, loader, device, physics_baseline=None):
    """Full evaluation report as a dict."""
    p = predict(model, loader, device)
    pred = p["logits"].argmax(axis=1)
    cm = confusion_matrix(pred, p["label"])
    acc, support = per_class_accuracy(cm)
    out = {
        "accuracy": float((pred == p["label"]).mean()),
        "merged_pair_accuracy": merged_pair_accuracy(pred, p["label"]),
        "pair_confusions": pair_confusions(cm),
        "regime_accuracy": regime_accuracy_from_fine(pred, p["label"]),
        "confusion": cm,
        "per_class": {CLASSES[i]: {"accuracy": float(acc[i]),
                                   "support": int(support[i])}
                      for i in range(len(CLASSES))},
        "abstention_curve": abstention_curve(pred, p["label"], p["abstain"]),
        "by_stack_size": accuracy_by_stack_size(pred, p["label"], p["n_curves"]),
        "n": int(len(pred)),
    }
    if physics_baseline is not None:
        out["physics_baseline"] = physics_baseline
    return out


def physics_baseline_accuracy(records, n_max=200, seed=0, n_restarts=6):
    """What the validated AICc identifier scores on the same data.

    The neural model has to beat this to justify existing at all - which only
    means anything if the comparison is on common ground. The pool is therefore
    filtered to classes the identifier's bank can actually emit, NOT to the
    neural head's class list: a class the bank has no candidate for is a
    guaranteed miss, and scoring it would depress the baseline by roughly its
    share of the data rather than by any failure of the method.

    This filter is a guard, not a no-op. It currently keeps everything, because
    the bank covers all nine generated classes - and it is what will keep the
    number honest if a tenth class is ever generated before it is registered.
    `skipped` reports how many records it had to drop, so a silent divergence
    between generator and bank shows up in the report instead of in the score.
    """
    from rheofp.fitting.identify import identify, ALL_MODELS

    answerable = set(ALL_MODELS)
    rng = np.random.default_rng(seed)
    pool = [r for r in records if r["label"] in answerable]
    picks = rng.choice(len(pool), size=min(n_max, len(pool)), replace=False)
    hits = 0
    for i in picks:
        rec = pool[int(i)]
        w, Gp, Gpp, _ = rec["curves"][0]
        try:
            best = identify(w, Gp, Gpp, n_restarts=n_restarts)["best"]
        except Exception:
            best = None
        hits += (best == rec["label"])
    return {"accuracy": hits / len(picks), "n": int(len(picks)),
            "skipped": int(len(records) - len(pool))}


def print_report(report):
    print(f"\naccuracy        {report['accuracy']:.3f}  (n={report['n']})")
    if "merged_pair_accuracy" in report:
        print(f"  degenerate pairs merged: {report['merged_pair_accuracy']:.3f}"
              "   <- accuracy where the fine split is physically recoverable")
    print(f"regime accuracy {report['regime_accuracy']:.3f}")
    if "physics_baseline" in report:
        b = report["physics_baseline"]
        print(f"physics baseline {b['accuracy']:.3f}  (AICc identifier, "
              f"n={b['n']}, single curve)")
        if b.get("skipped"):
            print(f"  WARNING: {b['skipped']} test records were dropped - their "
                  "class has no candidate in the identifier's bank, so the two "
                  "numbers above are NOT measured on the same classes")

    print("\nper class:")
    for name, d in report["per_class"].items():
        bar = "#" * int(round(d["accuracy"] * 30))
        print(f"  {name:<20s} {d['accuracy']:.3f}  n={d['support']:<5d} {bar}")

    print("\nconfusion (rows = truth):")
    print(format_confusion(report["confusion"]))

    if report.get("pair_confusions"):
        print("\nerror mass inside known-degenerate pairs:")
        for row in report["pair_confusions"]:
            print(f"  {row['pair']:<34s} {row['errors']:5d} errors "
                  f"({row['share_of_all_errors']:.0%} of all)")

    print("\naccuracy vs stack size:")
    for row in report["by_stack_size"]:
        print(f"  {row['n_curves']} curve(s): {row['accuracy']:.3f} "
              f"(n={row['n']})")

    print("\nabstention (drop least-confident first):")
    for row in report["abstention_curve"][::2]:
        print(f"  abstain {row['abstained']:.0%}  coverage {row['coverage']:.2f}"
              f"  accuracy {row['accuracy']:.3f}")
