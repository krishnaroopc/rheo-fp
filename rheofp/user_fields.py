"""Optional things the user already knows about their sample — Plan B.

REPORTING ONLY, like `plausibility.py`, `ranges.py` and `plain_language.py`.
Nothing here reaches `identify()` or the network; the dependency runs
`user_fields -> report` and never back. No torch.

>>> WHAT THIS IS FOR <<<
The mandatory input stays what it has always been: frequency, G', G'' and
temperature. Everything else the pipeline currently has to GUESS from curve
shape. This module lets someone state what they already know and turns it
into an independent cross-check on the answer.

>>> EVERY FIELD IS OPTIONAL AND THE ZERO CASE IS THE NORMAL CASE. <<<
Most real uploads will supply none of these. `user_note()` returns None when
nothing is supplied, and no code path changes. This is load-bearing: the
project's 0.923 accuracy is measured on bare curves, and that must remain
exactly what a bare upload does.

>>> WHY THESE FOUR, AND WHY NOT AS MODEL INPUTS <<<
Each one hits a decision the code already makes badly:

  1. `Mw` - `tube.Z_of_sample(Mw, Ge)` converts a fitted plateau modulus plus
     a known molecular weight into an expected entanglement count. That
     machinery has existed in `tube.py` all along but is only used in the
     other direction (forcing Mw into validation curves); it has never been
     a user-facing cross-check. With Mw the fitted Z becomes falsifiable.
  2. `flows` - "I can confirm it pours". `terminal_reached` is one of only
     two hard discards the project trusts, and it is ALREADY DOCUMENTED to
     miss a visibly flowing sample: Pryke's Ma38k measures 1.39 against a
     1.4 cutoff while plainly flowing (raw terminal slopes 1.87/0.85,
     G''/G' = 33 at the lowest point). A person's direct observation is
     better evidence than a slope estimate that can miss by a rounding error.
  3. `solvent_present` - the axis behind the single biggest error source in
     the classifier. Zimm vs Rouse-screened is 58% of all remaining error and
     is essentially "good solvent or screened", which is currently inferred
     from spectral shape alone.
  4. `suspected_class` - what the user thinks it is.

>>> #4 IS DELIBERATELY KEPT OUT OF THE MODEL, AND THAT IS THE WHOLE POINT. <<<
A claimed architecture is shown ALONGSIDE the tool's independent answer,
never fed into classification. Blending it in would teach the model to defer
to a claim that may be wrong or partial, and would destroy the only thing
that makes the comparison worth printing: that the two were arrived at
independently. Same principle as `neural_report.pair_note()`, which prints
`YOUR SHORTLIST: A or B` on a two-brain disagreement and refuses to average
them into one verdict.

>>> WHAT IS NOT BUILT HERE <<<
Promoting `flows` / `solvent_present` into actual TRAINED NETWORK INPUTS. That
needs a presence-flag per field (real value vs placeholder) and training with
fields randomly blanked (feature dropout), so the network cannot learn to
lean on a field that is usually absent - plus an ablation showing accuracy
with zero fields supplied reproduces 0.923 unchanged. That is a retraining
experiment, and it is only worth doing if this report-time version proves
useful first.
"""
import numpy as np

from rheofp.models.tube import Z_of_sample

# Which classes carry a fitted plateau modulus that Z_of_sample can use, and
# at which index. Only these support the Mw cross-check; asking for an
# entanglement count from a critical gel is meaningless.
# Keyed the same (class -> index) way as ranges.EXPECTED and
# plausibility.PARAM_NAMES, so a test can check the three agree.
PLATEAU_INDEX = {
    "reptation": 0,          # Ge, log10 Pa
    "sticky_reptation": 0,   # Ge, log10 Pa
    "star": 0,               # G_N, log10 Pa - but see the caveat below
}

# The fitted Z, for classes that report one.
Z_INDEX = {
    "reptation": 2,
    "sticky_reptation": 2,
    "star": 1,
}

# >>> HOW CLOSE COUNTS AS AGREEMENT <<<
# Z_of_sample inverts Ge = rho R T / Me, so the expected Z inherits every
# uncertainty in rho, T and the plateau reading. Liu et al. (2006) measure the
# METHOD spread on G_N alone at 5-10% (monodisperse) to 15% (polydisperse),
# and published values for one polymer can differ by a factor of 3.4
# (bisphenol-A PC, their Table 9). Z is linear in 1/Ge, so that propagates
# directly. On top of that `tube.py`'s defaults are POLYSTYRENE at 180 C
# (RHO_DEFAULT = 959 kg/m^3, TEMP_DEFAULT = 453.15 K) - wrong for any other
# chemistry unless the caller overrides them.
# So: only a factor-of-2 disagreement is worth reporting. Anything tighter
# would fire on correct answers, which is the standard the at-bound and range
# checks were both held to.
Z_FACTOR_TOLERANCE = 2.0


def mw_cross_check(name, params, mw_g_per_mol, rho=None, temp_k=None):
    """Compare the fitted Z against the Z implied by a user-supplied Mw.

    Returns None when the class carries no plateau modulus and no Z, when no
    Mw was given, or when the inputs are not finite. Otherwise a dict with
    both counts and whether they agree within `Z_FACTOR_TOLERANCE`.

    `rho` (kg/m^3) and `temp_k` default to `tube.py`'s polystyrene-at-180C
    values; pass them for any other chemistry or the expected Z is wrong by
    the ratio of the densities and temperatures.
    """
    if mw_g_per_mol is None or name not in PLATEAU_INDEX:
        return None
    try:
        mw = float(mw_g_per_mol)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(mw) or mw <= 0 or params is None:
        return None

    values = np.asarray(params, float)
    i_ge = PLATEAU_INDEX[name]
    i_z = Z_INDEX.get(name)
    if i_ge >= len(values) or i_z is None or i_z >= len(values):
        return None
    if not np.isfinite(values[i_ge]) or not np.isfinite(values[i_z]):
        return None

    ge = 10.0**float(values[i_ge])       # plateau moduli are fitted as log10
    fitted_z = float(values[i_z])
    kwargs = {}
    if rho is not None:
        kwargs["rho"] = float(rho)
    if temp_k is not None:
        kwargs["temp"] = float(temp_k)
    expected_z = float(Z_of_sample(mw, ge, **kwargs))
    if not np.isfinite(expected_z) or expected_z <= 0 or fitted_z <= 0:
        return None

    ratio = fitted_z / expected_z
    agrees = (1.0 / Z_FACTOR_TOLERANCE) <= ratio <= Z_FACTOR_TOLERANCE
    return {
        "fitted_z": fitted_z,
        "expected_z": expected_z,
        "ratio": ratio,
        "agrees": agrees,
        "mw": mw,
        "plateau_pa": ge,
        "defaults_used": rho is None and temp_k is None,
    }


def flow_contradiction(name, feats, flows):
    """Does a user-observed flow state contradict what the curve suggested?

    Two directions, and they are NOT symmetric:

      * user says it FLOWS but `terminal_reached` is False -> the sample is a
        melt whose terminal zone is outside the window, or the threshold
        missed it. This is the documented Pryke Ma38k case (1.39 against a
        1.4 cutoff, while pouring). If a NETWORK class won, that is a real
        contradiction: a permanent network cannot flow.
      * user says it does NOT flow but `terminal_reached` is True -> flow was
        measured. Either the observation is about a different timescale (a
        material can be solid to the hand and liquid over hours) or something
        is wrong with the data.
    """
    if flows is None or feats is None:
        return None
    observed = bool(feats.get("terminal_reached"))
    flows = bool(flows)
    if flows == observed:
        return None
    network_won = name in ("cured_elastomer", "critical_gel")
    return {
        "user_flows": flows,
        "terminal_reached": observed,
        "network_won": network_won,
        "slope_Gp_lo": feats.get("slope_Gp_lo"),
        "slope_Gpp_lo": feats.get("slope_Gpp_lo"),
    }


def user_note(name, params, feats=None, mw_g_per_mol=None, flows=None,
              solvent_present=None, suspected_class=None,
              rho=None, temp_k=None):
    """Report-ready note from whatever optional fields were supplied.

    Returns None when nothing was supplied or nothing is worth saying - the
    normal case for a bare upload.
    """
    parts = []

    # 1. Mw -> expected entanglement count.
    mw = mw_cross_check(name, params, mw_g_per_mol, rho=rho, temp_k=temp_k)
    if mw is not None:
        if mw["agrees"]:
            parts.append(
                f"YOUR Mw AGREES WITH THE FIT. At Mw = {mw['mw']:.3g} g/mol "
                f"and the fitted plateau modulus, you would expect about "
                f"{mw['expected_z']:.1f} entanglements per chain; the fit "
                f"independently returned {mw['fitted_z']:.1f}. That is a "
                "genuine consistency check - the fit never saw your Mw.")
        else:
            direction = "more" if mw["ratio"] > 1 else "fewer"
            parts.append(
                f"YOUR Mw DISAGREES WITH THE FIT. At Mw = {mw['mw']:.3g} "
                f"g/mol and the fitted plateau modulus you would expect about "
                f"{mw['expected_z']:.1f} entanglements per chain, but the fit "
                f"returned {mw['fitted_z']:.1f} - a factor of "
                f"{max(mw['ratio'], 1 / mw['ratio']):.1f} {direction}. Either "
                "the class is wrong, the plateau is being read off the wrong "
                "part of the curve, or the sample is more polydisperse than a "
                "single Mw describes.")
        if mw["defaults_used"]:
            parts.append(
                "Note the expected count above assumes polystyrene's density "
                "at 180 C, because no density or temperature was supplied. "
                "For another chemistry it scales with density and absolute "
                "temperature, so treat a borderline disagreement cautiously.")

    # 2. Observed flow vs measured flow.
    flow = flow_contradiction(name, feats, flows)
    if flow is not None:
        if flow["user_flows"]:
            txt = ("YOU SAY IT FLOWS, BUT THIS CURVE DOES NOT SHOW FLOW. "
                   "The low-frequency slopes did not reach the terminal "
                   "values this tool requires")
            if flow["slope_Gp_lo"] is not None:
                txt += (f" (G' slope {flow['slope_Gp_lo']:.2f}, needs > 1.4)")
            txt += (". That threshold is known to be sharp: a real flowing "
                    "star melt has measured 1.39 and missed it by 0.01. Your "
                    "observation is the better evidence. ")
            txt += ("Because a permanent network cannot flow at any "
                    "temperature, a flowing sample means this network answer "
                    "is wrong - treat it as refuted."
                    if flow["network_won"] else
                    "The likely reading is that your terminal zone lies below "
                    "the lowest frequency measured; extending the sweep down "
                    "or raising the temperature would show it.")
            parts.append(txt)
        else:
            parts.append(
                "YOU SAY IT DOES NOT FLOW, BUT THIS CURVE DOES SHOW FLOW. "
                "The low-frequency slopes reached terminal values, which is a "
                "positive observation of flow on the timescale measured. A "
                "material can be solid to the hand and still flow over hours "
                "- if that is not the case here, check the sample and the "
                "low-frequency points, which are the noisiest.")

    # 3. Solvent, against the degenerate pair it bears on.
    if solvent_present is not None:
        unentangled = name in ("zimm", "rouse_screened")
        if bool(solvent_present):
            parts.append(
                "YOU REPORT SOLVENT PRESENT. "
                + ("That supports a solution class. Which of the two you get "
                   "(good-solvent vs screened) turns on concentration, and "
                   "this tool cannot measure concentration from one curve - "
                   "these two classes account for most of its remaining "
                   "confusion, so treat the choice between them as open."
                   if unentangled else
                   f"`{name}` is a MELT class, which does not assume a "
                   "solvent. If your sample is a solution, that is a real "
                   "disagreement worth resolving before trusting this label."))
        else:
            parts.append(
                "YOU REPORT NO SOLVENT (a melt). "
                + ("`zimm` and `rouse_screened` are SOLUTION classes, so a "
                   "solvent-free sample contradicts this label. The fitted "
                   "spectral shape may still be right while the class name is "
                   "not - an unentangled melt is not in this bank."
                   if unentangled else
                   "That is consistent with this melt class."))

    # 4. The user's own guess, shown beside the answer, never blended into it.
    if suspected_class:
        claimed = str(suspected_class).strip()
        if claimed and claimed != name:
            parts.append(
                f"YOU SUSPECTED `{claimed}` AND THIS TOOL SAYS `{name}`. "
                "These were reached independently - your guess was not used "
                "in the fit, deliberately, so that this comparison means "
                "something. Treat it as a two-item shortlist to settle with "
                "what you know about the sample's synthesis, not as one "
                "answer overruling the other. If you want the case for your "
                f"candidate on this same data, contest(w, Gp, Gpp, "
                f"'{claimed}') fits it and reports in full.")
        elif claimed:
            parts.append(
                f"YOU SUSPECTED `{claimed}` AND THIS TOOL AGREES. Your guess "
                "was not used in the fit, so this is an independent "
                "confirmation rather than the tool echoing you back.")

    if not parts:
        return None
    return {"kind": "user_fields", "text": " ".join(parts)}
