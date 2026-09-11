"""The neural head as report.py's SECOND COLUMN, and the agreement between
the two brains as the confidence signal neither can provide alone.

Why this module exists, in one line from the design notes:

    the two brains are mathematically independent, so whether they AGREE is a
    better confidence signal than either one's own certainty.

Both available self-confidences are known to fail, and to fail in the same
direction - overconfidence on unfamiliar material:

  * The network's abstention head is trained ONLY against the network's own
    errors on the SYNTHETIC distribution. It has never seen a polymer blend, a
    block copolymer or a semicrystalline melt, so a low abstain_p on one of
    those is not evidence of anything. It is a within-distribution error
    predictor being read as an out-of-distribution detector.
  * AICc's Akaike weight reaches 1.000 even when the TRUE class is absent from
    the bank entirely. Measured: handed a wormlike micelle with no micelle
    candidate registered, the 8-model bank answered `branched` at weight 1.000
    with a 0.05-decade residual - far under FLOOR_CHI2, so the none-of-the-
    above floor could not catch it either. The most flexible candidate present
    simply absorbs the curve.

Agreement is not subject to either failure, because the two methods share no
machinery. The AICc side fits closed-form constitutive models by L-BFGS-B in
log space and ranks them by a parsimony-penalised likelihood; the network is a
conv encoder over a resampled log-omega grid with masked attention pooling,
trained by gradient descent. They share only the taxonomy and the training
distribution's physics. When they land on the same class from opposite
directions that is genuine corroboration; when they diverge, at least one is
wrong and the reader has been told so.

This attacks the dominant error mode directly. Most of this classifier's
errors are a GOOD fit of the WRONG class (a Zimm curve read as Rouse fits
beautifully - that is precisely why they are confusable), and no confidence
score flags them. A disagreement does.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not combine the two into a single verdict, and it does not let the
network overrule identify(). Two independent readings shown side by side are
worth more than an averaged one, because the disagreement is the information.
Nor does it change identify(): report.py's contract with identify() is
untouched here, and this module imports from report.py rather than the other
way round, so `import rheofp.report` still costs no torch.

The asymmetry worth remembering when reading a divergence: the network is
more accurate on the synthetic test split (0.923 against the AICc bank's
0.907 on the SAME split), but the two are not strictly comparable - the
baseline sees ONE curve where the network sees the whole stack - and that
margin is inside the baseline's own ~+-0.027 sampling error at n=150. Neither
side is the referee. Where they differ, the honest report is "these two
disagree", not "the better one says X".
"""
from __future__ import annotations

import numpy as np

from rheofp.report import DEGENERATE_PAIRS, _wrap

DEFAULT_CHECKPOINT = "checkpoints/rheonet.pt"

# How much of the network's probability mass has to sit on its top class
# before its own ranking is called decisive. Not calibrated against anything
# external - it exists so the text can say "the network is unsure" rather than
# printing a bare 0.31, and it is deliberately loose.
NEURAL_CONFIDENT_P = 0.60
NEURAL_UNSURE_P = 0.40

# Above this the abstention head is asking to be listened to. The trained
# checkpoint's mean abstain_p on its own test split is 0.068, and dropping the
# least-confident 10% of predictions lifts accuracy 0.923 -> 0.957, so the
# head does carry real signal - WITHIN the synthetic distribution. See the
# module docstring for why that is not a general reliability statement.
ABSTAIN_HIGH = 0.30

# --- what the agreement flag is actually worth, measured -------------------
# scripts/measure_agreement.py, THREE independent seeds, all committed:
#   seed 7  n=200  docs/agreement_measurement_2026-09-09.txt
#   seed 11 n=600  docs/agreement_measurement_n600_2026-09-10.txt
#   seed 23 n=600  docs/agreement_measurement_seed23_2026-09-10.txt
# The constants below are POOLED over all three (1400 curves; 1231 in the
# agree arm, 169 in the disagree arm), which is better grounded than any
# single run and is what the user-facing text quotes. A test pins them.
#
# THE GATE QUESTION IS SETTLED AS "SMALL BUT REAL", and it took three runs to
# say that honestly. The margin - agreement-gated accuracy minus the accuracy
# of simply keeping the top-N% by the network's own probability, at matched
# coverage - came out:
#
#     seed 7   +0.006  (0.3 SE)   read at the time as "refuted"
#     seed 11  +0.019  (1.8 SE)   read at the time as "suggestive"
#     seed 23  +0.012  (1.1 SE)   pre-registered rule: AMBIGUOUS
#     POOLED   +0.014  (2.0 SE)
#
# Every individual run was ambiguous; only pooling reaches 2 SE. But the sign
# never flipped - three for three positive - so the effect is consistent and
# small rather than absent. The defensible wording is "comparable, possibly a
# little better", and NOT more than that: a 1.4-point gain on one gate is not
# a reason to trust agreement over the network's own confidence.
#
# Three things that were WRONG in earlier readings and are fixed here:
#  * "More than halves the fitting side" was an artefact of seed 7's 18-curve
#    disagree arm. Pooled over 169 curves it is 0.945 +- 0.007 (agree) against
#    0.438 +- 0.038 (disagree), a ratio of 0.46. "Roughly halves" is right.
#  * WHICH brain degrades more on a disagreement is NOT stable: the network
#    fell further at seed 11 (0.413 vs 0.493), the fitter at seed 23 (0.395 vs
#    0.421). So neither side is reliably the one to trust when they split -
#    the argument for the shortlist rather than picking a winner.
#  * `agree_degenerate` swings between runs (physics 0.364 / 0.576 / 0.575)
#    on ~5-7% of curves. Only its `either right` figure (0.970-1.000) is
#    quotable.
AGREE_N = 1400                   # total curves across the three runs
AGREE_ARM_N = 1231               # of those, where the two brains agreed
DISAGREE_ARM_N = 169
AGREE_ACC_PHYS = 0.945          # physics side, where the two agree
AGREE_ACC_NEURAL = 0.937        # network, where the two agree
AGREE_ACC_GATE_BASELINE = 0.923  # network's own p as a gate, matched coverage
GATE_MARGIN_SE = 2.0             # pooled, in standard errors
DISAGREE_ACC_PHYS = 0.438       # physics side, where they disagree
DISAGREE_ACC_NEURAL = 0.426     # network, where they disagree
EITHER_RIGHT_DISAGREE = 0.864   # one of the two labels is correct
EITHER_RIGHT_AGREE = 0.975


def load_checkpoint(path=DEFAULT_CHECKPOINT, device="cpu"):
    """Load the trained RheoNet checkpoint.

    Imports torch lazily so that `import rheofp.report` and the whole AICc
    pipeline stay usable on a machine with no torch and no checkpoint -
    checkpoints/ is gitignored and does NOT travel between PCs.
    """
    import torch

    from rheofp.ml.model import RheoNet

    ckpt = torch.load(path, map_location=device, weights_only=False)
    model = RheoNet()
    model.load_state_dict(ckpt["state_dict"])
    model.eval()
    return model, ckpt["norm"], list(ckpt["classes"])


def predict(model, norm, classes, curves):
    """Run the network on a stack of curves.

    `curves` is a list of dicts with omega/Gp/Gpp and optionally T_K - the
    same shape identify_stack() takes. A single curve is the degenerate N=1
    case, which is what the masked attention pool was built for, so one curve
    and a temperature series go through the same path.

    Returns (probs over `classes`, abstain_p).
    """
    import torch

    from rheofp.ml.dataset import curve_tensor, _summary

    xs, ss = [], []
    for c in curves:
        w = np.asarray(c["omega"], float)
        gp = np.asarray(c["Gp"], float)
        gpp = np.asarray(c["Gpp"], float)
        T_K = float(c.get("T_K", float("nan")))
        xs.append((curve_tensor(w, gp, gpp) - norm["x_mean"]) / norm["x_std"])
        ss.append((_summary(w, gp, gpp, T_K) - norm["s_mean"]) / norm["s_std"])

    xt = torch.from_numpy(np.stack(xs).astype(np.float32))[None]   # (1,N,pts,C)
    st = torch.from_numpy(np.stack(ss).astype(np.float32))[None]   # (1,N,S)
    mask = torch.ones(1, len(curves), dtype=torch.bool)
    with torch.no_grad():
        out = model(xt, st, mask)
    probs = torch.softmax(out["class_logits"], dim=-1)[0].numpy()
    abstain_p = float(torch.sigmoid(out["abstain_logit"])[0].item())
    return probs, abstain_p


def _neural_confidence(p_top):
    if p_top >= NEURAL_CONFIDENT_P:
        return "confident"
    if p_top >= NEURAL_UNSURE_P:
        return "leaning"
    return "unsure"


def neural_column(probs, classes, abstain_p, n_curves=1, top=3):
    """The network's own reading, as a structured dict.

    Deliberately parallel in shape to what explain() reports for the AICc
    side, so the two can be printed as columns of one table.
    """
    order = np.argsort(probs)[::-1]
    ranked = [{"name": classes[i], "p": float(probs[i])} for i in order[:top]]
    p_top = float(probs[order[0]])
    return {
        "winner": classes[int(order[0])],
        "p": p_top,
        "confidence": _neural_confidence(p_top),
        "ranked": ranked,
        "abstain_p": abstain_p,
        "abstain_high": abstain_p >= ABSTAIN_HIGH,
        "n_curves": int(n_curves),
    }


def agreement(physics_winner, neural, physics_ranking=None):
    """Compare the two independent readings - the point of the whole module.

    Four outcomes, each with a different thing to tell the reader:

      agree            both landed on the same class from opposite directions.
                       The strongest corroboration available here, and it is
                       not the same statement as either one's own confidence.
      agree_degenerate they differ, but only across a pair known to be
                       physically inseparable from a SAOS spectrum (Zimm vs
                       Rouse, cured elastomer vs critical gel). This is not a
                       real disagreement about the material - it is the
                       taxonomy's own known blind spot, and it should not be
                       reported with the same alarm as a genuine split.
      disagree_ranked  they differ, but the network's class is a LIVE
                       alternative on the AICc side (delta < 10). The two
                       methods are looking at the same short list and
                       ordering it differently.
      disagree         they differ and the network's class is not even a live
                       alternative for AICc. At least one of them is wrong in
                       a way neither one's confidence score will show.
    """
    n_win = neural["winner"]
    if n_win == physics_winner:
        kind = "agree"
    elif frozenset({n_win, physics_winner}) in DEGENERATE_PAIRS:
        kind = "agree_degenerate"
    else:
        kind = "disagree"

    delta = None
    if physics_ranking is not None:
        for r in physics_ranking:
            if r["name"] == n_win:
                delta = float(r["delta"])
                break
        if kind == "disagree" and delta is not None and delta < 10:
            kind = "disagree_ranked"

    return {
        "kind": kind,
        "physics_winner": physics_winner,
        "neural_winner": n_win,
        "neural_delta_aicc": delta,
        "degeneracy_note": DEGENERATE_PAIRS.get(
            frozenset({n_win, physics_winner})),
        "text": _agreement_text(kind, physics_winner, neural, delta),
        # What the PAIR is worth, where there is a pair. See pair_note().
        "pair": sorted({physics_winner, n_win}) if n_win != physics_winner
                else None,
        "pair_note": pair_note(kind),
    }


def _agreement_text(kind, physics_winner, neural, delta):
    n_win = neural["winner"]
    p = neural["p"]
    independence = (
        "These two methods share no machinery - one fits constitutive models "
        "and ranks them by penalised likelihood, the other is a trained "
        "network reading the curve shape directly. ")

    if kind == "agree":
        return (
            f"BOTH methods independently say {physics_winner} "
            f"(the network puts {p:.0%} of its probability there). "
            + independence +
            "So this is corroboration from two directions rather than one "
            "method repeating itself, and it is INDEPENDENT of both "
            "confidence scores - which matters because both of those stay "
            f"high on material the bank does not contain. Across {AGREE_N} "
            "planted curves in three independent runs, agreement gated "
            f"accuracy to {AGREE_ACC_NEURAL:.2f} against "
            f"{AGREE_ACC_GATE_BASELINE:.2f} for simply trusting the network's "
            "own probability at the same coverage - a small edge that was "
            "positive in every run but only reaches significance when they "
            "are pooled. Comparable, then, and probably a shade better; not "
            "a reason to prefer it. And it is not proof at all: both were "
            "built against the same taxonomy and the same physics, so "
            "material outside that taxonomy can fool them both at once.")

    if kind == "agree_degenerate":
        return (
            f"The two methods split - fitting says {physics_winner}, the "
            f"network says {n_win} ({p:.0%}) - but ONLY across a pair that is "
            "known to be inseparable from a SAOS spectrum by construction. "
            "Treat the regime-level answer as corroborated and this "
            "particular split as unresolved by this measurement; the "
            "disagreement reflects the taxonomy's known blind spot, not a "
            "conflict about the material. Worth knowing where this lands in "
            "practice: on planted curves in exactly this situation, one of "
            "the two labels was the right one EVERY time, even though each "
            "method on its own was right well under half the time. The pair "
            "is trustworthy here; the choice between them is not.")

    if kind == "disagree_ranked":
        return (
            f"THE TWO METHODS DISAGREE. Fitting ranks {physics_winner} first; "
            f"the network says {n_win} ({p:.0%}), which is a LIVE alternative "
            f"on the fitting side too (delta AICc {delta:.1f}). So both "
            "methods are looking at the same short list and ordering it "
            "differently, which is the mildest form of disagreement - but it "
            "still means at least one of them is wrong, and neither one's own "
            "confidence score will show you which. If you have independent "
            f"reason to believe {n_win}, this measurement does not rule it "
            "out.")

    return (
        f"THE TWO METHODS DISAGREE, and sharply. Fitting ranks "
        f"{physics_winner} first, while the network says {n_win} ({p:.0%}) - "
        + (f"a class fitting places at delta AICc {delta:.1f}, i.e. not even "
           "a live alternative on that side. "
           if delta is not None else
           "a class fitting never even put on the ballot. ")
        + "Two independent methods reaching different classes is a signal "
        "neither self-confidence can produce, and it is the one case where "
        "you should not accept either label without checking the evidence "
        "below by eye. Measured on planted curves, a disagreement roughly "
        "HALVES both methods' accuracy - the fitting side falls from "
        f"{AGREE_ACC_PHYS:.2f} to {DISAGREE_ACC_PHYS:.2f} and the network "
        f"from {AGREE_ACC_NEURAL:.2f} to {DISAGREE_ACC_NEURAL:.2f} - and "
        "which of the two ends up being the right one changes from run to "
        "run, so neither label inherits the doubt of the other. This pattern "
        "is also what material from OUTSIDE the taxonomy tends to produce, "
        "since each method then falls back on whichever of its own classes "
        "is least bad, and they need not pick the same one.")


def pair_note(kind):
    """What the PAIR of labels is worth, as distinct from either label.

    The most robust thing the measurement produced, and it was not the thing
    being measured. Pooled over three independent seeds (1400 curves), one of
    the two labels is the correct one far more often than either method alone
    is right:

        where they agree            97.5%  (either brain right)
        where they disagree         86.4%  -- vs 43.8% / 42.6% individually
        across the degenerate pair  97-100%

    So even when the pair cannot be resolved, it is usually the right SHORTLIST
    - which is a genuinely useful thing to hand a rheologist who knows their
    own sample, and it is exactly what a single averaged verdict would destroy.
    That is the argument for printing both labels prominently on a
    disagreement rather than trying to pick a winner.

    This is the claim that has held up best across re-measurement: the gate
    comparison swung between "refuted" and "suggestive" over three runs, while
    the pair advantage stayed at roughly double either member's own accuracy
    every time (either-right 0.889 / 0.907 / 0.816 against 0.39-0.49 each).
    Note it does vary by ~9 points between seeds on the small disagree arm
    (18-76 curves), so quote it as "about 85-90%", not to the decimal.

    One sub-result that held in all three runs and is worth keeping: a SHARP
    disagreement (the network's class not even ranked by AICc) is the pair's
    BETTER case, not its worse one - pooled either-right 0.93 across 112
    curves, against 0.75 for the milder `disagree_ranked` kind on 51. That is
    the opposite of what the alarming wording around sharp splits suggests.
    When the two methods diverge completely they are usually diverging onto the
    right answer and a wrong one; when they merely reorder the same short list,
    they are more often both looking at the wrong part of it. Seed 23 did pull
    the sharp figure down (1.00 / 0.98 / 0.85), so the ordering is solid but
    the gap is not as wide as the first two runs implied.

    Returns None where the two agree on one class, since there is no pair.
    """
    if kind == "agree":
        return None
    if kind == "agree_degenerate":
        return (
            "TAKE THE TWO TOGETHER. On planted curves that split across this "
            "known-degenerate pair, one of the two labels was correct 97-100% "
            "of the time in every measurement run, while each method ALONE "
            "managed only 40-58% - and which of the two is the better bet is "
            "not even stable between runs. If you can tell these apart by any "
            "other means (solvent quality, whether the sample was "
            "crosslinked), that outside knowledge settles it, and the pair "
            "above is a reliable shortlist to apply it to.")
    return (
        "TAKE THE TWO TOGETHER. Measured on planted curves, one of the two "
        "labels offered here is the correct one about 85-90% of the time "
        f"(pooled {EITHER_RIGHT_DISAGREE:.0%} over three runs), even though "
        "on these disagreement cases each method ALONE is right only about "
        f"{DISAGREE_ACC_NEURAL:.0%} to {DISAGREE_ACC_PHYS:.0%} of the time. "
        "So the pair is much more trustworthy than the choice between them: "
        "treat this as a two-item shortlist to settle with what you already "
        "know about your sample, not as one answer with a dissent attached.")


def explain_with_neural(result, curves, model=None, norm=None, classes=None,
                        checkpoint=DEFAULT_CHECKPOINT, base=None):
    """explain()'s dict plus a `neural` column and an `agreement` verdict.

    `result` is identify()'s (or identify_stack()'s) output; `curves` is the
    stack it was given - a one-element list for a single spectrum. Pass a
    preloaded (model, norm, classes) to avoid re-reading the checkpoint in a
    loop.

    Returns the same dict explain() returns, with two keys added, so every
    existing consumer of that dict keeps working untouched.
    """
    from rheofp.report import explain

    if base is None:
        first = curves[0]
        base = explain(result, w=np.asarray(first["omega"], float),
                       Gp=np.asarray(first["Gp"], float),
                       Gpp=np.asarray(first["Gpp"], float))

    if model is None:
        model, norm, classes = load_checkpoint(checkpoint)

    probs, abstain_p = predict(model, norm, classes, curves)
    neural = neural_column(probs, classes, abstain_p, n_curves=len(curves))
    base["neural"] = neural
    base["agreement"] = agreement(base["winner"], neural,
                                  result.get("ranking"))
    return base


def format_neural(rep, width=76):
    """Render the neural column + agreement verdict as plain text.

    Printed after the AICc report, not merged into it - the two readings stay
    visibly separate because their divergence is the information.
    """
    neural = rep.get("neural")
    if neural is None:
        return ""
    agree = rep["agreement"]
    L = ["", "=" * width, "SECOND OPINION: THE NEURAL HEAD", "=" * width]

    stack_note = (f" (reading all {neural['n_curves']} curves as one stack)"
                  if neural["n_curves"] > 1 else "")
    L.append(f"  Network says : {neural['winner']} "
             f"at {neural['p']:.0%} probability ({neural['confidence']})"
             + stack_note)
    L.append(f"  Fitting says : {rep['winner']} "
             f"at {rep['winner_rms_log']:.4f} decades "
             f"({rep['winner_fit_verdict']})")
    L.append("")
    L.append(f"  {'network ranks':<24s}{'p':>8s}")
    for r in neural["ranked"]:
        L.append(f"    {r['name']:<22s}{r['p']:8.3f}")

    L.append("")
    L.append(f"  abstention head: {neural['abstain_p']:.2f}"
             + ("  -- HIGH: the network is flagging this as the kind of curve "
                "it gets wrong" if neural["abstain_high"] else ""))
    for chunk in _wrap(
            "Read that number narrowly. It is trained against the network's "
            "own errors on the SYNTHETIC distribution only, so it predicts "
            "in-distribution mistakes and says nothing about material the "
            "bank has never seen. A low value is not evidence the answer is "
            "right.", width - 4):
        L.append(f"    {chunk}")

    L.append("")
    L.append("DO THE TWO BRAINS AGREE?")
    L.append("-" * width)
    for i, chunk in enumerate(_wrap(agree["text"], width - 4)):
        L.append(("  - " if i == 0 else "    ") + chunk)
    if agree["degeneracy_note"]:
        L.append("")
        for chunk in _wrap(agree["degeneracy_note"], width - 4):
            L.append(f"    {chunk}")

    # The pair, printed as a shortlist. This is the most robust thing the
    # measurement produced: one of these two labels is usually right even
    # where neither method individually is, so the pair is worth more than
    # the argument about which of them wins.
    if agree["pair_note"]:
        L.append("")
        L.append(f"  YOUR SHORTLIST: {' or '.join(agree['pair'])}")
        for chunk in _wrap(agree["pair_note"], width - 4):
            L.append(f"    {chunk}")
    L.append("=" * width)
    return "\n".join(L)
