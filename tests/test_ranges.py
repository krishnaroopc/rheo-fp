"""Tests for the literature range table (rheofp/ranges.py), Plan A step 2.

The range check answers the question the at-bound check cannot: a parameter
can sit comfortably inside its bounds and still describe no real material.
`n_e` is the standing example - it was caught in step 1 only because its
bound happens to sit at 0.90; had the bound been 2.0, n_e = 1.4 would have
passed silently while being twice BSW's stated physical range.

These tests pin: the ranges are literature-grounded (not copies of synth.py's
sampling ranges, which would make the check circular), the log10 handling is
right, the indices agree with plausibility.PARAM_NAMES, and the five
deliberately-unranged classes stay silent.
"""
import numpy as np
import pytest

from rheofp.fitting.identify import ALL_MODELS
from rheofp.plausibility import PARAM_NAMES
from rheofp.ranges import (
    BSW_N_E, CURED_M, EXPECTED, GEL_U, G_PLATEAU_PA, Z_STAR_ARM,
    out_of_range_parameters, out_of_range_warning,
)


def test_scope_is_the_five_classes_with_a_documented_real_failure():
    """Plan A scoped this to branched, star, reptation, cured_elastomer and
    critical_gel. The other five have no real-data failure to calibrate a
    range against, and inventing one would be guessing dressed as physics."""
    assert set(EXPECTED) == {
        "branched", "star", "reptation", "cured_elastomer", "critical_gel"}


def test_every_ranged_class_is_in_the_bank_with_valid_indices():
    for name, spec in EXPECTED.items():
        assert name in ALL_MODELS, name
        k = len(ALL_MODELS[name][2])
        for idx in spec:
            assert 0 <= idx < k, f"{name}[{idx}] out of range for k={k}"


def test_range_labels_agree_with_the_at_bound_parameter_names():
    """The two reporting modules describe the same parameters, so a reader
    must not see 'entanglements per arm Z' in one and something else in the
    other. Guards against the indices drifting apart."""
    for name, spec in EXPECTED.items():
        for idx, (_rng, _log, label, _why) in spec.items():
            other = PARAM_NAMES[name][idx][0]
            # Compare on the distinctive symbol, not the whole phrase.
            key = label.split()[-1]
            assert key in other, (
                f"{name}[{idx}]: ranges says '{label}', "
                f"plausibility says '{other}'")


def test_every_range_is_ordered_and_positive_width():
    for name, spec in EXPECTED.items():
        for idx, (rng, _log, label, _why) in spec.items():
            lo, hi = rng
            assert lo < hi, f"{name}[{idx}] ({label}): {lo} !< {hi}"


def test_a_value_inside_its_range_is_silent():
    # branched: G_N = 10^5 Pa = 100 kPa, n_e = 0.5, n_g = 0.55 - all ordinary.
    assert out_of_range_parameters("branched", [5.0, 1.0, -1.0, 0.5, 0.55]) == []
    assert out_of_range_warning("branched", [5.0, 1.0, -1.0, 0.5, 0.55]) is None


def test_log10_parameters_are_exponentiated_before_comparison():
    """Moduli are fitted as log10 Pa. A raw 5.0 means 100 kPa, which is fine;
    comparing 5.0 directly against a Pascal range would be nonsense.

    Uses `star`, whose G_N IS a real plateau modulus. (`branched`'s G_N is
    deliberately unranged - see the note in ranges.EXPECTED.)"""
    assert out_of_range_parameters("star", [5.0, 15.0, -5.0]) == []
    bad = out_of_range_parameters("star", [1.0, 15.0, -5.0])   # 10 Pa
    assert [b["index"] for b in bad] == [0]
    assert bad[0]["side"] == "below"
    assert bad[0]["value"] == pytest.approx(10.0)
    assert bad[0]["is_log10"] is True


def test_the_branched_n_e_finding_is_what_this_catches_independently_of_bounds():
    """>>> The reason this module exists. <<<

    On both real Pivokonsky LDPE melts n_e fits to 0.90 and chases 2.0 when
    freed, against BSW's own stated ~0.2-0.7. Step 1 caught it only because
    the bound sits at 0.90. This must catch it on the VALUE, so that widening
    the bound could never hide it.
    """
    assert BSW_N_E[1] < 0.90, (
        "the n_e range must exclude the measured real-LDPE value of 0.90, or "
        "this check cannot see the open BSW finding")
    bad = out_of_range_parameters("branched", [2.8, 1.97, 1.43, 0.90, 0.55])
    assert [b["index"] for b in bad] == [3]
    assert bad[0]["side"] == "above"
    # And it must still catch it if the bound were ever widened.
    bad2 = out_of_range_parameters("branched", [2.8, 1.97, 1.43, 2.0, 0.55])
    assert [b["index"] for b in bad2] == [3]


def test_ranges_are_not_copies_of_the_generator_sampling_ranges():
    """The user's instruction was literature grounding, so this stays an
    INDEPENDENT check rather than a circular one. If a range were lifted from
    synth.py, the check could only ever confirm 'looks like training data'."""
    from rheofp.data import synth
    assert tuple(BSW_N_E) != tuple(synth.BRANCHED_N_E)
    # n_e in particular: synth plants (0.15, 0.75); a copy would be a bug.
    assert BSW_N_E[0] != synth.BRANCHED_N_E[0] or BSW_N_E[1] != synth.BRANCHED_N_E[1]


def test_star_arm_entanglements_bracket_the_real_mm1998_set():
    """The documented literature reading must contain MM1998's seven real
    four-arm PI stars (Z ~ 2.2-21). Kept as a constant even though the range
    is not shipped - star's Z bounds (4, 60) already bind first."""
    lo, hi = Z_STAR_ARM
    assert lo <= 2.2 and hi >= 21.0
    assert 1 not in EXPECTED["star"], (
        "star's Z range is redundant against STAR_BNDS - see the "
        "REDUNDANT-RANGE note in ranges.py")


def test_every_shipped_range_is_actually_reachable():
    """>>> Guards against shipping dead code that LOOKS like a check. <<<

    If a parameter's bounds are already stricter than its literature range,
    the range can never fire, and an entry for it implies a check that is not
    happening. Three candidate entries were removed on exactly this basis
    (branched n_g, reptation Z, star Z); this test stops them coming back and
    stops new ones being added inertly.
    """
    for name, spec in EXPECTED.items():
        bnds = ALL_MODELS[name][2]
        for idx, (rng, is_log10, label, _why) in spec.items():
            lo, hi = bnds[idx]
            blo = 10.0**lo if is_log10 else lo
            bhi = 10.0**hi if is_log10 else hi
            rlo, rhi = rng
            assert blo < rlo or bhi > rhi, (
                f"{name}[{idx}] ({label}): bounds ({blo:.4g}, {bhi:.4g}) lie "
                f"inside range ({rlo:.4g}, {rhi:.4g}), so this entry can "
                f"never fire. Remove it or widen the bound.")


def test_gel_exponent_range_contains_the_real_tixier_values():
    """Tixier et al. (2004) measure u = 0.69-0.75 on real PDMS gels."""
    lo, hi = GEL_U
    assert lo <= 0.69 and hi >= 0.75
    assert out_of_range_parameters("critical_gel", [3.0, 0.72]) == []


def test_gel_exponent_outside_zero_to_one_is_flagged():
    bad = out_of_range_parameters("critical_gel", [3.0, 0.99])
    assert [b["index"] for b in bad] == [1]
    assert bad[0]["side"] == "above"


def test_cured_exponent_range_is_small_by_construction():
    """m is small for a cured network - the modulus is nearly flat."""
    assert CURED_M[1] < 1.0
    assert out_of_range_parameters("cured_elastomer", [5.0, 3.5, 0.2]) == []
    bad = out_of_range_parameters("cured_elastomer", [5.0, 3.5, 0.9])
    assert [b["index"] for b in bad] == [2]


def test_unranged_classes_are_always_silent():
    """Absence of a range is not evidence of a problem."""
    for name in set(ALL_MODELS) - set(EXPECTED):
        p0 = ALL_MODELS[name][1]
        assert out_of_range_parameters(name, p0) == []
        assert out_of_range_warning(name, p0) is None


def test_none_and_short_vectors_are_safe():
    assert out_of_range_parameters("branched", None) == []
    # A truncated vector must not raise - indices past the end are skipped.
    assert out_of_range_parameters("branched", [5.0]) == []


def test_non_finite_values_are_skipped_not_flagged():
    bad = out_of_range_parameters("branched", [np.nan, 1.0, -1.0, 0.5, 0.55])
    assert bad == []


def test_warning_text_names_the_parameter_and_the_reason():
    warn = out_of_range_warning("branched", [2.8, 1.97, 1.43, 0.90, 0.55])
    assert warn is not None
    assert "terminal wedge exponent n_e" in warn["text"]
    assert "Baumgaertel" in warn["text"]
    # It must say what an out-of-range value MEANS, not just that it happened.
    assert "do not describe any real material" in warn["text"]


def test_moduli_are_reported_in_readable_units():
    """A rheologist reads kPa and MPa, not 1.2e+06."""
    warn = out_of_range_warning("star", [8.0, 15.0, -5.0])   # 100 MPa
    assert "MPa" in warn["text"]


def test_the_check_does_not_mutate_its_input():
    theta = np.array([2.8, 1.97, 1.43, 0.90, 0.55])
    before = theta.copy()
    out_of_range_warning("branched", theta)
    assert np.array_equal(theta, before)


def test_ranges_does_not_import_torch():
    import importlib
    import sys
    sys.modules.pop("rheofp.ranges", None)
    had_torch = "torch" in sys.modules
    importlib.import_module("rheofp.ranges")
    if not had_torch:
        assert "torch" not in sys.modules


def test_branched_G_N_is_deliberately_unranged():
    """>>> A near-miss caught by these tests, worth pinning. <<<

    BSW's G_N is a WINDOW-LIMITED AMPLITUDE SCALE, not a measured plateau
    modulus (CLAUDE.md says so explicitly), so Fetters' plateau values do not
    apply to it. The real Pivokonsky LDPE melts fit G_N = 635 Pa and 1108 Pa -
    the softer one sits BELOW a 1 kPa plateau floor while being a CORRECT
    `branched` call on real LDPE. Ranging it produced a permanent false alarm
    on the project's own branched benchmark, which is the exact mistake this
    table exists to avoid making about other people's fits.
    """
    assert 0 not in EXPECTED["branched"]
    # Both real fitted amplitudes must be silent.
    for lg in (np.log10(635.0), np.log10(1108.0)):
        assert out_of_range_parameters(
            "branched", [lg, 1.97, 1.43, 0.5, 0.55]) == []
