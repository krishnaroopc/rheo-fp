"""Milner-McLeish (1997) star-melt model: forward physics + inverse recovery.

The forward tests pin the model against the paper's own analytic statements
and published figures rather than against remembered numbers - eq 24 reducing
to eq 8, the Figure 2 potential ratio, the quoted log(tau(1)/tau_0) = 13.8,
and the eq-22 handoff location. Several of these caught real transcription
errors while the module was being written, so they are regression tests in the
strict sense, not decoration.

Reference: Macromolecules 1997, 30, 2159 (originals/milner_mcleish1997_star.pdf),
with Ball & McLeish 1989 (ball_mcleish1989.pdf) and Pearson & Helfand 1984
(pearson_helfand1984.pdf) as the two precursors it builds on.
"""
import time

import numpy as np
import pytest

import rheofp.models.star as star
from rheofp.models.star import (
    ALPHA_CR, STAR_MODELS, dueff_ds, fit_star, model_star, star_spectrum,
    tau_of_s, ueff, _tau_activated, _tau_early,
)

# The paper's Figure 1/5 system: 12-arm 1,4-polybutadiene, arm Mw 30 280,
# Me = 1815 -> Z = 16.68, with the literature values quoted in its section IV.
Z_FIG1 = 30280.0 / 1815.0
G_N_FIG1 = 1.25e6
TAU_E_FIG1 = 7.8e-6

W_WIDE = np.logspace(-6, 6, 400)


# --- forward physics: the potential (eq 24) ---------------------------------

def test_ueff_reduces_to_ball_mcleish_eq8_at_alpha_one():
    # eq 24 with alpha = 1 must collapse onto the older eq 8, 15N(s^2-2s^3/3)/8Ne.
    s = np.linspace(0.0, 1.0, 201)
    Z = 17.0
    assert np.allclose(ueff(s, Z, alpha=1.0),
                       15.0 * Z * (s**2 - 2.0 * s**3 / 3.0) / 8.0)


def test_ueff_at_alpha_one_is_one_third_of_the_pearson_helfand_barrier():
    # Paper, under eq 8: "Ueff(1) is reduced by a factor of 3".
    Z = 17.0
    assert ueff(1.0, Z, alpha=1.0) == pytest.approx(15.0 * Z / 8.0 / 3.0)


def test_ueff_matches_the_published_figure_2_curve():
    # Figure 2 plots Pearson-Helfand, Ball-McLeish and "this work". Read off
    # its s = 1 endpoints, this work sits at ~0.26 of the PH barrier.
    Z = 17.0
    ratio = ueff(1.0, Z, ALPHA_CR) / (15.0 * Z / 8.0)
    assert ratio == pytest.approx(0.26, abs=0.02)


def test_pearson_helfand_barrier_reproduces_the_papers_quoted_13_8_decades():
    # Paper, section II: for the Figure 1 system the un-diluted theory gives
    # log(tau(1)/tau_0) = 13.8 - the headline failure dynamic dilution fixes.
    assert (15.0 * 17.0 / 8.0) / np.log(10) == pytest.approx(13.8, abs=0.1)


def test_ueff_derivative_is_analytic_and_correct():
    s = np.linspace(0.05, 0.95, 50)
    h = 1e-6
    for alpha in (1.0, ALPHA_CR):
        numeric = (ueff(s + h, 17.0, alpha) - ueff(s - h, 17.0, alpha)) / (2 * h)
        assert np.allclose(dueff_ds(s, 17.0, alpha), numeric, rtol=1e-6)


def test_ueff_is_a_monotonically_increasing_barrier():
    # A retraction potential that turned over would let the arm end fall
    # inward for free; it also silently signals a transcription slip in eq 24.
    s = np.linspace(0.0, 1.0, 2000)
    for alpha in (1.0, ALPHA_CR):
        assert np.all(np.diff(ueff(s, 17.0, alpha)) >= -1e-12)


def test_stronger_dilution_softens_the_barrier():
    # The Colby-Rubinstein exponent 4/3 dilutes faster than the binary-contact
    # alpha = 1, so it must give the LOWER barrier at every interior s.
    s = np.linspace(0.05, 1.0, 50)
    assert np.all(ueff(s, 17.0, ALPHA_CR) < ueff(s, 17.0, 1.0))


# --- forward physics: the relaxation-time crossover (eqs 13, 22, 29) --------

def test_eq22_hands_off_from_the_early_to_the_activated_branch():
    # The paper places the crossover at 1 - s of order (Ne/N)^(1/2); for
    # Z = 17 that is s ~ 0.2. If the activated branch never overtakes the
    # early one, the terminal time stays Rouse-like and the whole alpha
    # dependence collapses - which is exactly the bug this guards.
    s = np.linspace(1e-6, 1.0 - 1e-9, 20000)
    early = _tau_early(s, Z_FIG1, TAU_E_FIG1)
    activated = _tau_activated(s, Z_FIG1, TAU_E_FIG1, ALPHA_CR)
    overtakes = early > activated
    assert overtakes.any(), "activated branch never takes over"
    assert 0.10 < s[np.argmax(overtakes)] < 0.35


def test_activated_prefactor_scales_as_Z_to_the_three_halves():
    # Paper, under eq 19: "tau(s) ~ tau_e (N/Ne)^(3/2) exp[Ueff(s)]", and in
    # the same sentence, that the prefactor "depends more weakly on N/Ne than
    # the Rouse time tau_R" - and tau_R/tau_e = Z^2. Measure the prefactor
    # alone by dividing out exp[Ueff] and the eq-29 denominator.
    def bare_prefactor(Z):
        s = 0.5
        denom = np.sqrt(s**2 * (1 - s) ** (2 * ALPHA_CR)
                        + _k_constant(Z) ** -2.0)
        return (_tau_activated(s, Z, 1.0, ALPHA_CR)
                * denom / np.exp(ueff(s, Z, ALPHA_CR)))

    exponent = np.log(bare_prefactor(40.0) / bare_prefactor(10.0)) / np.log(4.0)
    assert exponent == pytest.approx(1.5, abs=0.02)
    assert exponent < 2.0, "prefactor must depend on Z more weakly than tau_R"


def _k_constant(Z, alpha=ALPHA_CR):
    """The eq-29 barrier-top constant K, duplicated here so the prefactor test
    does not depend on the module's private spelling of it."""
    from scipy.special import gamma
    return ((15.0 * Z / 4.0) ** (alpha / (alpha + 1.0))
            * (1.0 + alpha) ** (-(2.0 * alpha + 1.0) / (1.0 + alpha))
            * gamma(1.0 / (1.0 + alpha)))


def test_tau_is_linear_in_tau_e():
    s = np.linspace(0.01, 0.99, 50)
    assert np.allclose(tau_of_s(s, 17.0, 1e-4), 10.0 * tau_of_s(s, 17.0, 1e-5),
                       rtol=1e-12)


# --- forward physics: the modulus (eqs 25, 26) ------------------------------

def test_terminal_scaling_is_maxwell_like():
    w = np.logspace(-8, -5, 60)
    Gp, Gpp = star_spectrum(w, G_N_FIG1, Z_FIG1, TAU_E_FIG1)
    assert np.polyfit(np.log10(w), np.log10(Gp), 1)[0] == pytest.approx(2.0, abs=1e-3)
    assert np.polyfit(np.log10(w), np.log10(Gpp), 1)[0] == pytest.approx(1.0, abs=1e-3)


def test_plateau_recovers_G_N():
    # eq 25's weight (alpha+1)(1-s)^alpha integrates to 1 over [0,1], so the
    # mode weights sum to G_N and G' must approach it on a wide window.
    # This is a property of the RETRACTION integral (eq 26) alone, so the
    # arm-Rouse modes are switched off: they sit above the G'' minimum, are
    # not part of MM's result, and deliberately carry G' above the plateau.
    Gp, _ = star_spectrum(W_WIDE, G_N_FIG1, Z_FIG1, TAU_E_FIG1,
                          arm_rouse=False)
    assert Gp.max() / G_N_FIG1 == pytest.approx(1.0, abs=0.06)


def test_arm_rouse_modes_lift_G_prime_above_the_plateau():
    """G_N stops being the maximum of G' once the arm's Rouse modes are on.

    Guards against reading the fitted G_N as "the highest G' you will see".
    Real G' does climb above the plateau toward the glassy zone, which is
    exactly what these modes represent - but it means G_N is the plateau
    LEVEL, not a bound on the curve.
    """
    bare, _ = star_spectrum(W_WIDE, G_N_FIG1, Z_FIG1, TAU_E_FIG1,
                            arm_rouse=False)
    full, _ = star_spectrum(W_WIDE, G_N_FIG1, Z_FIG1, TAU_E_FIG1,
                            arm_rouse=True)
    assert full.max() > 1.5 * bare.max()
    # ...and they only ADD, never subtract, at every frequency.
    assert np.all(full >= bare - 1e-9 * bare.max())


def test_arm_rouse_modes_do_not_disturb_the_terminal_zone():
    """The added modes are a HIGH-frequency term and must leave flow alone.

    If they leaked into the terminal region they would corrupt the very
    thing the star class is identified by, so this pins the separation.
    """
    w_term = np.logspace(-12, -9, 40)
    bare = star_spectrum(w_term, G_N_FIG1, Z_FIG1, TAU_E_FIG1,
                         arm_rouse=False)
    full = star_spectrum(w_term, G_N_FIG1, Z_FIG1, TAU_E_FIG1,
                         arm_rouse=True)
    # Not exactly zero - a Maxwell mode's omega^1 tail reaches every
    # frequency - but 1e-4 decades is four orders below digitizing scatter,
    # so the terminal slopes and the flow behaviour are untouched.
    for b, f in zip(bare, full):
        assert np.max(np.abs(np.log10(f) - np.log10(b))) < 1e-4


def test_arm_rouse_mode_sum_is_converged_and_bounded():
    """The ladder truncation must be a converged approximation, not a cap.

    MODE_TAU_FLOOR_DECADES stops the sum where modes stop mattering; loosening
    it must not change the answer. It also has to stay fast for EVERY tau_e the
    optimizer can reach - bounding the sum by tau_e instead of by the window
    once reached ~3.7M modes and made a single fit take minutes.
    """
    w = np.logspace(-3, 3, 60)
    ref = star_spectrum(w, 4e5, 9.4, 1e-6)
    saved = star.MODE_TAU_FLOOR_DECADES
    try:
        star.MODE_TAU_FLOOR_DECADES = 4.0
        loose = star_spectrum(w, 4e5, 9.4, 1e-6)
    finally:
        star.MODE_TAU_FLOOR_DECADES = saved
    for r, l in zip(ref, loose):
        assert np.allclose(np.log10(r), np.log10(l), atol=5e-3)

    # A large tau_e must not blow the mode count up.
    t0 = time.perf_counter()
    star_spectrum(w, 4e5, 40.0, 1e3)
    assert time.perf_counter() - t0 < 1.0


def test_G_N_is_a_pure_amplitude():
    a = star_spectrum(W_WIDE, 1e6, 17.0, 1e-5)
    b = star_spectrum(W_WIDE, 2e6, 17.0, 1e-5)
    assert np.allclose(b[0], 2 * a[0], rtol=1e-12)
    assert np.allclose(b[1], 2 * a[1], rtol=1e-12)


def test_tau_e_is_a_pure_time_scale():
    # Scaling tau_e by c must map the curve rigidly to w -> w/c.
    w = np.logspace(-4, 4, 300)
    a = star_spectrum(w, 1e6, 17.0, 1e-5)
    b = star_spectrum(w / 10.0, 1e6, 17.0, 1e-4)
    assert np.allclose(a[0], b[0], rtol=1e-9)
    assert np.allclose(a[1], b[1], rtol=1e-9)


def test_arm_count_is_not_a_parameter():
    # The theory predicts LVE depends on ARM LENGTH only - a 3-arm and a
    # 12-arm star with the same Z relax identically. This is a real physical
    # claim (Pearson-Helfand's observed arm-number independence of viscosity),
    # so the signature must not grow an `f` to look more informative.
    import inspect
    assert "f" not in inspect.signature(star_spectrum).parameters


def test_spectrum_broadens_monotonically_with_Z():
    # Z is the only shape parameter; the barrier grows with it, so the
    # spectrum must widen. This is what makes Z identifiable against tau_e.
    #
    # Width is measured as the span of tau(s) itself rather than from the
    # G'' peak, because the peak is not a stable landmark: past Z ~ 40 the
    # barrier separates the Rouse and activated relaxations far enough that
    # G'' develops TWO maxima (see the test below), and the global peak jumps
    # between them. Measuring off the ladder avoids that discontinuity.
    s = np.linspace(0.01, 1.0 - 1e-9, 2000)
    spans = [np.log10(tau_of_s(s, Z, 1e-5).max() / tau_of_s(s, Z, 1e-5).min())
             for Z in (5.0, 10.0, 17.0, 25.0, 40.0)]
    assert np.all(np.diff(spans) > 0)


def test_high_entanglement_splits_G_double_prime_into_two_peaks():
    # Real feature of the theory, pinned so it is not mistaken for a bug or
    # a quadrature artifact later. tau(s) crosses over from the early Rouse
    # branch to the activated one (eq 22); when Z is large enough the
    # activated terminal time is pushed so far from the Rouse time that the
    # single broad loss peak resolves into two - a fast one near the
    # crossover frequency and a slow one near 1/tau(1). Verified converged:
    # identical peak positions for n_s from 400 to 64000.
    def n_maxima(Z):
        _, Gpp = star_spectrum(W_WIDE, 1e6, Z, 1e-5)
        return int((np.diff(np.sign(np.diff(Gpp))) < 0).sum())

    assert n_maxima(17.0) == 1
    assert n_maxima(25.0) == 1
    assert n_maxima(40.0) == 2


# --- inverse recovery -------------------------------------------------------

PLANTED = [
    (1.25e6, 17.0, 7.8e-6),
    (5.0e5, 8.0, 1.0e-4),
    (2.0e6, 30.0, 1.0e-6),
    (8.0e5, 12.0, 3.0e-5),
]


@pytest.mark.parametrize("G_N, Z, tau_e", PLANTED)
def test_planted_parameters_are_recovered_exactly_without_noise(G_N, Z, tau_e):
    w = np.logspace(-3, 5, 60)
    Gp, Gpp = star_spectrum(w, G_N, Z, tau_e)
    keep = (Gp > Gp.max() * 1e-6) & (Gpp > Gpp.max() * 1e-6)
    got = fit_star(w[keep], Gp[keep], Gpp[keep], n_restarts=24, seed=1)
    assert got["G_N"] == pytest.approx(G_N, rel=0.02)
    assert got["Z"] == pytest.approx(Z, rel=0.02)
    assert got["tau_e"] == pytest.approx(tau_e, rel=0.05)


@pytest.mark.parametrize("Z", [17.0, 30.0])
def test_recovery_survives_two_percent_noise(Z):
    # 2% log-normal is the digitizing scatter synth.py assumes for real figures.
    rng = np.random.default_rng(3)
    w = np.logspace(-3, 5, 50)
    Gp, Gpp = star_spectrum(w, 1e6, Z, 1e-5)
    Gp = Gp * np.exp(rng.normal(0, 0.02, len(w)))
    Gpp = Gpp * np.exp(rng.normal(0, 0.02, len(w)))
    got = fit_star(w, Gp, Gpp, n_restarts=24, seed=3)
    assert got["Z"] == pytest.approx(Z, rel=0.05)
    assert got["G_N"] == pytest.approx(1e6, rel=0.05)


def test_a_cropped_high_frequency_window_loses_Z_at_low_entanglement():
    # HONEST LIMIT, pinned deliberately. At Z = 8 the whole spectrum is only
    # ~3 decades wide, so a window that cuts the plateau leaves the G'' peak
    # at the edge and Z poorly constrained - the profile likelihood still has
    # its true minimum (verified: cost 5e-29 at Z=8 vs 2e-3 at Z=9), but 2%
    # noise is enough to move the optimum by ~20%. This is a window
    # limitation, not a fitter defect, and it is why the eventual class must
    # not report Z from a terminal-only sweep.
    rng = np.random.default_rng(0)
    w = np.logspace(-3, 2, 50)
    Gp, Gpp = star_spectrum(w, 1e6, 8.0, 1e-5)
    Gp = Gp * np.exp(rng.normal(0, 0.02, len(w)))
    Gpp = Gpp * np.exp(rng.normal(0, 0.02, len(w)))
    got = fit_star(w, Gp, Gpp, n_restarts=24, seed=0)
    assert got["Z"] != pytest.approx(8.0, rel=0.05)


def test_registry_entry_matches_the_house_shape():
    forward, p0, bounds, k = STAR_MODELS["star"]
    assert forward is model_star
    assert k == len(p0) == len(bounds) == 3
    Gp, Gpp = forward(np.logspace(-2, 2, 20), p0)
    assert np.all(np.isfinite(Gp)) and np.all(np.isfinite(Gpp))
    assert np.all(Gp > 0) and np.all(Gpp > 0)


def test_model_star_takes_log10_moduli_and_times():
    # The registry convention is log10 for moduli/times, linear for exponents
    # and counts - Z is a count, so it stays linear.
    w = np.logspace(-2, 2, 30)
    direct = star_spectrum(w, 1e6, 17.0, 1e-5)
    viareg = model_star(w, [6.0, 17.0, -5.0])
    assert np.allclose(direct[0], viareg[0])
    assert np.allclose(direct[1], viareg[1])


def test_star_is_in_the_identifier_bank():
    # Wired in 2026-09-09 after the pre-registered cannibalisation check
    # (scripts/check_star_cannibalisation.py). Replaced the earlier guard test
    # that asserted its ABSENCE while the check was outstanding.
    from rheofp.fitting.identify import ALL_MODELS
    assert ALL_MODELS["star"] == STAR_MODELS["star"]
    assert ALL_MODELS["star"][0] is model_star


def test_identify_recovers_a_planted_star_melt():
    # The point of the class existing: before it was on the ballot, `branched`
    # (BSW) absorbed 25/30 planted star melts silently and confidently.
    from rheofp.fitting.identify import identify
    w = np.logspace(-2, 4, 60)
    Gp, Gpp = star_spectrum(w, 1e6, 20.0, 1e-5)
    assert identify(w, Gp, Gpp, n_restarts=8)["best"] == "star"


# --- real data: the class's measured scope (step 4, 2026-09-09) -------------
#
# Milner-McLeish 1998's own seven-star validation set, Z = Ma/Me known from
# GPC. identify() returns `star` on five of the seven; the two misses are the
# two largest arms, and they are exactly the two curves whose window never
# reaches terminal flow. The tests below pin that split, because it IS the
# class's real-data warrant and it would otherwise regress silently.

# sample -> (Z_true, terminal flow observed?)
MM1998_SAMPLES = {
    "PI4_Ma11k": (2.20, True), "PI4_Ma17k": (3.40, True),
    "PI4_Ma36k": (7.20, True), "PI4_Ma44k": (8.80, True),
    "PI4_Ma47k": (9.40, True), "PI4_Ma95k": (19.00, False),
    "PI4_Ma105k": (21.00, False),
}


@pytest.mark.parametrize("sample", list(MM1998_SAMPLES))
def test_mm1998_terminal_flow_splits_exactly_at_the_two_largest_arms(sample):
    """Cheap (features only) and it is the precondition the class depends on.

    Every MM1998 curve the class gets right reaches terminal flow; both misses
    do not. Note this must NOT become a pre-filter discard - an unobserved
    terminal zone is missing evidence, not evidence against a star (the
    `has_shoulder` lesson, see next-actions).
    """
    from rheofp.io.data import load_npz
    from rheofp.fitting.identify import signature_features
    s = load_npz("data/mm1998.npz")[sample]
    feats, _ = signature_features(s["omega"], s["Gp"], s["Gpp"])
    # signature_features returns np.bool_, so compare by value not identity.
    assert bool(feats["terminal_reached"]) is MM1998_SAMPLES[sample][1]


def test_mm1998_mid_band_star_is_identified_decisively_on_real_data():
    """Ma36k, Z = 7.2: the cleanest of the five hits.

    star wins by dAICc 225 with rms 0.025 against branched's 0.062 - a
    decisive win on real data from a paper that measured Z independently, not
    a parsimony tie. Contrast the Z = 2.2 arm, where star still wins but only
    by dAICc ~5 with the rms tied, because below Z ~ 4 the retraction barrier
    is ~1 kT and there is no star-specific shape left to detect.
    """
    from rheofp.io.data import load_npz
    from rheofp.fitting.identify import identify
    s = load_npz("data/mm1998.npz")["PI4_Ma36k"]
    out = identify(s["omega"], s["Gp"], s["Gpp"], n_restarts=8)
    assert out["best"] == "star"
    star_row = next(r for r in out["ranking"] if r["name"] == "star")
    assert star_row["rms_log"] < 0.04
    runner_up = out["ranking"][1]
    assert runner_up["delta"] > 50.0


def test_lowering_the_Z_bounds_floor_does_not_rescue_weakly_entangled_arms():
    """The floor of 4 is a scope statement, not the thing clamping these fits.

    Measured 2026-09-09 on the two genuinely weakly-entangled arms (true Z
    3.40 and 2.20): the fitted Z sits at 9.12 and 6.66, both far ABOVE the
    floor, and dropping the floor to 3 or 2 moves neither. So the earlier note
    that the floor makes these "unfittable by construction" was wrong - what
    actually happens is that below Z ~ 4 the cost is flat in Z (no barrier, no
    distinguishable shape), so Z is unidentifiable there whatever the bound.
    identify() still returns `star` for both; only Z is wrong, and Z is
    already declared a non-reportable output.
    """
    from rheofp.io.data import load_npz
    d = load_npz("data/mm1998.npz")
    orig = star.Z_BOUNDS
    try:
        for sample in ("PI4_Ma17k", "PI4_Ma11k"):
            s = d[sample]
            fits = {}
            for floor in (4.0, 2.0):
                star.Z_BOUNDS = (floor, orig[1])
                fits[floor] = fit_star(s["omega"], s["Gp"], s["Gpp"],
                                       n_restarts=16, seed=0)
            # Not sitting on the bound at either setting, and unmoved by it.
            assert fits[4.0]["Z"] > 4.5, sample
            assert fits[2.0]["Z"] == pytest.approx(fits[4.0]["Z"], rel=0.05)
    finally:
        star.Z_BOUNDS = orig


# --- real data: Pryke 2002, a THIRD chemistry (1,2-polybutadiene) -----------
#
# Pryke, Blackwell, McLeish & Young (2002), Macromolecules 35, 467, Figure 2:
# symmetric THREE-ARM 1,2-PBD star melts at 333 K, Z = Ma/Me known from the
# paper's own tables (Me = 3550). Predictions were pre-registered in
# docs/pryke2001_preregistration.md BEFORE these curves were digitized; the
# OUTCOME section there records what held and what did not.
#
# Why this set earns tests of its own: every prior star validation is
# polyisoprene (mm1998) or polyisobutylene (santangelo1999), so this is the
# first evidence the class survives a change of chemistry.

PRYKE_SAMPLES = {"PBD3_Ma38k": 10.96, "PBD3_Ma78k": 22.14}


@pytest.mark.parametrize("sample", list(PRYKE_SAMPLES))
def test_pryke2002_star_is_identified_on_a_third_chemistry(sample):
    """P1 of the pre-registration, and it held on both well-entangled panels.

    dAICc 170 (Ma38k) and 87 (Ma78k) over `branched`, with star's rms 50% and
    29% better - decisive wins of the MM1998 mid-band kind, not the Z = 2.2
    parsimony tie.
    """
    from rheofp.io.data import load_npz
    from rheofp.fitting.identify import identify
    s = load_npz("data/pryke2002.npz")[sample]
    out = identify(s["omega"], s["Gp"], s["Gpp"], n_restarts=12)
    assert out["best"] == "star"
    assert out["ranking"][1]["delta"] > 50.0


@pytest.mark.parametrize("sample", list(PRYKE_SAMPLES))
def test_pryke2002_recovers_the_papers_own_plateau_modulus(sample):
    """The run's strongest positive result, and it was a pre-registered check.

    The paper states G_0 = 0.765 MPa for 1,2-PBD (Table 2). A free three-
    parameter fit that never saw that number returns 0.776 and 0.731 MPa -
    within 1.4% and 4.4%. Item 3 on the pre-registration's "what would count
    as a genuine problem" list was G_N landing far from 0.765; it did not.

    Note G' RISES ABOVE G_N at high frequency here (max G' is 3.3-3.6x G_0)
    because of the arm-Rouse term - G_N is the plateau LEVEL, not the curve
    maximum. Comparing the paper's G_0 against max(G') would fail this test
    for the wrong reason.
    """
    from rheofp.io.data import load_npz
    s = load_npz("data/pryke2002.npz")[sample]
    fit = fit_star(s["omega"], s["Gp"], s["Gpp"], n_restarts=12, seed=0)
    assert fit["G_N"] == pytest.approx(0.765e6, rel=0.10)


@pytest.mark.parametrize("sample", list(PRYKE_SAMPLES))
def test_pryke2002_Z_is_biased_high_and_stays_non_reportable(sample):
    """P3: Z came back +24% and +42%, inside the +17-84% band from MM1998.

    Pinned so that nobody later reads a plausible-looking Z off this dataset
    and starts reporting it. The class says "star", never "Z = ...".
    """
    from rheofp.io.data import load_npz
    s = load_npz("data/pryke2002.npz")[sample]
    fit = fit_star(s["omega"], s["Gp"], s["Gpp"], n_restarts=12, seed=0)
    z_true = PRYKE_SAMPLES[sample]
    assert fit["Z"] > z_true, "bias has flipped sign - re-read the envelope"
    assert fit["Z"] < 1.9 * z_true


def test_terminal_reached_is_a_sharp_threshold_that_a_flowing_melt_can_miss():
    """P4's PREMISE failed here, and this pins the reason so it is not re-guessed.

    The pre-registration made `terminal_reached` the predictor of the class's
    real-data success (5/5 True, 1/5 False across MM1998 + Santangelo). On
    Pryke both samples read False and `star` was correct on BOTH.

    The cause is not subtle once measured: the feature is a hard threshold,
    `slope_Gp_lo > 1.4 and slope_Gpp_lo > 0.7`, and Ma38k measures 1.39 /
    0.625 - it misses the G' cut by 0.01 while plainly flowing (G''/G' = 33 at
    its lowest raw point, terminal slopes 1.87 / 0.85 on the raw trace before
    the common-grid interpolation smooths the low-frequency end).

    So the honest statement is NOT "the envelope is wrong" but "a threshold
    this sharp will call a flowing melt non-terminal". Left UNCHANGED
    deliberately: n=2, the feature gates a sound positive-observation discard
    (flow rules out permanent networks), and moving a threshold to fit two
    curves is what this project pre-registers against.
    """
    from rheofp.io.data import load_npz
    from rheofp.fitting.identify import signature_features
    s = load_npz("data/pryke2002.npz")["PBD3_Ma38k"]
    feats, allowed = signature_features(s["omega"], s["Gp"], s["Gpp"])
    assert bool(feats["terminal_reached"]) is False
    # ... yet it sits within a whisker of the cut, on the correct side physically
    assert feats["slope_Gp_lo"] == pytest.approx(1.39, abs=0.05)
    assert feats["slope_Gp_lo"] < 1.4
    # and because flow was not "observed", the network classes stay on the
    # ballot - star still wins on merit rather than by elimination.
    assert "cured_elastomer" in allowed
