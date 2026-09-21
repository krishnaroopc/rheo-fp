"""Tests for the at-bound plausibility check (rheofp/plausibility.py).

These pin the two things that make the check worth having:
  1. it FIRES on the failure shape that twice changed a model verdict
     (`tdd`'s pinned M*/Me, `comb`'s pinned s_b), and
  2. it stays QUIET otherwise - a report-only warning that cries wolf on
     correct answers is noise. That is the `has_shoulder` lesson: an absent
     observation is not evidence, and a warning nobody can act on trains
     users to ignore the ones that matter.

Also pinned: the check never touches identify()'s ranking, and the module
imports no torch (same dependency rule report.py follows).
"""
import numpy as np
import pytest

from rheofp.fitting.identify import ALL_MODELS
from rheofp.plausibility import (
    AT_BOUND_FRAC, INTEGER_ROUNDED, PARAM_NAMES, SOFT_BOUND_NOTES,
    at_bound_parameters, at_bound_warning,
)


def test_every_bank_class_has_parameter_names():
    """A warning that says 'parameter 3' is useless to a rheologist.

    Also a coverage invariant in the spirit of
    test_every_generated_class_has_a_candidate_in_the_identifier_bank: if a
    class joins the bank, its parameter names must arrive with it.
    """
    for name, (_forward, p0, _bnds, _k) in ALL_MODELS.items():
        assert name in PARAM_NAMES, f"{name} has no PARAM_NAMES entry"
        assert len(PARAM_NAMES[name]) == len(p0), (
            f"{name}: {len(PARAM_NAMES[name])} names for {len(p0)} parameters")


def test_parameter_names_match_the_fitted_k():
    """The names must line up with what AICc is charged for."""
    for name, (_f, p0, bnds, k) in ALL_MODELS.items():
        assert len(bnds) == len(p0) == k, (
            f"{name}: k={k} but {len(p0)} params / {len(bnds)} bounds")


def test_a_parameter_on_its_upper_bound_is_detected():
    lo, hi = ALL_MODELS["star"][2][1]          # star's Z bounds, (4, 60)
    theta = [5.5, hi, -5.0]
    pinned = at_bound_parameters("star", theta, ALL_MODELS["star"][2])
    assert [p["index"] for p in pinned] == [1]
    assert pinned[0]["side"] == "upper"
    assert pinned[0]["bound"] == pytest.approx(hi)


def test_a_parameter_on_its_lower_bound_is_detected():
    bnds = ALL_MODELS["star"][2]
    theta = [5.5, bnds[1][0], -5.0]            # Z at its floor of 4
    pinned = at_bound_parameters("star", theta, bnds)
    assert [p["index"] for p in pinned] == [1]
    assert pinned[0]["side"] == "lower"


def test_an_interior_vector_is_silent():
    """The quiet case, which is most calls."""
    bnds = ALL_MODELS["star"][2]
    mids = [0.5 * (lo + hi) for lo, hi in bnds]
    assert at_bound_parameters("star", mids, bnds) == []
    assert at_bound_warning("star", mids, bnds) is None


def test_tolerance_is_relative_to_the_bound_span():
    """A fixed absolute tolerance would be wrong across parameters whose
    ranges span 3 decades (n_e in (0.05, 0.9)) and 200 (Z in (2, 200))."""
    bnds = [(0.0, 1000.0)]
    inside = [1000.0 - 2.0 * AT_BOUND_FRAC * 1000.0]
    edge = [1000.0 - 0.5 * AT_BOUND_FRAC * 1000.0]
    assert at_bound_parameters("zimm", inside, bnds) == []
    assert len(at_bound_parameters("zimm", edge, bnds)) == 1


def test_the_tdd_failure_shape_is_what_this_detects():
    """`tdd` was REJECTED because M*/Me pinned to its upper bound of 60 while
    Z error blew out to +50-60%. That was caught by a human reading one
    number. Assert the mechanical check would have caught it.

    Stand-in: the same shape in a bank class - a 4-parameter vector with the
    last parameter hard against its ceiling.
    """
    bnds = ALL_MODELS["sticky_reptation"][2]
    theta = [3.0, 3.0, 10.0, bnds[3][1]]
    warn = at_bound_warning("sticky_reptation", theta, bnds)
    assert warn is not None
    assert warn["n_hard"] == 1
    assert "not a measurement" in warn["text"]
    # It must name the parameter in rheologist's language, not "parameter 4".
    assert "sticker lifetime" in warn["text"]


def test_a_soft_bound_is_reported_but_not_called_a_hard_failure():
    """star's Z floor of 4 is the identifiability limit ASSERTING itself, not
    a numerical wall - refitting at floors 4/3/2/1 left two weakly entangled
    arms at Z = 9.12 and 6.66, unmoved. So a Z at the floor must be explained,
    NOT counted as a reason to distrust the vector.
    """
    bnds = ALL_MODELS["star"][2]
    warn = at_bound_warning("star", [5.5, bnds[1][0], -5.0], bnds)
    assert warn is not None
    assert warn["n_hard"] == 0
    assert "not a reportable output" in warn["text"]
    assert "not a measurement" not in warn["text"]


def test_critical_gel_exponent_bounds_are_physics_not_a_wall():
    """u is confined to (0,1) by Winter-Chambon. Landing near an edge means
    'barely a gel', so it must not be reported as a fitter failure."""
    bnds = ALL_MODELS["critical_gel"][2]
    warn = at_bound_warning("critical_gel", [3.0, bnds[1][1]], bnds)
    assert warn is not None
    assert warn["n_hard"] == 0
    assert "physically confined" in warn["text"]


def test_soft_bound_notes_reference_real_classes_and_parameters():
    """Guard against a note drifting off the parameter it explains."""
    for (cls, idx), _note in SOFT_BOUND_NOTES.items():
        assert cls in ALL_MODELS or cls == "comb", cls
        if cls in ALL_MODELS:
            assert idx < len(ALL_MODELS[cls][2]), f"{cls}[{idx}] out of range"


def test_mixed_hard_and_soft_pins_count_only_the_hard_ones():
    bnds = ALL_MODELS["star"][2]
    # G_N at its ceiling (hard) AND Z at its floor (soft).
    warn = at_bound_warning("star", [bnds[0][1], bnds[1][0], -5.0], bnds)
    assert warn["n_hard"] == 1
    assert len(warn["pinned"]) == 2
    assert "not a measurement" in warn["text"]


def test_unknown_class_degrades_gracefully():
    """comb is NOT in the bank but is the class this check was validated on,
    so a name absent from PARAM_NAMES must still work."""
    pinned = at_bound_parameters("comb", [1.0, 2.0], [(0.0, 1.0), (0.0, 10.0)])
    assert len(pinned) == 1
    assert pinned[0]["param"] == "parameter 1"


def test_none_inputs_are_safe():
    assert at_bound_parameters("star", None, ALL_MODELS["star"][2]) == []
    assert at_bound_parameters("star", [1, 2, 3], None) == []


def test_degenerate_bounds_are_skipped():
    """A zero-width or non-finite bound has no meaningful 'edge'."""
    assert at_bound_parameters("zimm", [1.0], [(1.0, 1.0)]) == []
    assert at_bound_parameters("zimm", [1.0], [(-np.inf, np.inf)]) == []


def test_plausibility_does_not_import_torch():
    """Same dependency rule report.py follows: the reporting layer stays
    importable without the ML stack."""
    import sys
    import importlib
    for mod in ("rheofp.plausibility",):
        sys.modules.pop(mod, None)
    had_torch = "torch" in sys.modules
    importlib.import_module("rheofp.plausibility")
    if not had_torch:
        assert "torch" not in sys.modules


def test_the_check_is_report_only():
    """It must not mutate what it is handed - identify()'s ranking entries
    are passed in directly."""
    bnds = ALL_MODELS["star"][2]
    theta = np.array([5.5, bnds[1][1], -5.0])
    before = theta.copy()
    at_bound_warning("star", theta, bnds)
    assert np.array_equal(theta, before)


def test_branched_n_e_ceiling_is_a_real_wall_not_a_soft_bound():
    """Pins the finding from docs/at_bound_calibration_2026-09-21.md.

    On the project's flagship real branched data (Pivokonsky LDPE) the BSW
    terminal-wedge exponent n_e sits ON its 0.90 ceiling, and widening the
    ceiling lets it chase all the way to 2.0 with rms improving monotonically
    - more than double BSW's own stated physical range of ~0.2-0.7. So this
    bound must keep producing a HARD warning; marking it soft would hide the
    third independent demonstration of BSW's over-flexibility.
    """
    bnds = ALL_MODELS["branched"][2]
    assert ("branched", 3) not in SOFT_BOUND_NOTES
    warn = at_bound_warning("branched", [2.80, 1.97, 1.43, bnds[3][1], 0.55], bnds)
    assert warn is not None
    assert warn["n_hard"] == 1
    assert "terminal wedge exponent" in warn["text"]
    assert "not a measurement" in warn["text"]


def test_integer_rounded_mode_counts_use_a_half_unit_band():
    """The forward models round mode counts (`int(round(N))`) and clip Z with
    `max(2.0, Z)`, so the float the fitter reports is NOT what the model used.
    A fitted N = 2.4 against a floor of 2 is a model running AT its floor.
    AT_BOUND_FRAC on a (2, 200) span is only 0.198, well inside that half-unit
    band, so without the widening these would be missed entirely.
    """
    bnds = ALL_MODELS["zimm"][2]
    assert ("zimm", 2) in INTEGER_ROUNDED
    # 2.4 rounds to 2 == the floor, so it must be reported.
    pinned = at_bound_parameters("zimm", [2.0, 0.0, 2.4], bnds)
    assert [p["index"] for p in pinned] == [2]
    assert pinned[0]["side"] == "lower"
    # 3.6 rounds to 4, comfortably off the floor -> silent.
    assert at_bound_parameters("zimm", [2.0, 0.0, 3.6], bnds) == []


def test_non_integer_parameters_keep_the_tight_tolerance():
    """The half-unit band must NOT leak onto continuous parameters, or an
    exponent like n_e (span 0.85) would be 'at bound' everywhere."""
    bnds = ALL_MODELS["branched"][2]
    assert ("branched", 3) not in INTEGER_ROUNDED
    # n_e = 0.5 is mid-range; a half-unit band would wrongly flag it.
    assert at_bound_parameters("branched", [3.0, 1.0, -1.0, 0.5, 0.55], bnds) == []


def test_integer_rounded_entries_point_at_real_count_parameters():
    """Guard against an INTEGER_ROUNDED key drifting onto the wrong index -
    the same failure mode SOFT_BOUND_NOTES is guarded against."""
    for cls, idx in INTEGER_ROUNDED:
        assert cls in ALL_MODELS, cls
        assert idx < len(ALL_MODELS[cls][2]), f"{cls}[{idx}] out of range"
        # every one of these must be a count-like parameter, by its own name
        assert PARAM_NAMES[cls][idx][1] == "count", (
            f"{cls}[{idx}] is {PARAM_NAMES[cls][idx]}, not a count")
