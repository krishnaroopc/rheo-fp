"""Human-readable explanation of an identify() result - the "why did you say
that?" layer.

The premise, from the user: it is acceptable for the classifier to be
confidently wrong PROVIDED the person holding the sample can see the reasoning
and argue with it. Under the molecular scope (CLAUDE.md "SCOPE") that is not a
nicety. A user can referee "is my sample a foam?" by looking at the jar; they
cannot referee "elastomer or vitrimer?", so the reported evidence has to do
that job for them.

This module ADDS to identify(); it does not change it. identify() is called by
the tests, the validation scripts and the ML baseline, and its return contract
stays fixed. Everything below is derived from what identify() already returns
and currently throws away: `ranking`, `allowed`, `features`, `abstain`, and
`stack` from identify_stack().

Two reporting decisions worth keeping, both forced by measurement:

1. Rank by DELTA AICc, never by Akaike weight. The weights collapse to
   1.000/0.000 almost always and hide live alternatives. The Tixier critical
   gel is the standing example: `critical_gel` won at weight 1.000, but
   `cured_elastomer` sat at delta 2.4 - "substantial support" on the standard
   scale - and actually fitted MARGINALLY BETTER (0.0107 vs 0.0108 decades),
   losing only on parsimony. A user shown "1.000" would think the question
   settled. It is not.

2. Always print ABSOLUTE fit quality, for the winner and for every
   alternative. A weight of 1.000 says the winner beat the others; it does not
   say anything fitted well. On an out-of-scope curve the winner reached
   0.0819 decades while the rest of the field sat at 0.129-0.50 - i.e. nothing
   fitted, and the "winner" was merely least-bad. That is invisible behind the
   weight and obvious in the residuals.

Neither of those is a confidence score. This module deliberately does not
invent one: both available self-confidences are known to fail on unfamiliar
material (the network's abstention is trained only against its own errors on
the synthetic distribution; AICc's weight reaches 1.000 even when the true
class is absent from the bank entirely). It reports evidence and lets the
reader judge.
"""
from __future__ import annotations

import numpy as np

from rheofp.fitting.identify import (
    ALL_MODELS, NETWORK_CLASSES, FLOOR_CHI2, identify, signature_features,
    fit_model,
)

# Burnham & Anderson's conventional reading of delta AICc. These are rules of
# thumb for model selection, not probabilities - printed so the reader can
# apply their own judgement rather than trusting a single winner.
DELTA_BANDS = (
    (2.0, "substantial support - a live alternative"),
    (4.0, "somewhat less support"),
    (7.0, "considerably less support"),
    (10.0, "little support"),
)
DELTA_BEYOND = "essentially no support"

# Absolute fit quality bands, in decades of RMS log-residual. FLOOR_CHI2 (0.15)
# is where identify() already flags low confidence; the tighter bands are
# calibrated on what the real digitized data actually achieves (Darby/Tixier
# ~0.01, Pivokonsky ~0.06).
FIT_BANDS = (
    (0.02, "excellent"),
    (0.05, "good"),
    (0.10, "fair"),
    (FLOOR_CHI2, "poor"),
)
FIT_BEYOND = "does not fit"

# Pairs that are near-inseparable from a SAOS spectrum by construction rather
# than by any defect in the models. Mirrors AMBIGUOUS_PAIRS in ml/evaluate.py;
# duplicated rather than imported so this module does not depend on torch.
DEGENERATE_PAIRS = {
    frozenset({"zimm", "rouse_screened"}):
        "Zimm and Rouse differ only in the mode-spacing exponent (1.8 vs 2.0). "
        "Once a window is cropped and noisy their log-slope distributions "
        "overlap almost entirely, so this split may not be recoverable from "
        "SAOS at all. Distinguishing them is a solvent-quality question: Zimm "
        "means hydrodynamic interaction is unscreened (dilute, good solvent), "
        "Rouse means it is screened.",
    frozenset({"cured_elastomer", "critical_gel"}):
        "These two are NESTED: a critical gel is the limit of the cured "
        "elastomer model as the equilibrium modulus goes to zero. The gel wins "
        "when that extra parameter is not earning its place, so a small delta "
        "here reflects parsimony, not physical distance.",
}

# Physical wording for the pre-filter rules that survive in identify(). Each
# entry says what was OBSERVED (never what was merely absent - the
# has_shoulder rule that reasoned from missing evidence was removed
# 2026-09-07) and what measurement would put the candidate back on the ballot.
_DISCARD_RULES = {
    "terminal_reached": (
        NETWORK_CLASSES,
        "terminal flow is visible in your window (G' slope {slope_Gp_lo:.2f}, "
        "G\" slope {slope_Gpp_lo:.2f}, both approaching the terminal limits "
        "2 and 1)",
        "A permanently crosslinked network cannot flow at any temperature, so "
        "observing flow rules these out. This is a positive observation, not "
        "an absence - if you believe your sample is a permanent network, the "
        "flow you measured needs explaining first.",
    ),
    "has_plateau": (
        frozenset({"reptation"}),
        "no entanglement plateau at least a decade wide was found inside your "
        "window",
        "Reptation describes an ENTANGLED melt, whose defining signature is "
        "that plateau. Widen the window - lower frequency to reach the "
        "terminal end, higher to expose the plateau - if you believe this "
        "melt is entangled. Be aware this discard reasons from an ABSENCE, "
        "unlike the flow test above: a plateau can be missing because the "
        "melt is unentangled, or simply because it lies outside the "
        "frequencies you measured.",
    ),
}
# has_plateau fires the discard when FALSE, unlike terminal_reached which
# fires when TRUE. (The rule itself keys off plateau width alone, while the
# reported has_plateau feature also requires spectrum above the plateau, so
# treat this as the reported approximation of the rule - hence the hedged
# wording above rather than a claim about exactly which test tripped.)
_INVERTED_RULES = frozenset({"has_plateau"})


def _band(value, bands, beyond):
    for edge, label in bands:
        if value < edge:
            return label
    return beyond


def delta_verdict(delta):
    """Burnham & Anderson reading of one delta AICc."""
    return _band(delta, DELTA_BANDS, DELTA_BEYOND)


def fit_verdict(rms_log):
    """Absolute fit quality of one candidate, in words."""
    return _band(rms_log, FIT_BANDS, FIT_BEYOND)


def describe_features(feats):
    """Turn the measured signature features into physical statements.

    These are the observations the ranking rests on. A rheologist can check
    them against their own reading of the curve, which is the whole point -
    the reasoning has to be arguable.
    """
    lines = []
    lines.append(
        f"Low-frequency slopes: G' {feats['slope_Gp_lo']:.2f}, "
        f"G\" {feats['slope_Gpp_lo']:.2f} "
        f"(terminal flow would approach 2 and 1)")
    if feats["terminal_reached"]:
        lines.append("Terminal relaxation IS reached inside your window - the "
                     "sample flows.")
    else:
        lines.append("Terminal relaxation is NOT reached in your window - the "
                     "longest relaxation time is at or below your lowest "
                     "frequency.")
    if feats["has_plateau"]:
        lines.append("A modulus plateau is present, with spectrum above it "
                     "(entanglement or network-like).")
    if feats["has_shoulder"]:
        lines.append("A second G\" maximum is present - a sticker / "
                     "bond-exchange shoulder, characteristic of a reversibly "
                     "associating network.")
    lines.append(
        f"Loss tangent: median {feats['median_tan_delta']:.2f}, varying by "
        f"{feats['tan_delta_spread']:.3f} decades across the window"
        + (" - essentially frequency-INDEPENDENT, the Winter-Chambon "
           "signature of a critical gel" if feats["tan_delta_spread"] < 0.15
           else ""))
    if feats["flat_decades_lo"] > 0:
        lines.append(f"G' is flat over {feats['flat_decades_lo']:.2f} decades "
                     "at low frequency (solid-like).")
    return lines


def explain_discards(result):
    """Which candidates never reached the fitting stage, and how to lift that.

    Converts a silent deletion into an actionable instruction. Only rules that
    rest on a POSITIVE observation remain in identify(); the missing-evidence
    has_shoulder rule was removed 2026-09-07.
    """
    feats = result["features"]
    considered = set(result["allowed"])
    missing = set(ALL_MODELS) - considered
    if not missing:
        return []

    out = []
    claimed = set()
    for flag, (classes, observed, why) in _DISCARD_RULES.items():
        fired = (not feats.get(flag) if flag in _INVERTED_RULES
                 else bool(feats.get(flag)))
        hit = missing & set(classes)
        if fired and hit:
            out.append({
                "classes": sorted(hit),
                "because": observed.format(**feats),
                "reasoning": why,
            })
            claimed |= hit
    leftover = missing - claimed
    if leftover:
        out.append({
            "classes": sorted(leftover),
            "because": "a pre-filter rule excluded them",
            "reasoning": "See signature_features() for the rule that applied.",
        })
    return out


def contest(w, Gp, Gpp, candidate, result=None, **kw):
    """"Why not X?" - fit a class the user believes in and report the case.

    The strongest thing this module does. The user names the class they expect;
    it is fitted on the same data as the winner and the comparison is reported
    in full: its delta AICc, its ABSOLUTE fit quality, and whether anything
    measured actually contradicts it. A small delta with a comparable residual
    means the user's belief is live and the classifier simply preferred a
    simpler model - which is a very different message from "you are wrong".
    """
    if candidate not in ALL_MODELS:
        raise KeyError(f"unknown class {candidate!r}; "
                       f"known: {sorted(ALL_MODELS)}")
    if result is None:
        result = identify(w, Gp, Gpp, **kw)

    ranked = {r["name"]: r for r in result["ranking"]}
    if candidate in ranked:
        cand = ranked[candidate]
        was_fitted = True
    else:
        # Struck off by the pre-filter, so identify() never fitted it. Fit it
        # now on the same data - the user asked, and a discard is a claim that
        # deserves to be shown its own numbers.
        cand = fit_model(candidate, w, Gp, Gpp,
                         n_restarts=kw.get("n_restarts", 12))
        cand["delta"] = cand["aicc"] - result["ranking"][0]["aicc"]
        was_fitted = False

    winner = result["ranking"][0]
    contradicts = [d for d in explain_discards(result)
                   if candidate in d["classes"]]
    pair = DEGENERATE_PAIRS.get(frozenset({candidate, winner["name"]}))
    return {
        "candidate": candidate,
        "winner": winner["name"],
        "is_winner": candidate == winner["name"],
        "delta_aicc": float(cand["delta"]),
        "delta_verdict": delta_verdict(cand["delta"]),
        "rms_log": float(cand["rms_log"]),
        "fit_verdict": fit_verdict(cand["rms_log"]),
        "winner_rms_log": float(winner["rms_log"]),
        "fits_better_than_winner": cand["rms_log"] < winner["rms_log"],
        "was_on_ballot": was_fitted,
        "contradicted_by": contradicts,
        "degeneracy_note": pair,
    }


def explain(result, w=None, Gp=None, Gpp=None, max_alternatives=4):
    """Build the full structured explanation of an identify() result.

    Returns a dict; render it with format_report(). Kept structured so the
    same content can feed a UI, a notebook, or the text report.
    """
    ranking = result["ranking"]
    winner = ranking[0]
    alts = []
    for r in ranking[1:1 + max_alternatives]:
        alts.append({
            "name": r["name"],
            "delta_aicc": float(r["delta"]),
            "delta_verdict": delta_verdict(r["delta"]),
            "rms_log": float(r["rms_log"]),
            "fit_verdict": fit_verdict(r["rms_log"]),
            "k": r["k"],
            "fits_better": r["rms_log"] < winner["rms_log"],
            "degeneracy_note": DEGENERATE_PAIRS.get(
                frozenset({r["name"], winner["name"]})),
        })

    # "Nothing fitted well" - the least-bad-winner case, invisible behind a
    # weight of 1.000 and only visible in the absolute residuals.
    field_poor = all(r["rms_log"] > FLOOR_CHI2 for r in ranking)

    settle = []
    if result.get("abstain"):
        settle.append(
            "Measure a temperature stack (the same sample at 2+ temperatures, "
            "with T recorded). A melt's relaxation walks along the frequency "
            "axis as it is heated; a permanent network's plateau does not. "
            "Pass the curves to identify_stack(), which resolves exactly this.")
    if winner["name"] in NETWORK_CLASSES and not result["features"]["terminal_reached"]:
        settle.append(
            "Extend to lower frequency (or higher temperature) to see whether "
            "terminal flow ever appears. If it does, this is not a permanent "
            "network.")
    if not result["features"]["has_shoulder"]:
        settle.append(
            "If you suspect exchangeable bonds (a vitrimer), widen the window "
            "or raise the temperature to bring the bond-exchange time into "
            "view - its signature is a second G\" maximum. Note the sticker "
            "classes WERE fitted and ranked here regardless; their absence "
            "from the top is a fitted result, not a pre-filter deletion.")

    return {
        "winner": winner["name"],
        "winner_rms_log": float(winner["rms_log"]),
        "winner_fit_verdict": fit_verdict(winner["rms_log"]),
        "winner_k": winner["k"],
        "weight": float(result["best_weight"]),
        "alternatives": alts,
        "evidence": describe_features(result["features"]),
        "discards": explain_discards(result),
        "n_considered": len(ranking),
        "n_total": len(ALL_MODELS),
        "field_all_poor": field_poor,
        "low_confidence": bool(result["low_confidence"]),
        "abstain": bool(result.get("abstain")),
        "abstain_reason": result.get("abstain_reason"),
        "stack": result.get("stack"),
        "what_would_settle_it": settle,
    }


def format_report(rep, width=76):
    """Render explain()'s dict as plain text."""
    L = []
    rule = "=" * width
    L.append(rule)
    L.append(f"IDENTIFIED: {rep['winner']}")
    L.append(rule)
    L.append(f"  Fit quality : {rep['winner_rms_log']:.4f} decades RMS "
             f"({rep['winner_fit_verdict']})")
    L.append(f"  Parameters  : {rep['winner_k']}")
    L.append(f"  Considered  : {rep['n_considered']} of {rep['n_total']} "
             "candidate models")

    if rep["abstain"]:
        L.append("")
        L.append("  !! ABSTAINING on the material-type call:")
        L.append(f"     {rep['abstain_reason']}")
    if rep["field_all_poor"]:
        L.append("")
        L.append("  !! NOTHING IN THE BANK FITS THIS DATA WELL. The winner is "
                 "the least-bad")
        L.append("     of a poor field, which a high Akaike weight would hide. "
                 "Treat the")
        L.append("     answer as unreliable - your material may be outside "
                 "the taxonomy.")
    elif rep["low_confidence"]:
        L.append("")
        L.append("  !! Low confidence: the best fit is still poor in absolute "
                 "terms.")

    L.append("")
    L.append("ALTERNATIVES  (ranked by delta AICc - see note below)")
    L.append("-" * width)
    L.append(f"  {'model':<20s} {'dAICc':>8s} {'fit(dec)':>9s}  interpretation")
    for a in rep["alternatives"]:
        flag = " *fits better*" if a["fits_better"] else ""
        L.append(f"  {a['name']:<20s} {a['delta_aicc']:8.1f} "
                 f"{a['rms_log']:9.4f}  {a['delta_verdict']}{flag}")
    L.append("")
    L.append("  delta AICc is the honest ranking here; Akaike weights collapse")
    L.append("  to 1.000/0.000 and hide live alternatives. Below ~2 the "
             "alternative")
    L.append("  has substantial support and should NOT be considered ruled out.")
    for a in rep["alternatives"]:
        if a["degeneracy_note"] and a["delta_aicc"] < 10:
            L.append("")
            L.append(f"  NOTE on {rep['winner']} vs {a['name']}:")
            for chunk in _wrap(a["degeneracy_note"], width - 4):
                L.append(f"    {chunk}")

    L.append("")
    L.append("WHAT WAS MEASURED")
    L.append("-" * width)
    for e in rep["evidence"]:
        for i, chunk in enumerate(_wrap(e, width - 4)):
            L.append(("  - " if i == 0 else "    ") + chunk)

    if rep["discards"]:
        L.append("")
        L.append("NOT CONSIDERED")
        L.append("-" * width)
        for d in rep["discards"]:
            L.append(f"  {', '.join(d['classes'])}")
            for chunk in _wrap("because " + d["because"], width - 6):
                L.append(f"    {chunk}")
            for chunk in _wrap(d["reasoning"], width - 6):
                L.append(f"    {chunk}")

    if rep["stack"]:
        L.append("")
        L.append("TEMPERATURE STACK")
        L.append("-" * width)
        L.append(f"  verdict: {rep['stack'].get('verdict')}")
        if rep["stack"].get("reason"):
            for chunk in _wrap(rep["stack"]["reason"], width - 4):
                L.append(f"  {chunk}")

    if rep["what_would_settle_it"]:
        L.append("")
        L.append("WHAT WOULD SETTLE IT")
        L.append("-" * width)
        for s in rep["what_would_settle_it"]:
            for i, chunk in enumerate(_wrap(s, width - 4)):
                L.append(("  - " if i == 0 else "    ") + chunk)

    L.append("")
    L.append("Disagree? Ask 'why not X?' - contest(w, Gp, Gpp, 'X') fits your")
    L.append("candidate on this same data and reports its case in full.")
    L.append(rule)
    return "\n".join(L)


def format_contest(c, width=76):
    """Render contest()'s dict as plain text."""
    L = ["-" * width,
         f"WHY NOT {c['candidate']}?",
         "-" * width]
    if c["is_winner"]:
        L.append(f"  {c['candidate']} IS the identified class.")
        L.append("-" * width)
        return "\n".join(L)

    L.append(f"  Its fit      : {c['rms_log']:.4f} decades ({c['fit_verdict']})")
    L.append(f"  Winner's fit : {c['winner_rms_log']:.4f} decades "
             f"({c['winner']})")
    L.append(f"  delta AICc   : {c['delta_aicc']:.1f} - {c['delta_verdict']}")
    if not c["was_on_ballot"]:
        L.append("  (this class was struck off by the pre-filter; it has been "
                 "fitted here on request)")
    L.append("")
    if c["fits_better_than_winner"]:
        for chunk in _wrap(
                f"NOTE: {c['candidate']} actually fits your data BETTER than "
                f"{c['winner']} in absolute terms. It ranks lower only on "
                "parsimony - AICc penalises its extra parameters. If you have "
                "independent reason to believe this material is "
                f"{c['candidate']}, nothing in your measurement contradicts "
                "that.", width - 2):
            L.append(f"  {chunk}")
    elif c["delta_aicc"] < 2:
        for chunk in _wrap(
                f"{c['candidate']} has substantial support and is NOT ruled "
                "out. The data does not separate it from the winner.",
                width - 2):
            L.append(f"  {chunk}")
    elif c["contradicted_by"]:
        for d in c["contradicted_by"]:
            for chunk in _wrap("Contradicted: " + d["because"], width - 2):
                L.append(f"  {chunk}")
            for chunk in _wrap(d["reasoning"], width - 2):
                L.append(f"  {chunk}")
    else:
        for chunk in _wrap(
                f"The data prefers {c['winner']} by a wide margin. No single "
                f"measured feature rules {c['candidate']} out - it simply "
                "explains the whole curve less well.", width - 2):
            L.append(f"  {chunk}")
    if c["degeneracy_note"]:
        L.append("")
        for chunk in _wrap(c["degeneracy_note"], width - 2):
            L.append(f"  {chunk}")
    L.append("-" * width)
    return "\n".join(L)


def _wrap(text, width):
    words, line, out = text.split(), "", []
    for word in words:
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out or [""]
