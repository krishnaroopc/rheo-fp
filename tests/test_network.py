import numpy as np
import pytest

from rheofp.io.data import load_npz
from rheofp.models.maxwell import maxwell_spectrum
from rheofp.models.network import (
    chasset_thirion_spectrum, critical_gel_spectrum,
    fit_chasset_thirion, fit_critical_gel, tan_delta_spread,
)
from rheofp.fitting.identify import (
    identify, signature_features, NETWORK_CLASSES,
    digitization_scatter, _apply_tie_rule,
)

OMEGA = np.logspace(-2, 3, int((3 - (-2)) * 12) + 1)
W_WIDE = np.logspace(-3, 4, 60)


def _rel(a, b):
    return abs(a - b) / abs(b)


def test_chasset_thirion_reduces_to_springpot_when_plateau_vanishes():
    Gp_ct, Gpp_ct = chasset_thirion_spectrum(OMEGA, 0.0, 500.0, 0.6)
    Gp_cg, Gpp_cg = critical_gel_spectrum(OMEGA, 500.0, 0.6)
    assert np.allclose(Gp_ct, Gp_cg)
    assert np.allclose(Gpp_ct, Gpp_cg)


def test_critical_gel_has_frequency_independent_loss_tangent():
    u = 0.7
    Gp, Gpp = critical_gel_spectrum(OMEGA, 250.0, u)
    tan_d = Gpp / Gp
    # Winter-Chambon: tan(delta) = tan(pi u / 2), flat in omega.
    assert np.allclose(tan_d, np.tan(np.pi * u / 2.0))
    assert tan_delta_spread(OMEGA, Gp, Gpp) < 1e-9


def test_cured_elastomer_is_plateau_dominated_with_small_loss_tangent():
    # Large G_inf, weak springpot: the cured-rubber corner of the family.
    Gp, Gpp = chasset_thirion_spectrum(OMEGA, 1.0e6, 2.0e4, 0.2)
    assert np.all(Gpp / Gp < 0.1)
    # G' stays within a factor of a few of the plateau across 5 decades.
    assert Gp.max() / Gp.min() < 5.0
    # ...and a real plateau makes tan(delta) vary, unlike a gel.
    assert tan_delta_spread(OMEGA, Gp, Gpp) > 0.3


def test_fit_chasset_thirion_recovers_planted_cured_elastomer():
    ref = dict(G_inf=1.0e6, c=2.0e4, m=0.25)
    Gp, Gpp = chasset_thirion_spectrum(OMEGA, ref["G_inf"], ref["c"], ref["m"])
    fit = fit_chasset_thirion(OMEGA, Gp, Gpp, n_restarts=24, seed=1)
    assert _rel(fit["G_inf"], ref["G_inf"]) < 1e-2
    assert _rel(fit["c"], ref["c"]) < 1e-2
    assert _rel(fit["m"], ref["m"]) < 1e-2


def test_fit_chasset_thirion_recovers_planted_weakly_crosslinked_network():
    # Smaller plateau, stronger power law - the near-threshold end of the
    # cured class, where G_inf is only marginally identifiable.
    ref = dict(G_inf=1.0e3, c=5.0e3, m=0.5)
    Gp, Gpp = chasset_thirion_spectrum(OMEGA, ref["G_inf"], ref["c"], ref["m"])
    fit = fit_chasset_thirion(OMEGA, Gp, Gpp, n_restarts=24, seed=2)
    assert _rel(fit["G_inf"], ref["G_inf"]) < 5e-2
    assert _rel(fit["c"], ref["c"]) < 5e-2
    assert _rel(fit["m"], ref["m"]) < 5e-2


def test_fit_critical_gel_recovers_planted_params_at_tixier_exponent():
    # u = 0.69 is Tixier's system I - deliberately NOT the universal 0.5.
    ref = dict(c=300.0, u=0.69)
    Gp, Gpp = critical_gel_spectrum(OMEGA, ref["c"], ref["u"])
    fit = fit_critical_gel(OMEGA, Gp, Gpp, n_restarts=24, seed=3)
    assert _rel(fit["c"], ref["c"]) < 1e-2
    assert _rel(fit["u"], ref["u"]) < 1e-2


def test_fit_critical_gel_recovers_winter_chambon_half_exponent():
    ref = dict(c=1.0e4, u=0.5)
    Gp, Gpp = critical_gel_spectrum(OMEGA, ref["c"], ref["u"])
    fit = fit_critical_gel(OMEGA, Gp, Gpp, n_restarts=24, seed=4)
    assert _rel(fit["c"], ref["c"]) < 1e-2
    assert _rel(fit["u"], ref["u"]) < 1e-2


def test_identify_routes_planted_cured_elastomer_and_abstains_on_one_curve():
    Gp, Gpp = chasset_thirion_spectrum(W_WIDE, 1.0e6, 2.0e4, 0.2)
    out = identify(W_WIDE, Gp, Gpp)
    assert out["best"] == "cured_elastomer"
    # Head 1 abstains from a single curve; head 2 still emits the model.
    assert out["abstain"] is True
    assert "melt" in out["abstain_reason"]


def test_temperature_stack_lifts_the_melt_rubber_abstention():
    Gp, Gpp = chasset_thirion_spectrum(W_WIDE, 1.0e6, 2.0e4, 0.2)
    out = identify(W_WIDE, Gp, Gpp, n_temperatures=4)
    assert out["best"] == "cured_elastomer"
    assert out["abstain"] is False


@pytest.mark.parametrize("u", [0.5, 0.69, 0.75])
def test_identify_routes_planted_critical_gel_across_the_exponent_range(u):
    # 0.5 = Winter-Chambon; 0.69/0.75 = Tixier's end-linked PDMS systems.
    Gp, Gpp = critical_gel_spectrum(W_WIDE, 300.0, u)
    out = identify(W_WIDE, Gp, Gpp)
    assert out["best"] == "critical_gel"
    # A gel has no plateau to confuse with a melt, so it never abstains.
    assert out["abstain"] is False


def test_terminal_relaxation_in_window_discards_both_network_classes():
    # A single Maxwell mode reaches full terminal flow (G' ~ w^2) inside this
    # window; a permanent network cannot flow, so both are ruled out.
    Gp, Gpp = maxwell_spectrum(W_WIDE, [1000.0], [1.0])
    feats, allowed = signature_features(W_WIDE, Gp, Gpp)
    assert feats["terminal_reached"]
    assert not (NETWORK_CLASSES & allowed)


def test_real_melt_is_not_misclassified_as_a_network():
    """Melt counterexample: Likhtman-McLeish (2002) PS 6, truncated windows.

    Hiding the terminal region is the classic way to make an entangled melt
    impersonate a rubber. The reptation model still wins on AICc at every
    truncation, so the network classes never steal real melt data.
    """
    d = load_npz("data/likhtman_mcleish2002_fig10.npz")["PS 6"]
    w, Gp, Gpp = d["omega"], d["Gp"], d["Gpp"]
    for wmin in (1e-5, 1e-2, 1e-1, 1e0):
        m = w >= wmin
        out = identify(w[m], Gp[m], Gpp[m])
        assert out["best"] not in NETWORK_CLASSES, f"misclassified at wmin={wmin}"


# Darby et al. (2022) Table 1 low-frequency (0.01 rad/s) G', Pa. The digitized
# Fig. 1a curves stop at 0.1 rad/s, so these are an out-of-window anchor.
_DARBY_TABLE1_PA = {"SY184_10-1": 620e3, "Solaris_1-1": 120e3, "EF0030_1-1": 27e3}


@pytest.mark.parametrize("sample", list(_DARBY_TABLE1_PA))
def test_darby2022_real_silicone_fits_cured_elastomer_and_recovers_ginf(sample):
    """Real cured-PDMS SAOS (Darby 2022 Fig. 1a, digitized).

    fit_chasset_thirion should describe the measured curve to well under a
    decade and land G_inf near the paper's tabulated low-frequency modulus.
    The tolerance is deliberately loose (35%): the anchor is a decade below
    the data, and the softest sample (EF, ~55% sol fraction) is noisy - see
    the network.py / litreview caveats.
    """
    d = load_npz("data/darby2022.npz")[sample]
    w, Gp, Gpp = d["omega"], d["Gp"], d["Gpp"]

    fit = fit_chasset_thirion(w, Gp, Gpp, n_restarts=32, seed=1)
    Gp_f, Gpp_f = chasset_thirion_spectrum(w, fit["G_inf"], fit["c"], fit["m"])
    assert np.abs(np.log10(Gp_f) - np.log10(Gp)).mean() < 0.03
    assert _rel(fit["G_inf"], _DARBY_TABLE1_PA[sample]) < 0.35
    # m in the dangling-chain regime (Curro-Pincus ~0.1-0.3, a little higher
    # here for the high-free-chain commercial kits).
    assert 0.1 < fit["m"] < 0.5

    out = identify(w, Gp, Gpp)
    assert out["best"] == "cured_elastomer"
    # single curve, no temperature stack -> head 1 abstains
    assert out["abstain"] is True


def test_tixier2004_real_gel_fits_critical_gel_in_measured_exponent_range():
    """Real near-gel-point PDMS SAOS (Tixier 2004 Fig. 2/4, digitized).

    fit_critical_gel should describe the parallel power laws to well under a
    decade and land u in Tixier's measured range - crucially NOT the
    universal 1/2 (their Table II gives u = 0.69-0.75; digitized curve ~0.76).
    identify() must route it to the critical_gel class.
    """
    d = load_npz("data/tixier2004.npz")["Tixier2004_gel"]
    w, Gp, Gpp = d["omega"], d["Gp"], d["Gpp"]

    fit = fit_critical_gel(w, Gp, Gpp, n_restarts=32, seed=1)
    Gp_f, Gpp_f = critical_gel_spectrum(w, fit["c"], fit["u"])
    resid = max(np.abs(np.log10(Gp_f) - np.log10(Gp)).mean(),
                np.abs(np.log10(Gpp_f) - np.log10(Gpp)).mean())
    assert resid < 0.03
    assert 0.6 < fit["u"] < 0.85          # Tixier range, not 0.5
    assert tan_delta_spread(w, Gp, Gpp) < 0.15   # loss tangent ~ flat

    out = identify(w, Gp, Gpp)
    assert out["best"] == "critical_gel"
    assert out["abstain"] is False        # a gel has no melt ambiguity


def test_chasset_thirion_fit_drives_plateau_to_zero_on_gel_data():
    # Fitting the 3-param model to true gel data must find G_inf negligible
    # against the springpot term - this is what makes the 2-param gel model
    # win on AICc rather than on residual.
    Gp, Gpp = critical_gel_spectrum(OMEGA, 300.0, 0.69)
    fit = fit_chasset_thirion(OMEGA, Gp, Gpp, n_restarts=24, seed=5)
    springpot_at_wmin = fit["c"] * OMEGA.min() ** fit["m"]
    assert fit["G_inf"] < 1e-3 * springpot_at_wmin
    assert _rel(fit["m"], 0.69) < 1e-2


# ---------------------------------------------------------------------------
# The noise-aware tie rule (2026-09-17), pre-registered in
# docs/tie_rule_preregistration.md. These pin the rule's SHAPE - that it fires
# only inside measured scatter, only at the top of the ranking, and only
# toward fewer parameters. They deliberately do not pin which class wins on
# any real curve; that is measured, not asserted.
# ---------------------------------------------------------------------------

def test_digitization_scatter_is_at_the_floor_for_an_exactly_smooth_curve():
    """A noiseless power law has no reading error, so the rule must be inert.

    This is the property that keeps the rule from firing on synthetic data
    generated without noise: scatter ~ 0 means no two candidates are ever
    within scatter of each other.
    """
    lw = np.log10(W_WIDE)
    Gp = 10.0 ** (5.0 - 0.5 * lw)
    Gpp = 10.0 ** (4.5 - 0.3 * lw)
    assert digitization_scatter(W_WIDE, Gp, Gpp) <= 1e-9


def test_digitization_scatter_recovers_planted_noise():
    """Scatter tracks noise actually added, within a factor of ~2.

    Not an equality: a local quadratic absorbs some of the noise it is fitted
    through, so the estimate is biased low by a known, bounded amount.
    """
    rng = np.random.default_rng(0)
    lw = np.log10(W_WIDE)
    smooth = 10.0 ** (5.0 - 0.5 * lw)
    for planted in (0.005, 0.02):
        noisy = smooth * 10.0 ** rng.normal(0.0, planted, size=smooth.shape)
        got = digitization_scatter(W_WIDE, noisy, noisy)
        assert 0.4 * planted < got < 1.6 * planted, (planted, got)


def test_tie_rule_prefers_the_simpler_model_only_inside_the_scatter():
    """The window is the whole rule: the same pair ties or does not by it."""
    pair = [{"name": "branched", "rms_log": 0.0200, "k": 5, "aicc": 0.0},
            {"name": "reptation", "rms_log": 0.0210, "k": 3, "aicc": 10.0}]

    inside = [dict(r) for r in pair]
    tie = _apply_tie_rule(inside, scatter=0.005)   # gap 0.001 < 0.005
    assert tie is not None
    assert inside[0]["name"] == "reptation"
    assert tie["displaced"] == "branched"

    outside = [dict(r) for r in pair]
    assert _apply_tie_rule(outside, scatter=0.0005) is None   # gap > scatter
    assert outside[0]["name"] == "branched"


def test_tie_rule_never_promotes_a_model_outside_the_window():
    """A distant simpler model must NOT be dragged up by a nearby tie."""
    results = [{"name": "branched", "rms_log": 0.020, "k": 5, "aicc": 0.0},
               {"name": "wormlike_micelle", "rms_log": 0.021, "k": 4,
                "aicc": 5.0},
               {"name": "zimm", "rms_log": 0.400, "k": 3, "aicc": 900.0}]
    tie = _apply_tie_rule(results, scatter=0.005)
    assert results[0]["name"] == "wormlike_micelle"   # k=4, inside
    assert "zimm" not in tie["tied_with"]             # k=3 but far outside


def test_tie_rule_is_silent_when_the_leader_is_already_the_simplest():
    results = [{"name": "reptation", "rms_log": 0.020, "k": 3, "aicc": 0.0},
               {"name": "branched", "rms_log": 0.021, "k": 5, "aicc": 8.0}]
    assert _apply_tie_rule(results, scatter=0.005) is None
    assert results[0]["name"] == "reptation"


def test_tie_rule_keeps_aicc_order_between_models_of_equal_k():
    """Parsimony cannot separate equal-k models, so AICc must still decide.

    This matters for the known zimm<->rouse_screened degenerate pair: the rule
    must not reshuffle it on noise.
    """
    results = [{"name": "zimm", "rms_log": 0.0200, "k": 3, "aicc": 0.0},
               {"name": "rouse_screened", "rms_log": 0.0205, "k": 3,
                "aicc": 0.4}]
    assert _apply_tie_rule(results, scatter=0.005) is None
    assert results[0]["name"] == "zimm"


def test_the_tie_rule_is_not_applied_by_identify():
    """>>> The tie rule was MEASURED AND REJECTED on 2026-09-17. <<<

    P1/P2/P3 passed, but P4 - a fixed rejection criterion - failed:
    cured_elastomer 10->8, branched 8->6, overall 0.890->0.850, firing on 7.0%
    of curves against a predicted <5%. Outcome in
    docs/tie_rule_outcome_2026-09-17.txt.

    The cause is that `digitization_scatter` reads ~0.0136 on GENERATED curves
    (synth.NOISE_DECADES = 0.02) against 0.0015-0.0085 on real digitized ones,
    so the tie window is ~5x too wide on the training distribution and starts
    absorbing real differences.

    This test fails the moment the rule is re-enabled, which is the point: it
    must not come back without the check being re-run at n=30.
    """
    rng = np.random.default_rng(0)
    lw = np.log10(W_WIDE)
    # A noisy curve - exactly the case where the rule WOULD have fired.
    smooth_p = 10.0 ** (5.0 - 0.2 * lw)
    noisy_p = smooth_p * 10.0 ** rng.normal(0.0, 0.02, size=smooth_p.shape)
    assert digitization_scatter(W_WIDE, noisy_p, noisy_p) > 0.005

    Gp, Gpp = maxwell_spectrum(W_WIDE, [1000.0], [1.0])
    out = identify(W_WIDE, Gp, Gpp)
    # The key stays in the contract so report.py need not special-case it...
    assert "tie_break" in out
    # ...but it is always None, because the rule is not applied.
    assert out["tie_break"] is None


def test_a_short_chain_linear_melt_keeps_reptation_on_the_ballot():
    """Pins the `wide_plateau` discard REMOVAL (2026-09-16).

    `if not wide_plateau: allowed.discard("reptation")` used to delete the
    linear-melt class whenever G' held flat for under a decade. On Katzarova
    2018's three monodisperse linear polystyrenes that width reads
    2.29 / 0.84 / 0.16 decades at Z = 29.5 / 15.5 / 7.9 - a monotone function
    of entanglement count, so the threshold was a cutoff on molecular weight
    wearing a shape test's clothes, and it removed the TRUE class from the
    ballot for the two shorter chains.

    Asserts only that the candidate is reachable, not that it wins - what it
    actually wins is measured elsewhere and is currently 1/3.
    """
    d = load_npz("data/katzarova2018.npz")
    for sample in ("PS392", "PS206", "PS105"):
        rec = d[sample]
        _, allowed = signature_features(rec["omega"], rec["Gp"], rec["Gpp"])
        assert "reptation" in allowed, f"{sample} lost the linear-melt class"


def test_the_surviving_zimm_rouse_discard_rests_on_a_positive_observation():
    """Pins `confident_entangled`, the OTHER hard discard (2026-09-17).

    CLAUDE.md said for a while that "exactly ONE hard discard remains". There
    are two: `terminal_reached` striking the network classes, and this one
    striking the unentangled pair. This second rule was pinned by NO test at
    all - the same blind spot that let the `wide_plateau` discard survive
    unexamined until it was found to be deleting the true class.

    It is sound by the project's own standard, and the test says why: it fires
    only on a POSITIVE observation (a plateau wider than a decade, with the
    spectrum continuing above it, AND terminal flow below it), never on an
    absence. A real entangled melt shows all three; an unentangled chain has
    no plateau to show, so ruling zimm/rouse out is a conclusion from what was
    SEEN, not from what was missing.
    """
    d = load_npz("data/katzarova2018.npz")

    # PS392 - the longest chain, plateau 2.29 decades: the rule fires.
    rec = d["PS392"]
    feats, allowed = signature_features(rec["omega"], rec["Gp"], rec["Gpp"])
    assert feats["confident_entangled"]
    assert feats["plateau_width"] >= 1.0
    assert feats["spectrum_above"] and feats["terminal_reached"]
    assert not {"zimm", "rouse_screened"} & allowed

    # PS105 - same chemistry, plateau only 0.16 decades: it must NOT fire.
    # A narrow plateau is weak evidence of few entanglements, never a positive
    # observation of many, so the unentangled classes stay on the ballot.
    rec = d["PS105"]
    feats, allowed = signature_features(rec["omega"], rec["Gp"], rec["Gpp"])
    assert not feats["confident_entangled"]
    assert {"zimm", "rouse_screened"} <= allowed


def test_every_feature_a_discard_rule_names_is_actually_exported():
    """A rule the report cannot read is a silent deletion.

    `confident_entangled` is built from `plateau_width` and `spectrum_above`,
    which were LOCALS in signature_features() and never reached `feats`. The
    report's rule table therefore could not name that discard and fell through
    to "a pre-filter rule excluded them" - in the layer whose whole purpose is
    turning a silent deletion into an instruction. This asserts the contract
    directly, so a future rule keyed off a private local fails here.
    """
    from rheofp.report import _DISCARD_RULES

    rec = load_npz("data/katzarova2018.npz")["PS392"]
    feats, _ = signature_features(rec["omega"], rec["Gp"], rec["Gpp"])
    for flag, (_, observed, _why) in _DISCARD_RULES.items():
        assert flag in feats, f"rule {flag!r} keys off a feature not exported"
        # the wording is a format string over feats - it must render
        observed.format(**feats)
