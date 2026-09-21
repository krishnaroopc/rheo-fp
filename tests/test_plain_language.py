"""Tests for the plain-language / regime reporting layer.

The load-bearing test here is
`test_concentration_regime_is_never_reported_from_a_single_curve`. It pins a
DECISION, not an implementation: concentration is not identifiable from one
curve, so no amount of later convenience should be allowed to start printing
one. See rheofp/plain_language.py's module docstring for why.
"""
import numpy as np
import pytest

from rheofp.data.synth import ALL_CLASSES
from rheofp import plain_language as pl


def test_every_generated_class_has_a_plain_name_and_a_regime_entry():
    """The bank-coverage invariant, applied to the reporting layer.

    Mirrors test_every_generated_class_has_a_candidate_in_the_identifier_bank.
    A class that can be generated and emitted but has no translation would
    reach a user as a bare internal label - the exact failure this module
    exists to prevent.
    """
    missing_name = sorted(set(ALL_CLASSES) - set(pl.PLAIN_NAMES))
    missing_regime = sorted(set(ALL_CLASSES) - set(pl.CLASS_REGIME))
    assert missing_name == [], f"no plain name for {missing_name}"
    assert missing_regime == [], f"no regime entry for {missing_regime}"


def test_no_translation_exists_for_a_class_that_cannot_be_generated():
    """The reverse direction, same as the bank invariant's reverse test.

    A stale entry here would advertise a class the pipeline cannot emit.
    """
    extra = sorted(set(pl.PLAIN_NAMES) - set(ALL_CLASSES))
    assert extra == [], f"translation for non-existent class {extra}"


def test_concentration_regime_is_never_reported_from_a_single_curve():
    """>>> THE DECISION THIS MODULE PINS. <<<

    Concentration is not in the forward models - model_zimm and model_rouse
    take (Gscale, tau1, N) and differ only in the spectral exponent. It scales
    amplitude and shifts the time axis, i.e. moves a curve without changing
    its shape, degenerate with Mw, solvent viscosity and temperature.

    So no per-class output may assert a concentration regime as a conclusion.

    A naive substring ban on the word "semidilute" is NOT the right test, and
    writing one first is what surfaced the distinction worth pinning:
    `rouse_screened`'s gloss says it "covers semidilute-unentangled solutions
    AND melts below Me". That names BOTH possibilities, which is exactly the
    honest statement - the failure would be naming only one, because choosing
    between them is a claim about whether solvent is present, and that is not
    in the curve.

    So the rule enforced here is: wherever a concentration word appears, the
    alternative must appear with it, or the text must be explicitly disclaiming
    (the caveat) or prescriptive (the stack hint).
    """
    conc_words = ("semidilute", "semi-dilute", "concentrated")
    for c in ALL_CLASSES:
        d = pl.describe_class(c)
        for field in ("plain_name", "gloss", "regime_note"):
            text = (d[field] or "").lower()
            if not any(word in text for word in conc_words):
                continue
            # A concentration word is present. It is only acceptable if the
            # melt alternative is named alongside it.
            assert "melt" in text, (
                f"{c}.{field} names a concentration regime without naming the "
                f"melt alternative, i.e. it silently assumes solvent is "
                f"present: {text!r}")

    # "dilute" unqualified is only legitimate for zimm, where unscreened
    # hydrodynamics IS dynamically what dilute means.
    for c in ALL_CLASSES:
        if c == "zimm":
            continue
        name = pl.plain_name(c).lower()
        assert not name.startswith("dilute"), (
            f"{c} is named as a dilute system but is not zimm: {name!r}")


def test_zimm_states_the_premise_its_dilute_claim_depends_on():
    """zimm is allowed to say 'dilute' because unscreened hydrodynamics is
    dynamically what dilute MEANS. But it must not leave that as a bare
    concentration claim - c* depends on molecular weight and solvent quality,
    neither of which is in the curve.
    """
    note = pl.regime_note("zimm").lower()
    assert "c*" in note
    assert "molecular weight" in note and "solvent" in note
    assert "not the concentration" in note or "not the concentration" in note


def test_the_caveat_is_attached_to_every_class_that_has_a_regime():
    """A regime line without the caveat is the failure mode: a reader turns
    'screened' into 'semidilute' and walks away with a concentration the
    measurement never contained."""
    for c in ALL_CLASSES:
        d = pl.describe_class(c)
        if d["regime"] is not None:
            assert d["concentration_caveat"] is not None, (
                f"{c} reports a regime with no concentration caveat")


def test_network_classes_get_no_regime_and_no_concentration_stack_hint():
    """A cured elastomer or critical gel is not placed on a dilute/semidilute
    axis at all, so suggesting a concentration series there is noise."""
    for c in ("cured_elastomer", "critical_gel"):
        d = pl.describe_class(c)
        assert d["regime"] is None
        assert d["regime_note"] is None
        assert d["stack_hint"] is None
        assert d["concentration_caveat"] is None


def test_screened_and_entangled_refuse_to_choose_between_solution_and_melt():
    """Both regimes cover solutions AND melts - the mechanism is identical and
    a single curve does not separate them. The note must say so rather than
    silently picking one, because picking one is a claim about whether solvent
    is present, which is not in the data."""
    for regime in (pl.SCREENED, pl.ENTANGLED):
        note = pl._REGIME_NOTES[regime].lower()
        assert "melt" in note and "solution" in note, (
            f"{regime} note must name both possibilities: {note!r}")


def test_plain_name_passes_unknown_labels_through_unchanged():
    """A display helper must never raise or drop information on an unexpected
    label - a missing translation should degrade to the internal name, not
    break the report."""
    assert pl.plain_name("some_future_class") == "some_future_class"
    assert pl.plain_gloss("some_future_class") is None
    assert pl.dynamic_regime("some_future_class") is None
    assert pl.regime_note("some_future_class") is None


def test_rouse_screened_name_does_not_read_as_a_concentration():
    """The specific label that motivated this layer. 'rouse_screened' is an
    internal name for a mode-spacing exponent plus a screening assumption; the
    user-facing phrasing must describe the physics, and must not silently
    become 'semidilute'."""
    name = pl.plain_name("rouse_screened")
    assert name != "rouse_screened"
    assert "unentangled" in name.lower()
    assert "semidilute" not in name.lower()


def test_report_renders_the_plain_name_without_losing_the_internal_label():
    """Scripts, tests and the notes all speak the internal label, so it must
    survive on the IDENTIFIED line; the plain name is added, never
    substituted."""
    from rheofp.report import format_report
    rep = {
        "winner": "rouse_screened", "winner_rms_log": 0.01,
        "winner_fit_verdict": "excellent", "winner_k": 3, "weight": 1.0,
        "alternatives": [], "evidence": [], "discards": [],
        "n_considered": 10, "n_total": 10, "field_all_poor": False,
        "challenge": [], "low_confidence": False, "abstain": False,
        "abstain_reason": None, "stack": None, "what_would_settle_it": [],
    }
    text = format_report(rep)
    assert "IDENTIFIED: rouse_screened" in text
    assert "unentangled" in text.lower()
    assert "REGIME" in text
    assert "not recoverable from one curve" in text.lower()
