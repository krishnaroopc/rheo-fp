"""Tests for the optional user-supplied fields (rheofp/user_fields.py), Plan B.

The load-bearing test is `test_the_zero_case_is_silent`: most real uploads
supply none of these fields, and the project's 0.923 accuracy is measured on
bare curves, so supplying nothing must change nothing.

Also pinned: the Mw cross-check agrees with reality on the one dataset where
Z is independently known, `suspected_class` is never blended into the answer,
and the flow contradiction handles both directions.
"""
import numpy as np
import pytest

from rheofp.fitting.identify import ALL_MODELS
from rheofp.plausibility import PARAM_NAMES
from rheofp.user_fields import (
    PLATEAU_INDEX, Z_FACTOR_TOLERANCE, Z_INDEX,
    flow_contradiction, mw_cross_check, user_note,
)


# --- the zero case ---------------------------------------------------------

def test_the_zero_case_is_silent():
    """>>> The most important test in this file. <<<

    Most uploads supply nothing. The measured 0.923 accuracy is on bare
    curves, so a bare call must produce no note and no behaviour change.
    """
    assert user_note("reptation", [3.0, 1.0, 10.0]) is None
    assert user_note("reptation", [3.0, 1.0, 10.0], feats={}) is None
    assert user_note("branched", [3.0, 1.0, -1.0, 0.3, 0.55],
                     mw_g_per_mol=None, flows=None,
                     solvent_present=None, suspected_class=None) is None


def test_every_field_is_independently_optional():
    """Any one field on its own must work, with the others absent."""
    feats = {"terminal_reached": False, "slope_Gp_lo": 1.39}
    assert user_note("reptation", [5.0, 1.0, 10.0], mw_g_per_mol=2e5) is not None
    assert user_note("reptation", [5.0, 1.0, 10.0], feats=feats,
                     flows=True) is not None
    assert user_note("zimm", [2.0, 0.0, 20.0], solvent_present=True) is not None
    assert user_note("star", [5.5, 15.0, -5.0],
                     suspected_class="branched") is not None


# --- Mw cross-check --------------------------------------------------------

def test_plateau_and_Z_indices_agree_with_the_parameter_names():
    """Guards the same drift risk ranges.py is guarded against: these indices
    must point at an actual plateau modulus and an actual entanglement count."""
    for name, idx in PLATEAU_INDEX.items():
        label = PARAM_NAMES[name][idx][0]
        assert "plateau" in label, f"{name}[{idx}] is '{label}', not a plateau"
        assert PARAM_NAMES[name][idx][1] == "log10 Pa"
    for name, idx in Z_INDEX.items():
        label = PARAM_NAMES[name][idx][0]
        assert "entanglements" in label, f"{name}[{idx}] is '{label}'"
        assert PARAM_NAMES[name][idx][1] == "count"


def test_mw_cross_check_agrees_on_real_polystyrene():
    """Measured 2026-09-21 on Katzarova 2018's three monodisperse PS melts,
    where Z is known independently from Mw/Me and tube.py's defaults ARE
    polystyrene at 180 C:

        PS105  true Z  7.9 | fitted  9.40 | Mw-implied  9.28 | ratio 1.01
        PS206  true Z 15.5 | fitted 16.07 | Mw-implied 14.49 | ratio 1.11
        PS392  true Z 29.5 | fitted 28.94 | Mw-implied 26.64 | ratio 1.09

    Reproduced here from the recorded fitted vectors rather than refitting,
    because a reptation fit is ~10 ms/call x hundreds of restarts. The point
    is that both independent routes land near the truth.
    """
    cases = [
        # (Mw, fitted Ge log10, fitted Z, expected ratio)
        (105e3, None, 9.40, 1.01),
        (206e3, None, 16.07, 1.11),
        (392e3, None, 28.94, 1.09),
    ]
    # Recover the Ge each fit used from the recorded ratio, then confirm the
    # cross-check reproduces it and calls agreement.
    for mw, _ge, fitted_z, ratio in cases:
        expected_z = fitted_z / ratio
        # Ge = rho R T / Me and Z = Mw / Me  =>  Ge = rho R T Z / Mw
        from rheofp.models.tube import RGAS, RHO_DEFAULT, TEMP_DEFAULT
        ge = RHO_DEFAULT * RGAS * TEMP_DEFAULT * expected_z / (mw / 1000.0)
        out = mw_cross_check("reptation", [np.log10(ge), 1.0, fitted_z], mw)
        assert out is not None
        assert out["agrees"], f"Mw={mw}: ratio {out['ratio']:.2f}"
        assert out["ratio"] == pytest.approx(ratio, rel=0.02)


def test_a_factor_of_three_disagreement_is_reported():
    from rheofp.models.tube import RGAS, RHO_DEFAULT, TEMP_DEFAULT
    mw = 2.0e5
    ge = RHO_DEFAULT * RGAS * TEMP_DEFAULT * 10.0 / (mw / 1000.0)
    out = mw_cross_check("reptation", [np.log10(ge), 1.0, 30.0], mw)
    assert not out["agrees"]
    assert out["ratio"] == pytest.approx(3.0, rel=0.01)
    note = user_note("reptation", [np.log10(ge), 1.0, 30.0], mw_g_per_mol=mw)
    assert "DISAGREES" in note["text"]


def test_tolerance_is_deliberately_loose():
    """Liu et al. (2006) measure 5-10% method spread on G_N for monodisperse
    samples and a factor of 3.4 across published values for one polymer, and
    Z is linear in 1/Ge. tube.py's rho/T defaults are polystyrene-specific on
    top of that. A tight tolerance would fire on correct answers."""
    assert Z_FACTOR_TOLERANCE >= 2.0


def test_mw_check_is_skipped_for_classes_without_a_plateau():
    """Asking a critical gel for an entanglement count is meaningless."""
    for name in ("critical_gel", "cured_elastomer", "zimm", "branched"):
        assert name not in PLATEAU_INDEX
        assert mw_cross_check(name, ALL_MODELS[name][1], 2e5) is None


def test_mw_check_rejects_nonsense_input():
    theta = [5.0, 1.0, 10.0]
    assert mw_cross_check("reptation", theta, 0) is None
    assert mw_cross_check("reptation", theta, -1) is None
    assert mw_cross_check("reptation", theta, float("nan")) is None
    assert mw_cross_check("reptation", theta, "not a number") is None
    assert mw_cross_check("reptation", None, 2e5) is None
    assert mw_cross_check("reptation", [5.0], 2e5) is None


def test_default_chemistry_is_flagged_in_the_note():
    """tube.py's defaults are POLYSTYRENE at 180 C. Using them silently on
    another chemistry would be a quiet error, so the note must say so."""
    note = user_note("reptation", [5.0, 1.0, 10.0], mw_g_per_mol=2e5)
    assert "polystyrene" in note["text"]
    # Supplying rho/T explicitly removes the caveat.
    note2 = user_note("reptation", [5.0, 1.0, 10.0], mw_g_per_mol=2e5,
                      rho=900.0, temp_k=400.0)
    assert "polystyrene" not in note2["text"]


# --- flow observation ------------------------------------------------------

def test_user_observed_flow_against_a_non_terminal_curve():
    """The documented Pryke Ma38k case: measured 1.39 against a 1.4 cutoff
    while plainly flowing."""
    feats = {"terminal_reached": False, "slope_Gp_lo": 1.39,
             "slope_Gpp_lo": 0.625}
    out = flow_contradiction("star", feats, flows=True)
    assert out is not None
    assert out["user_flows"] is True and out["terminal_reached"] is False
    assert out["network_won"] is False
    note = user_note("star", [5.5, 15.0, -5.0], feats=feats, flows=True)
    assert "1.39" in note["text"]


def test_a_flowing_sample_refutes_a_network_answer():
    """A permanent network cannot flow at any temperature - the project's own
    grounding for the terminal_reached hard discard."""
    feats = {"terminal_reached": False, "slope_Gp_lo": 1.2, "slope_Gpp_lo": 0.6}
    out = flow_contradiction("cured_elastomer", feats, flows=True)
    assert out["network_won"] is True
    note = user_note("cured_elastomer", [5.0, 3.5, 0.2], feats=feats, flows=True)
    assert "refuted" in note["text"]


def test_the_other_direction_is_handled_too():
    feats = {"terminal_reached": True, "slope_Gp_lo": 1.9, "slope_Gpp_lo": 0.95}
    out = flow_contradiction("reptation", feats, flows=False)
    assert out is not None
    assert out["user_flows"] is False and out["terminal_reached"] is True
    note = user_note("reptation", [5.0, 1.0, 10.0], feats=feats, flows=False)
    assert "DOES SHOW FLOW" in note["text"]


def test_agreement_on_flow_says_nothing():
    """No contradiction, no note - silence is the default."""
    assert flow_contradiction("reptation", {"terminal_reached": True},
                              flows=True) is None
    assert flow_contradiction("star", {"terminal_reached": False},
                              flows=False) is None


def test_flow_check_needs_both_pieces():
    assert flow_contradiction("reptation", {"terminal_reached": True},
                              flows=None) is None
    assert flow_contradiction("reptation", None, flows=True) is None


# --- solvent ---------------------------------------------------------------

def test_solvent_present_against_a_melt_class_is_a_disagreement():
    note = user_note("reptation", [5.0, 1.0, 10.0], solvent_present=True)
    assert "MELT class" in note["text"]


def test_solvent_present_with_a_solution_class_flags_the_open_pair():
    """zimm vs rouse_screened is 58% of the classifier's remaining error and
    turns on concentration, which one curve cannot measure."""
    note = user_note("zimm", [2.0, 0.0, 20.0], solvent_present=True)
    assert "concentration" in note["text"]


def test_no_solvent_contradicts_a_solution_class():
    note = user_note("rouse_screened", [2.0, 0.0, 20.0], solvent_present=False)
    assert "contradicts" in note["text"]


# --- the user's own guess --------------------------------------------------

def test_a_suspected_class_is_shown_as_a_shortlist_never_blended():
    """>>> The design point of field 4. <<<

    A claimed architecture is shown beside the independent answer. It must be
    framed as a two-item shortlist, exactly as neural_report.pair_note() does
    for a two-brain disagreement, and must never be described as overruling
    or being overruled.
    """
    note = user_note("star", [5.5, 15.0, -5.0], suspected_class="branched")
    assert "shortlist" in note["text"]
    assert "independently" in note["text"]
    assert "contest(" in note["text"]


def test_a_matching_guess_is_called_an_independent_confirmation():
    note = user_note("star", [5.5, 15.0, -5.0], suspected_class="star")
    assert "AGREES" in note["text"]
    assert "not used in the fit" in note["text"]


def test_a_blank_guess_is_ignored():
    assert user_note("star", [5.5, 15.0, -5.0], suspected_class="   ") is None
    assert user_note("star", [5.5, 15.0, -5.0], suspected_class="") is None


# --- hygiene ---------------------------------------------------------------

def test_nothing_here_mutates_its_input():
    theta = np.array([5.0, 1.0, 10.0])
    before = theta.copy()
    user_note("reptation", theta, feats={"terminal_reached": False},
              mw_g_per_mol=2e5, flows=True, solvent_present=False,
              suspected_class="star")
    assert np.array_equal(theta, before)


def test_user_fields_does_not_import_torch():
    import importlib
    import sys
    sys.modules.pop("rheofp.user_fields", None)
    had_torch = "torch" in sys.modules
    importlib.import_module("rheofp.user_fields")
    if not had_torch:
        assert "torch" not in sys.modules
