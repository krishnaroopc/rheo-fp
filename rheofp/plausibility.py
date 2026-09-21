"""Is the WINNING class's fitted vector physically plausible?

REPORTING ONLY. Nothing here feeds back into `identify()`'s ranking, by the
same rule `report.py` and `plain_language.py` follow: the dependency runs
`plausibility -> report`, never back. This module imports no torch and does
not import `report` or `neural_report`.

>>> THE GAP THIS CLOSES <<<
`identify()` cross-checks the two brains' LABELS against each other
(agree/disagree) and `report.py` checks the winner's absolute fit QUALITY
(`FLOOR_CHI2`). Nothing checked whether the winner's fitted NUMBERS describe a
physically realizable material. That is a real blind spot, because this
project's characteristic error is a GOOD FIT OF THE WRONG CLASS - which no
confidence score and no fit-quality floor flags.

>>> WHY AT-BOUND SPECIFICALLY: it has already decided two model verdicts <<<
A fitted parameter sitting on its bound is not a measurement. The optimiser
wanted to keep going and the wall stopped it, so the value reports the wall's
position, not the sample's. Worse, in this project's experience such a
parameter is usually ABSORBING MISFIT for the rest of the vector. Twice now
that has been caught by a human reading one number, and both times it changed
a decision:

  * `tdd` (2026-09-18) was REJECTED for it. Freeing `M*/Me` made TDD-DR beat
    BSW 3/3 - the result the project had chased for a month - but `M*/Me`
    pinned to its upper bound of 60 and the recovered `Z` error blew out from
    +4.6%/+6.5% to +50.2%/+60.4%. Winning by flexibility while destroying the
    one physical quantity the class exists to report.
  * `comb` (2026-09-21) was diagnosed by it. `s_b` pins to its ceiling of 120
    on EIGHT of nine real Kapnistos combs, which is why their rms is 0.24-0.39
    - the model is not fitting an architecture, it has run out of cross-bar.
    See `docs/comb_reparameterisation_diagnosis.md`.

Both were found by hand, after the fact, on curves someone happened to look
at. This makes it automatic, for every class, on every call.

>>> WHAT THIS IS NOT <<<
An at-bound parameter is a reason to DISTRUST A NUMBER, not evidence that the
class is wrong. Three of the ten classes have bounds that a perfectly ordinary
sample can legitimately reach - see `SOFT_BOUND_NOTES` - and `critical_gel`'s
`u` is an exponent whose physical range IS its bound. So this reports; it
never discards a candidate and never reorders the ranking. That restraint is
the project's own standing rule: a hard discard needs a POSITIVE observation
(`terminal_reached`, `confident_entangled`), and "the fitter hit a wall" is
not an observation about the sample.
"""
import numpy as np

# A parameter counts as "at" its bound within this fraction of the bound's own
# span. L-BFGS-B lands exactly on a bound when it is pushing against one, so a
# tight tolerance is enough; it is not zero because the optimiser can stop a
# hair short and because a log10 parameter's last digits are not meaningful.
AT_BOUND_FRAC = 1e-3

# >>> MODE COUNTS ARE ROUNDED INSIDE THE FORWARD MODELS, so the float the
# fitter reports is not the value the model used. <<<
# `model_zimm`/`model_rouse` do `N = max(2, int(round(N)))`, the sticky models
# do the same for their mode counts, and the reptation family clips Z with
# `max(2.0, Z)`. The EFFECTIVE parameter therefore snaps to an integer, and a
# fitted 2.4 against a floor of 2 is a model running at its floor even though
# 2.4 is 0.4 away from it. AT_BOUND_FRAC on a (2, 200) span is 0.198, well
# inside that half-unit band, so these would be missed. Measured 2026-09-21.
# For the parameters listed here, "at bound" also means "rounds onto the
# bound". Keyed (class, index) exactly like SOFT_BOUND_NOTES so it cannot
# silently drift onto the wrong parameter (there is a test).
INTEGER_ROUNDED = frozenset({
    ("zimm", 2), ("rouse_screened", 2),          # number of Rouse modes N
    ("reptation", 2),                            # entanglements Z (clipped)
    ("sticky_rouse", 3),                         # Rouse modes per strand
    ("sticky_reptation", 2),                     # entanglements Z (clipped)
})

# Parameter names and units, per class, in fitted order. These are the names a
# rheologist uses, not the internal symbols - the audience for a report is a
# materials scientist, not someone reading this source. Sources: each model's
# own `model_*` docstring in rheofp/models/.
PARAM_NAMES = {
    "zimm": [
        ("G scale", "log10 Pa"), ("longest relaxation time", "log10 s"),
        ("number of Rouse modes N", "count"),
    ],
    "rouse_screened": [
        ("G scale", "log10 Pa"), ("longest relaxation time", "log10 s"),
        ("number of Rouse modes N", "count"),
    ],
    "reptation": [
        ("plateau modulus Ge", "log10 Pa"), ("disengagement time tau_d", "log10 s"),
        ("entanglements per chain Z", "count"),
    ],
    "sticky_rouse": [
        ("transient-network plateau Gs", "log10 Pa"),
        ("sticker lifetime tau_s", "log10 s"),
        ("strand Rouse time tau_R", "log10 s"),
        ("Rouse modes per strand", "count"),
    ],
    "sticky_reptation": [
        ("entanglement plateau Ge", "log10 Pa"),
        ("sticky-reptation terminal time tau_st", "log10 s"),
        ("entanglements per chain Z", "count"),
        ("sticker lifetime tau_s", "log10 s"),
    ],
    "cured_elastomer": [
        ("equilibrium modulus G_inf", "log10 Pa"),
        ("Chasset-Thirion coefficient c", "log10"),
        ("Chasset-Thirion exponent m", "-"),
    ],
    "critical_gel": [
        ("gel stiffness c", "log10"), ("critical-gel exponent u", "-"),
    ],
    "wormlike_micelle": [
        ("plateau modulus G0", "log10 Pa"),
        ("reptation time tau_rep", "log10 s"),
        ("breaking time tau_br", "log10 s"),
        ("stretching exponent beta", "-"),
    ],
    "branched": [
        ("BSW amplitude G_N", "log10 Pa"),
        ("longest relaxation time tau_max", "log10 s"),
        ("crossover time tau_c", "log10 s"),
        ("terminal wedge exponent n_e", "-"),
        ("high-frequency wedge exponent n_g", "-"),
    ],
    "star": [
        ("plateau modulus G_N", "log10 Pa"),
        ("entanglements per ARM Z", "count"),
        ("entanglement Rouse time tau_e", "log10 s"),
    ],
}

# >>> BOUNDS A LEGITIMATE SAMPLE CAN REACH, so the warning must say so. <<<
# Without these the check would cry wolf on correct answers, which is the
# `has_shoulder` missing-evidence mistake in a new costume. Keyed
# (class, parameter index) -> the note appended to that parameter's warning.
SOFT_BOUND_NOTES = {
    # star.py: below Z ~ 4 the retraction barrier is ~1-2 kBT and the cost is
    # FLAT in Z, so Z is unidentifiable there whatever the bound. Refitting at
    # floors 4/3/2/1 left two weakly-entangled arms at Z = 9.12 and 6.66,
    # unmoved - the floor is ASSERTING the identifiability limit, not causing
    # it. Z is already non-reportable for `star` (biased +17-84%).
    ("star", 1): ("`star`'s Z floor of 4 marks where a star's shape stops "
                  "depending on Z at all, so this is the expected reading for "
                  "a weakly entangled arm - not a sign the class is wrong. Z "
                  "is not a reportable output for this class in any case."),
    # critical_gel: u is the Winter-Chambon exponent. Its (0.01, 0.99) bounds
    # ARE the physical range - u must lie in (0,1) for a critical gel - so
    # landing near an edge means "barely a gel", not "the fitter escaped".
    ("critical_gel", 1): ("the critical-gel exponent is physically confined to "
                          "0 < u < 1, so this bound is the physics, not a "
                          "numerical wall. A value at the edge means the "
                          "power law is nearly elastic (u->0) or nearly "
                          "viscous (u->1)."),
    ("cured_elastomer", 2): ("the Chasset-Thirion exponent m is likewise "
                             "confined to a narrow physical range; a small m "
                             "is the ordinary reading for a well-cured "
                             "network with a nearly flat modulus."),
}


def at_bound_parameters(name, params, bounds, frac=AT_BOUND_FRAC):
    """Which fitted parameters are sitting on their bounds?

    `params` and `bounds` come straight from `identify()`'s ranking entry and
    `ALL_MODELS[name]` respectively. All ten banks' bounds are STATIC tuples
    handed directly to L-BFGS-B by `fit_model` -> `multi_restart_fit`, so
    comparing a fitted value against them is exact. (Verified 2026-09-21. If a
    class is ever given data-dependent bounds computed inside its own `fit_*`
    - as `fit_comb` and `fit_star` do for tau_e - then the static tuple stops
    being what constrained the fit and this comparison would go stale for that
    class. `comb` is not in the bank; `star`'s registry entry uses the static
    STAR_BNDS.)

    Returns a list of dicts, one per pinned parameter, in fitted order.
    """
    out = []
    if params is None or bounds is None:
        return out
    names = PARAM_NAMES.get(name)
    for i, (value, (lo, hi)) in enumerate(zip(np.asarray(params, float), bounds)):
        lo = float(lo)
        hi = float(hi)
        span = hi - lo
        if not np.isfinite(span) or span <= 0:
            continue
        tol = frac * span
        if (name, i) in INTEGER_ROUNDED:
            # The model rounds this one, so anything that rounds onto the
            # bound IS on the bound. See INTEGER_ROUNDED.
            tol = max(tol, 0.5)
        which = None
        if value <= lo + tol:
            which = "lower"
        elif value >= hi - tol:
            which = "upper"
        if which is None:
            continue
        pname, unit = (names[i] if names and i < len(names)
                       else (f"parameter {i + 1}", "-"))
        out.append({
            "index": i,
            "param": pname,
            "unit": unit,
            "value": float(value),
            "bound": lo if which == "lower" else hi,
            "side": which,
            "note": SOFT_BOUND_NOTES.get((name, i)),
        })
    return out


def at_bound_warning(name, params, bounds, frac=AT_BOUND_FRAC):
    """Report-ready warning for a winner with pinned parameters, else None.

    Phrased for a rheologist: what the number is, that it cannot be trusted,
    and what it implies about the REST of the fit - because the lesson from
    `tdd` is that a pinned parameter damages the parameters beside it, not
    only itself.
    """
    pinned = at_bound_parameters(name, params, bounds, frac=frac)
    if not pinned:
        return None

    # Written as flowing prose, NOT a newline-separated list: report.py's
    # `_wrap` splits on whitespace and collapses newlines, so an embedded
    # bullet list renders as "permitted: - terminal wedge exponent ...".
    lines = []
    for p in pinned:
        edge = "lowest" if p["side"] == "lower" else "highest"
        unit = "" if p["unit"] == "-" else f" {p['unit']}"
        lines.append(
            f"{p['param']} = {p['value']:.4g}{unit}, at the {edge} value "
            f"the fit was allowed ({p['bound']:.4g})"
            + (f" -- {p['note']}" if p["note"] else ""))

    hard = [p for p in pinned if p["note"] is None]
    joined = lines[0] if len(lines) == 1 else (
        "; ".join(lines[:-1]) + "; and " + lines[-1])
    body = (
        f"FITTED VALUES AT THEIR LIMITS. The `{name}` fit ended with "
        f"{len(pinned)} parameter{'s' if len(pinned) != 1 else ''} pressed "
        f"against the edge of the range it was permitted: {joined}.")

    if hard:
        body += (
            " A parameter stopped by its limit is not a measurement - the "
            "fit wanted to keep going and was prevented, so the value tells "
            "you where the limit is, not what the sample is. Treat "
            + ", ".join(f"'{p['param']}'" for p in hard)
            + " as unquantified. It also casts doubt on the parameters "
            "beside it: a pinned parameter tends to soak up misfit that "
            "belongs elsewhere in the vector, so the whole set is less "
            "trustworthy than its fit quality alone suggests. In this "
            "project's own history that pattern twice signalled a model "
            "winning by flexibility rather than by physics. The class may "
            "still be right - this is a reason to distrust the NUMBERS, not "
            "the label.")
    else:
        body += ("\n\nEvery value above sits at a limit that is itself "
                 "physical, so this is a note about interpretation rather "
                 "than a problem with the fit.")

    return {
        "kind": "at_bound",
        "pinned": pinned,
        "n_hard": len(hard),
        "text": body,
    }
