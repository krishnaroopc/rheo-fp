"""The explanation layer.

What matters is that the report tells the truth about the evidence: that it
ranks by delta AICc rather than the collapsed Akaike weight, that it exposes a
runner-up which fits BETTER than the winner, that it says so plainly when
nothing in the bank fits at all, and that contesting a class the pre-filter
struck off still fits it and reports its numbers.
"""
import numpy as np
import pytest

from rheofp.fitting.identify import identify, identify_stack, ALL_MODELS
from rheofp.io.data import load_npz
from rheofp.report import (
    explain, format_report, contest, format_contest,
    delta_verdict, fit_verdict, DEGENERATE_PAIRS,
)


def _blend(n=60):
    """A two-plateau blend: out of scope for every model in the bank.

    This is the probe both out-of-distribution detectors in next-actions 1j
    failed to catch, which is why it is the one used here.
    """
    w = np.logspace(-3, 3, n)

    def mx(g, t):
        x = (w * t) ** 2
        return g * x / (1 + x), g * (w * t) / (1 + x)

    a, b = mx(1e5, 1e-2), mx(1e3, 1e2)
    return w, a[0] + b[0], a[1] + b[1]


def test_report_exposes_a_runner_up_that_fits_better_than_the_winner():
    """The standing worked example: the Tixier critical gel.

    critical_gel wins, but cured_elastomer sits at delta ~2.4 and fits
    MARGINALLY BETTER (0.0107 vs 0.0108 decades), losing only on parsimony.
    A user shown the winner alone would believe the question settled; the
    report has to say it is not.

    (Note the weight here is ~0.77, not the 1.000 the notes describe as
    typical - which is itself the point. The weight is not a reliable readout
    either way, so the report leans on delta AICc and absolute fit instead.)
    """
    s = list(load_npz("data/tixier2004.npz").values())[0]
    out = identify(s["omega"], s["Gp"], s["Gpp"])
    rep = explain(out)

    assert rep["winner"] == "critical_gel"
    runner = rep["alternatives"][0]
    assert runner["name"] == "cured_elastomer"
    assert runner["delta_aicc"] < 5                # a live alternative
    assert runner["fits_better"]                   # ...and it fits better
    assert runner["degeneracy_note"]               # nested pair, flagged

    text = format_report(rep)
    assert "fits better" in text
    assert "NESTED" in text


def test_contest_says_nothing_contradicts_a_better_fitting_alternative():
    s = list(load_npz("data/tixier2004.npz").values())[0]
    c = contest(s["omega"], s["Gp"], s["Gpp"], "cured_elastomer")
    assert c["fits_better_than_winner"]
    assert "nothing in your measurement contradicts" in format_contest(c)


def test_report_reads_as_decisive_when_the_evidence_is_decisive():
    """Pivokonsky LDPE: branched at delta 0, nothing else within ~50."""
    s = load_npz("data/pivo2006.npz")["E"]
    rep = explain(identify(s["omega"], s["Gp"], s["Gpp"]))
    assert rep["winner"] == "branched"
    assert rep["alternatives"][0]["delta_aicc"] > 10
    assert not rep["field_all_poor"]
    assert all(not a["fits_better"] for a in rep["alternatives"])


def test_out_of_scope_material_is_flagged_as_a_least_bad_winner():
    """A high Akaike weight hides the case where NOTHING fits.

    Both OOD detectors tried in next-actions 1j failed on this exact probe.
    The report does not need to identify the blend - it needs to refuse to
    pretend the winner is trustworthy.
    """
    w, Gp, Gpp = _blend()
    out = identify(w, Gp, Gpp)
    rep = explain(out)

    assert out["best_weight"] > 0.9        # confident...
    assert rep["field_all_poor"]           # ...but nothing fits
    assert rep["winner_fit_verdict"] == "does not fit"
    assert "NOTHING IN THE BANK FITS" in format_report(rep)


def test_contest_fits_a_class_the_prefilter_struck_off():
    """A discard is a claim, and it owes the user its numbers on request."""
    s = load_npz("data/pivo2006.npz")["E"]
    out = identify(s["omega"], s["Gp"], s["Gpp"])
    assert "reptation" not in out["allowed"]      # struck off, never fitted

    c = contest(s["omega"], s["Gp"], s["Gpp"], "reptation", result=out)
    assert not c["was_on_ballot"]
    assert np.isfinite(c["delta_aicc"]) and c["delta_aicc"] > 0
    assert np.isfinite(c["rms_log"])
    assert c["contradicted_by"]                   # and it says which rule
    assert "struck off by the pre-filter" in format_contest(c)


def test_discards_are_reported_with_a_way_to_lift_them():
    s = load_npz("data/pivo2006.npz")["E"]
    rep = explain(identify(s["omega"], s["Gp"], s["Gpp"]))
    assert rep["discards"]
    d = rep["discards"][0]
    assert "reptation" in d["classes"]
    assert d["because"] and d["reasoning"]
    # Never a bare "a pre-filter rule excluded them" - that is the fallback
    # for an unrecognised rule and means this table has drifted.
    assert "a pre-filter rule excluded them" not in d["because"]


def test_vitrimer_absence_is_reported_as_a_fitted_result_not_a_deletion():
    """After the 2026-09-07 has_shoulder fix the sticker classes are always
    fitted. The report must not tell a user they were excluded."""
    s = load_npz("data/pivo2006.npz")["E"]
    out = identify(s["omega"], s["Gp"], s["Gpp"])
    rep = explain(out)
    assert "sticky_rouse" in out["allowed"]
    assert "sticky_reptation" in out["allowed"]
    for d in rep["discards"]:
        assert "sticky_rouse" not in d["classes"]
        assert "sticky_reptation" not in d["classes"]
    assert "not a pre-filter deletion" in format_report(rep)


def test_stack_verdict_reaches_the_report():
    from rheofp.data.synth import make_example
    rng = np.random.default_rng(4)
    ex = make_example(rng, "sticky_reptation", n_curves=4)
    stack = [dict(omega=w, Gp=gp, Gpp=gpp, T_K=T)
             for w, gp, gpp, T in ex["curves"]]
    rep = explain(identify_stack(stack, n_restarts=6))
    assert rep["stack"]
    assert rep["stack"]["verdict"] in ("melt", "network", "ambiguous")
    assert "TEMPERATURE STACK" in format_report(rep)


def test_abstention_is_surfaced_with_what_would_settle_it():
    """A cured elastomer from a single curve abstains; the report must both
    say so and name the measurement that resolves it."""
    from rheofp.data.synth import make_example
    rng = np.random.default_rng(5)
    for _ in range(8):
        ex = make_example(rng, "cured_elastomer", n_curves=1)
        w, Gp, Gpp, _ = ex["curves"][0]
        out = identify(w, Gp, Gpp, n_restarts=6)
        if out["abstain"]:
            rep = explain(out)
            text = format_report(rep)
            assert "ABSTAINING" in text
            assert rep["what_would_settle_it"]
            assert "temperature" in " ".join(rep["what_would_settle_it"]).lower()
            return
    pytest.skip("no abstention drawn in this sample")


def test_contest_rejects_an_unknown_class():
    w, Gp, Gpp = _blend(20)
    with pytest.raises(KeyError):
        contest(w, Gp, Gpp, "not_a_real_class")


def test_verdict_bands_are_monotonic_and_cover_the_range():
    ds = [0.0, 1.9, 2.1, 5.0, 8.0, 50.0]
    assert len({delta_verdict(d) for d in ds}) >= 4
    assert delta_verdict(0.0) != delta_verdict(50.0)
    assert fit_verdict(0.005) == "excellent"
    assert fit_verdict(10.0) == "does not fit"


def test_degenerate_pairs_match_the_ml_evaluator():
    """This module duplicates AMBIGUOUS_PAIRS to avoid a torch dependency;
    the two must not drift apart."""
    from rheofp.ml.evaluate import AMBIGUOUS_PAIRS
    assert {frozenset(p) for p in AMBIGUOUS_PAIRS} == set(DEGENERATE_PAIRS)


def test_every_bank_class_is_contestable():
    """contest() must work for anything identify() could be asked about."""
    w, Gp, Gpp = _blend(30)
    out = identify(w, Gp, Gpp, n_restarts=4)
    for name in ALL_MODELS:
        c = contest(w, Gp, Gpp, name, result=out, n_restarts=4)
        assert np.isfinite(c["rms_log"])
        assert isinstance(format_contest(c), str)


# --- the always-on challenge -------------------------------------------------

def test_challenge_is_present_even_for_a_confident_correct_answer():
    """The whole point of making it unconditional.

    Pivokonsky E is real data, correctly classified, decisive on delta AICc.
    It still gets a full "don't think it's branched?" section - because a
    caveat that appeared only when something looked wrong would teach the
    reader that a quiet report means a sure answer, and that inference is
    false: most of this classifier's errors are GOOD fits of the WRONG class.
    """
    s = load_npz("data/pivo2006.npz")["E"]
    rep = explain(identify(s["omega"], s["Gp"], s["Gpp"]))
    assert rep["winner"] == "branched"
    assert not rep["field_all_poor"]          # nothing is wrong here...
    assert rep["challenge"]                   # ...and it is challenged anyway

    text = format_report(rep)
    assert "DON'T THINK IT'S BRANCHED? THIS MAY BE WHY" in text
    # and it must say why it is always printed, so the reader does not read
    # its presence as a warning sign
    assert "printed for every result" in text


def test_challenge_states_absolute_fit_in_both_directions():
    """A good fit is reported as good - with the caveat that a good fit only
    shows the model CAN produce the data, not that nothing else could."""
    s = load_npz("data/pivo2006.npz")["E"]
    kinds = {c["kind"] for c in explain(
        identify(s["omega"], s["Gp"], s["Gpp"]))["challenge"]}
    assert "fit" in kinds and "nothing_fits" not in kinds

    w, Gp, Gpp = _blend()
    kinds = {c["kind"] for c in explain(identify(w, Gp, Gpp))["challenge"]}
    assert "nothing_fits" in kinds and "fit" not in kinds


def test_challenge_names_a_live_alternative_with_its_numbers():
    s = list(load_npz("data/tixier2004.npz").values())[0]
    rep = explain(identify(s["omega"], s["Gp"], s["Gpp"]))
    alts = [c for c in rep["challenge"] if c["kind"] == "alternative"]
    assert alts, "a delta-2.4 runner-up must be named"
    assert alts[0]["name"] == "cured_elastomer"
    assert "BETTER than the winner" in alts[0]["text"]


def test_challenge_does_not_name_hopeless_alternatives():
    """Naming every class would be noise. Only alternatives within delta 10 -
    the band where the data genuinely does not separate them - are raised."""
    s = load_npz("data/pivo2006.npz")["E"]
    rep = explain(identify(s["omega"], s["Gp"], s["Gpp"]))
    assert rep["alternatives"][0]["delta_aicc"] > 10      # nothing is close
    assert not [c for c in rep["challenge"] if c["kind"] == "alternative"]


def test_challenge_always_states_the_out_of_taxonomy_limit():
    """No result can escape the fact that only nine classes exist, so this
    item is unconditional - including on the classifier's best day."""
    for path, sample in (("data/pivo2006.npz", "E"),
                         ("data/darby2022.npz", None),
                         ("data/tixier2004.npz", None)):
        d = load_npz(path)
        s = d[sample] if sample else list(d.values())[0]
        rep = explain(identify(s["omega"], s["Gp"], s["Gpp"], n_restarts=6))
        kinds = [c["kind"] for c in rep["challenge"]]
        assert "out_of_taxonomy" in kinds, path


# --- branched-vs-vitrimer-power-law contradiction (2026-09-07) --------------

def test_real_vitrimer_called_branched_trips_the_contradiction():
    """The concrete case this check exists for: Ricarte (2023) PB-v-4 at
    120 C is a real dioxaborolane vitrimer that identify() calls `branched`
    at a genuinely good fit (see scripts/diagnose_sticky_models.py for why -
    a forward-model limit, not a ranking bug). User decision 2026-09-07: keep
    the sticky models as they are and make the ambiguity explicit instead of
    replacing them."""
    from rheofp.report import branched_vitrimer_contradiction
    v = load_npz("data/ricarte2023.npz")["Ricarte2023_PBv4_120C"]
    out = identify(v["omega"], v["Gp"], v["Gpp"])
    assert out["best"] == "branched"

    c = branched_vitrimer_contradiction("branched", v["omega"], v["Gp"], v["Gpp"])
    assert c is not None
    assert c["slope"] < 0
    assert c["gp_span"] < 0.3

    rep = explain(out, w=v["omega"], Gp=v["Gp"], Gpp=v["Gpp"])
    kinds = [ch["kind"] for ch in rep["challenge"]]
    assert "vitrimer_powerlaw" in kinds
    text = format_report(rep)
    assert "POWER-LAW regime" in text
    assert "sticky_rouse" in text


def test_real_branched_melt_does_not_trip_the_contradiction():
    """Must not false-positive on the classifier's actual working case -
    Pivokonsky (2006) real LDPE, correctly identified as branched."""
    from rheofp.report import branched_vitrimer_contradiction
    for name, s in load_npz("data/pivo2006.npz").items():
        out = identify(s["omega"], s["Gp"], s["Gpp"])
        assert out["best"] == "branched"
        c = branched_vitrimer_contradiction(
            "branched", s["omega"], s["Gp"], s["Gpp"])
        assert c is None, f"{name}: false positive"

        rep = explain(out, w=s["omega"], Gp=s["Gp"], Gpp=s["Gpp"])
        kinds = [ch["kind"] for ch in rep["challenge"]]
        assert "vitrimer_powerlaw" not in kinds


def test_contradiction_only_fires_for_a_branched_winner():
    """The check is specific to `branched` - it says nothing about a
    sticker-class or any other winner, by construction."""
    from rheofp.report import branched_vitrimer_contradiction
    v = load_npz("data/ricarte2023.npz")["Ricarte2023_PBv4_120C"]
    c = branched_vitrimer_contradiction(
        "sticky_rouse", v["omega"], v["Gp"], v["Gpp"])
    assert c is None


def test_contradiction_is_skipped_without_the_raw_curve():
    """explain() must not crash or silently misbehave when the caller does
    not have the raw curve to pass - it only omits this one check."""
    s = load_npz("data/pivo2006.npz")["E"]
    out = identify(s["omega"], s["Gp"], s["Gpp"])
    rep = explain(out)                      # no w/Gp/Gpp passed
    kinds = [ch["kind"] for ch in rep["challenge"]]
    assert "vitrimer_powerlaw" not in kinds
    assert rep["winner"] == "branched"      # rest of the report still works


def test_contradiction_has_zero_false_positives_on_a_mixed_population():
    """Measured guard for the threshold choice: among curves the classifier
    genuinely calls `branched` from a mixed synthetic population, none should
    trip this check - it is calibrated to real vitrimer data specifically,
    not to ordinary branched variability."""
    from rheofp.data.synth import make_example
    from rheofp.report import branched_vitrimer_contradiction
    rng = np.random.default_rng(9)
    checked = flagged = 0
    for cls in ("branched", "reptation", "zimm", "rouse_screened"):
        for _ in range(15):
            ex = make_example(rng, cls, n_curves=1)
            w, gp, gpp, _ = ex["curves"][0]
            out = identify(w, gp, gpp, n_restarts=6)
            if out["best"] == "branched":
                checked += 1
                if branched_vitrimer_contradiction("branched", w, gp, gpp):
                    flagged += 1
    assert checked > 10, "test did not exercise enough branched winners"
    assert flagged == 0
