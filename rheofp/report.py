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

# --- branched-vs-vitrimer-power-law-regime contradiction (2026-09-07) ------
# Investigated in scripts/diagnose_sticky_models.py, next-actions 2b: on two
# real dioxaborolane-vitrimer temperature stacks (Ricarte 2023), every curve
# was called `branched`, at GOOD absolute fit (0.047-0.084 dec), so no misfit
# flag fired. Root cause is a forward-model limit, decided by the user
# (2026-09-07) to leave as-is rather than replace: the sticky models are a
# few discrete Maxwell modes about one sticker time, so they produce a G''
# PEAK that must fall on both sides and cannot rise monotonically across a
# power-law regime, which is exactly the real vitrimer's shape (G'' RISES as
# omega falls; log-slope -0.70) with G' essentially flat (0.019 decades). BSW's
# two power-law wedges fit that shape well, so `branched` wins on genuine
# merit - not a ranking bug - and nothing else in the report catches it,
# because the fit really is good.
#
# This is therefore reported as a NAMED, ALWAYS-CHECKED contradiction on a
# `branched` winner specifically, following the melt-vs-rubber abstention
# precedent (report the ambiguity rather than resolve it silently either way).
# It is not a class-conditional feature and is not added to
# signature_features() / identify()'s pre-filter - identify()'s contract and
# accuracy are deliberately untouched; this is reporting only.
#
# Thresholds chosen from measurement, not asserted: checked against 31
# curves the classifier genuinely called `branched` from a mixed synthetic
# population (branched, reptation, zimm, rouse_screened) - ZERO false
# positives - and against both real Pivokonsky LDPE curves (also correctly
# unflagged, slopes +0.73/+0.81, G' span 3.3-3.4 decades). Real vitrimer data
# is the only case observed to trip both conditions at once.
VITRIMER_POWERLAW_SLOPE_MAX = 0.0   # G'' low-w log-slope must be negative
VITRIMER_POWERLAW_GP_SPAN_MAX = 0.3  # decades - real branched melts span 1-5


def _gpp_low_freq_slope(w, Gpp, frac=0.3):
    lw = np.log10(w)
    n = max(4, int(len(w) * frac))
    return float(np.polyfit(lw[:n], np.log10(Gpp[:n]), 1)[0])


def branched_vitrimer_contradiction(winner_name, w, Gp, Gpp):
    """Does a `branched` winner actually look like an unreachable vitrimer?

    Returns a dict if the contradiction fires, else None. Needs the raw curve
    (not just identify()'s features), so it is computed here rather than in
    signature_features.
    """
    if winner_name != "branched" or w is None:
        return None
    slope = _gpp_low_freq_slope(w, Gpp)
    gp_span = float(np.ptp(np.log10(np.clip(Gp, 1e-30, None))))
    if slope < VITRIMER_POWERLAW_SLOPE_MAX and gp_span < VITRIMER_POWERLAW_GP_SPAN_MAX:
        return {
            "slope": slope,
            "gp_span": gp_span,
            "text": (
                f"Your G\" RISES as frequency falls (low-frequency log-slope "
                f"{slope:.2f}) while G' stays essentially flat "
                f"({gp_span:.3f} decades of span). A genuine branched melt "
                "does the opposite - G\" turns over and G' spans several "
                "decades as the terminal zone is approached (measured on "
                "real LDPE: slopes +0.73/+0.81, G' span 3.3-3.4 decades). "
                "This shape is instead the signature of a POWER-LAW regime, "
                "the kind a vitrimer shows between its rubbery plateau and "
                "an exchange-controlled terminal relaxation that lies "
                "outside your measured window. rheofp's sticky_rouse and "
                "sticky_reptation models cannot currently reproduce this "
                "shape (they are built from a handful of Maxwell modes "
                "around one sticker time, which makes a G\" PEAK, not a "
                "rising power-law wing) - so `branched` wins here on "
                "genuine fit quality, not by ruling out a vitrimer. If you "
                "suspect exchangeable bonds, this measurement cannot settle "
                "it either way; reaching the sticker peak (a higher "
                "temperature or a wider window) is what would."),
        }
    return None


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
        # Deliberately NOT attributed to stickers. Measured 2026-09-09 on
        # planted curves, a second G" maximum appears in ~72% of `branched`,
        # ~75% of `reptation` and ~88% of `star` - none of which has any
        # exchangeable bonds - and in only ~62% of `sticky_rouse`, the class it
        # is meant to mark. So the feature points away from the sticker classes
        # at least as often as toward them, and the old wording
        # ("characteristic of a reversibly associating network") was a causal
        # claim the evidence does not support.
        #
        # The mechanism is NOISE, not spectrum shape: `has_shoulder` in
        # signature_features counts raw local maxima with no smoothing and no
        # prominence threshold, and 2% multiplicative scatter on 10-100 points
        # manufactures them. Broken down by Z, planted stars trip it at 84% for
        # Z 5-20 (a single clean loss peak) against 100% for Z 35-45 (a genuine
        # two-peak split) - nearly flat, i.e. the detector is not seeing the
        # physics. See next-actions; fixing the detector is a separate, gated
        # change because signature_features feeds the pre-filter.
        lines.append("A second G\" maximum is present. This can indicate a "
                     "bond-exchange (sticker) time inside your window, but it "
                     "also appears in broad-spectrum melts and in star "
                     "polymers, so on its own it does not identify an "
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


def challenge(result, max_named=3, w=None, Gp=None, Gpp=None):
    """"Don't think it's X? Here's why it might not be." Always produced.

    Deliberately unconditional - it is printed for a confident correct answer
    exactly as for a doubtful one. The reason is that the alternative, showing
    a caveat only when some internal test trips, teaches the reader that a
    QUIET report means a SURE answer. That inference is false here and known
    to be false: most of this classifier's errors are good fits of the wrong
    class (a Zimm curve read as Rouse fits beautifully - that is why they are
    confusable), and no available signal flags them. A caveat that is always
    present carries no such implication, and a reader who knows their own
    sample can act on the specific reasons named below.

    Returns a list of dicts: `text` plus `kind` for anything that wants to
    style them.
    """
    ranking = result["ranking"]
    winner = ranking[0]
    feats = result["features"]
    items = []

    # 1. Absolute fit of the winner - stated every time, in both directions.
    if all(r["rms_log"] > FLOOR_CHI2 for r in ranking):
        items.append({
            "kind": "nothing_fits",
            "text": (
                f"No model in the bank fits this data well - the best is "
                f"{winner['name']} at {winner['rms_log']:.3f} decades, which "
                f"is poor in absolute terms. A material outside the bank's "
                f"{len(ALL_MODELS)} classes looks exactly like this. Treat "
                f"the label as a guess."),
        })
    else:
        items.append({
            "kind": "fit",
            "text": (
                f"{winner['name']} reproduces your curve to "
                f"{winner['rms_log']:.4f} decades, which is a genuinely good "
                "fit - but a good fit only means this model CAN produce your "
                "data, never that no other explanation could."),
        })

    # 2. The live alternatives, named, with what separates them.
    for a in ranking[1:1 + max_named]:
        if a["delta"] > 10:
            break
        note = DEGENERATE_PAIRS.get(frozenset({a["name"], winner["name"]}))
        better = a["rms_log"] < winner["rms_log"]
        txt = (f"It could be {a['name']} instead (delta AICc "
               f"{a['delta']:.1f}, {delta_verdict(a['delta'])}; fits your data "
               f"to {a['rms_log']:.4f} decades")
        txt += (", which is actually BETTER than the winner - it lost only "
                "because it spends more parameters to get there)."
                if better else ").")
        if note:
            txt += " " + note
        items.append({"kind": "alternative", "name": a["name"], "text": txt})

    # 2b. A `branched` winner that actually looks like an unreachable
    # vitrimer power-law regime - see branched_vitrimer_contradiction().
    contradiction = branched_vitrimer_contradiction(winner["name"], w, Gp, Gpp)
    if contradiction:
        items.append({"kind": "vitrimer_powerlaw", "text": contradiction["text"]})

    # 3. Classes that were never fitted at all.
    for d in explain_discards(result):
        items.append({
            "kind": "discarded",
            "text": (f"{', '.join(d['classes'])} was never fitted, "
                     f"because {d['because']}. {d['reasoning']}"),
        })

    # 4. The standing limits of the method, which no single result can escape.
    items.append({
        "kind": "out_of_taxonomy",
        "text": (
            f"Only {len(ALL_MODELS)} classes exist in this bank. Polymer "
            f"blends, block copolymers, comb architectures, semicrystalline "
            f"and filled melts are NOT among them, and none of them are "
            f"visible by eye either. If your sample is one of those, the "
            f"classifier will still return one of its {len(ALL_MODELS)} - and "
            f"if the wrong class happens to fit well, nothing here will say "
            f"so."),
    })
    if not feats["terminal_reached"]:
        items.append({
            "kind": "window",
            "text": (
                "Your window does not reach terminal flow, so the longest "
                "relaxation in this material was never measured - it lies at "
                "or below your lowest frequency. Anything distinguished by "
                "that relaxation cannot be settled by this measurement."),
        })
        if winner["name"] == "star":
            items.append({
                "kind": "window",
                "text": (
                    f"That matters more than usual for a star melt. A star arm "
                    f"relaxes by retraction along its own tube, and because "
                    f"the retraction time grows exponentially with arm length "
                    f"the resulting spectrum is very broad and its "
                    f"characteristic shape sits in the TERMINAL zone. Your low-"
                    f"frequency slopes are G' {feats['slope_Gp_lo']:.2f} and "
                    f"G\" {feats['slope_Gpp_lo']:.2f}, short of the 2 and 1 of "
                    f"a melt in flow, so that zone is not in your data and the "
                    f"star spectrum has been matched on its high-frequency "
                    f"wing alone - where a broad linear or long-chain-branched "
                    f"melt looks much the same. On the literature star melts "
                    f"tested, this class was right on every curve that reached "
                    f"flow and unreliable on every curve that did not, "
                    f"including one linear melt that came back as a star. "
                    f"Before accepting this, push the terminal zone into your "
                    f"window: run the low-frequency end further down, or "
                    f"measure warmer and shift by time-temperature "
                    f"superposition. Reaching the G'/G\" crossover and the "
                    f"onset of the 2/1 slopes is what makes a star call "
                    f"trustworthy."),
            })
    if not feats["has_shoulder"]:
        items.append({
            "kind": "window",
            "text": (
                "No bond-exchange shoulder is visible. That does not rule out "
                "exchangeable bonds (a vitrimer) - the exchange time may "
                "simply sit outside your window. Both sticker classes were "
                "fitted and ranked here regardless."),
        })
    return items


def explain(result, w=None, Gp=None, Gpp=None, max_alternatives=4):
    """Build the full structured explanation of an identify() result.

    Returns a dict; render it with format_report(). Kept structured so the
    same content can feed a UI, a notebook, or the text report.

    Pass w, Gp, Gpp (the same curve given to identify()) to enable the
    branched-vs-vitrimer-power-law-regime check in challenge(), which needs
    the raw curve rather than identify()'s summary features. Omitting them
    only skips that one check; everything else is unaffected.
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
            "view - it would show as a second G\" maximum, though that alone "
            "is not specific to stickers. Note the sticker classes WERE "
            "fitted and ranked here regardless; their absence from the top is "
            "a fitted result, not a pre-filter deletion.")

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
        "challenge": challenge(result, w=w, Gp=Gp, Gpp=Gpp),
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
    L.append(f"DON'T THINK IT'S {rep['winner'].upper()}? THIS MAY BE WHY")
    L.append("-" * width)
    for c in rep["challenge"]:
        for i, chunk in enumerate(_wrap(c["text"], width - 4)):
            L.append(("  - " if i == 0 else "    ") + chunk)
    L.append("")
    for chunk in _wrap(
            "This section is printed for every result, including confident "
            "and correct ones. A caveat that appeared only when something "
            "looked wrong would imply that a quiet report means a sure "
            "answer - and that is not true here: most errors this classifier "
            "makes are GOOD fits of the WRONG class, and nothing flags them.",
            width - 2):
        L.append(f"  {chunk}")

    L.append("")
    L.append("Still disagree? Ask 'why not X?' - contest(w, Gp, Gpp, 'X') fits")
    L.append("your candidate on this same data and reports its case in full.")
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
