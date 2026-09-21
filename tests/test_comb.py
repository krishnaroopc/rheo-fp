"""McLeish et al. (1999) comb/H-polymer model: forward physics + recovery.

The forward tests pin the model against the paper's own analytic statements and
against defects that were actually hit while writing it - the arm/cross-bar
ladder inversion and the tau_e bounds artefact both shipped in working code and
were caught by measurement, so these are regression tests in the strict sense.

Reference: Macromolecules 1999, 32, 6734
(originals/mcleish1999_h_polymers.pdf), with
McLeish & Larson 1998 (mcleish_larson1998_pompom.pdf) as the superseded
precursor and Kapnistos et al. 2005
(kapnistos2005_comb_linear_backbone.pdf) as the comb-side
cross-check on the two disputed constants.
"""
import numpy as np
import pytest

from rheofp.models.comb import (
    ARM_BARRIER_COEFF, BACKBONE_BARRIER_COEFF, COMB_MODELS, N_RESTARTS,
    P_SQUARED, Q_FIXED, R_DILUTION, X_EPS, arm_potential, backbone_potential,
    comb_spectrum, fit_comb, model_comb, phi_b_from_architecture, solve_xc,
    tau_arm, tau_backbone, _arm_potential_slope, _backbone_potential_slope,
)

# ML1999's own PI values, section 4.1: G_0 ~ 0.52 MPa and tau_e ~ 7e-6 s at
# 25 C, held "within factors of 1.2" across their samples. s_a/s_b here are in
# the range of their Table 2 fitted values.
G_0_PI = 5.2e5
TAU_E_PI = 7e-6
S_A_REF, S_B_REF, PHI_B_REF = 8.0, 30.0, 0.30

W_WIDE = np.logspace(-8, 7, 500)


# --- the potentials: eqs 25, 28, 35, 37 -------------------------------------

def test_arm_potential_is_zero_at_the_free_end_and_maximal_at_the_branch():
    # x_a runs from the FREE END (0) to the BRANCH POINT (1), the same
    # orientation as star.py's s and the OPPOSITE of ML1998's x. Getting this
    # backwards inverts the entire spectrum, so it is pinned.
    assert arm_potential(0.0, S_A_REF, 0.7) == pytest.approx(0.0)
    assert arm_potential(1.0, S_A_REF, 0.7) > 0.0
    u = arm_potential(np.linspace(0.0, 1.0, 50), S_A_REF, 0.7)
    assert np.all(np.diff(u) > 0)


def test_backbone_potential_is_zero_at_the_branch_and_maximal_at_the_middle():
    assert backbone_potential(0.0, S_B_REF, PHI_B_REF) == pytest.approx(0.0)
    assert backbone_potential(1.0, S_B_REF, PHI_B_REF) > 0.0
    u = backbone_potential(np.linspace(0.0, 1.0, 50), S_B_REF, PHI_B_REF)
    assert np.all(np.diff(u) > 0)


@pytest.mark.parametrize("potential,slope,args", [
    (arm_potential, _arm_potential_slope, (S_A_REF, 0.7)),
    (backbone_potential, _backbone_potential_slope, (S_B_REF, PHI_B_REF)),
])
def test_potential_slopes_are_analytic_and_correct(potential, slope, args):
    # The slopes are stated separately in the paper (under eqs 30 and 39) and
    # are used in the first-passage prefactor, so an inconsistency between
    # U and dU/dx would be silent.
    x = np.linspace(0.05, 0.95, 9)
    h = 1e-6
    fd = (potential(x + h, *args) - potential(x - h, *args)) / (2 * h)
    assert np.allclose(slope(x, *args), fd, rtol=1e-5)


def test_cross_bar_barrier_is_half_the_arm_barrier_coefficient():
    # eq 25 gives U = (15/8) s_a x^2 for an arm; eq 35 gives (15/16) s_b x^2
    # for the cross-bar, because the cross-bar is treated as a two-arm star of
    # arm length N_b/2.
    assert BACKBONE_BARRIER_COEFF == pytest.approx(ARM_BARRIER_COEFF / 2.0)


def test_cross_bar_material_deepens_the_arm_barrier():
    # Section 4.1: arms on an H-polymer relax exponentially slower than the
    # same arms on a pure star, because cross-bar material acts as a permanent
    # network throughout arm relaxation. This is the paper's explanation of
    # Roovers' viscosity-enhancement observation. Lower phi_a = more cross-bar.
    deep = arm_potential(1.0, S_A_REF, 0.5)
    shallow = arm_potential(1.0, S_A_REF, 1.0)
    assert deep > shallow


def test_phi_b_from_architecture_matches_the_geometric_identity():
    # ML1998 eq 10: phi_b = s_b / (s_b + 2 q s_a).
    assert phi_b_from_architecture(8.0, 30.0, q=2.0) == pytest.approx(
        30.0 / (30.0 + 2.0 * 2.0 * 8.0))


# --- the hierarchy: the defect that destroyed the signature -----------------

def test_the_arm_and_crossbar_ladders_do_not_overlap():
    """REGRESSION. The cross-bar ladder must START where the arm ladder ENDS.

    A branch point cannot hop until its arms have fully retracted (section 2.1
    step iii), so tau_b(0) >= tau_a(1) is the hierarchy itself. Before the
    floors were added the backbone ladder began 15.8 decades BELOW the arm
    ladder's end - eq 34's x_b^2 early branch sends tau_b -> 0 at x_b -> 0 -
    which interleaved the two ladders and destroyed the two-feature signature.
    """
    x = np.linspace(X_EPS, 1.0 - X_EPS, 200)
    ta = tau_arm(x, S_A_REF, 1.0 - PHI_B_REF, TAU_E_PI)
    tb = tau_backbone(x, S_A_REF, S_B_REF, PHI_B_REF, TAU_E_PI)
    assert tb.min() >= ta.max() * (1.0 - 1e-9)


def test_the_arm_ladder_is_floored_at_tau_e():
    """REGRESSION. Eq 3 is an x_a -> 0 ASYMPTOTE, not a spectrum.

    Taken literally it put the fastest arm mode at 2.5e-37 s (a 37-decade
    ladder). The paper bounds the entangled description at tau_e, the Rouse
    time of one entanglement length, with the G'' minimum at w ~ 1/tau_e and
    free Rouse modes above it - which ML1999 says outright its theory does not
    cover. star.py records the identical trap for its eq 13.
    """
    x = np.linspace(X_EPS, 1.0 - X_EPS, 200)
    ta = tau_arm(x, S_A_REF, 1.0 - PHI_B_REF, TAU_E_PI)
    assert ta.min() >= TAU_E_PI * (1.0 - 1e-9)
    # ...and the ladder stays physically narrow, not tens of decades.
    assert np.log10(ta.max() / ta.min()) < 12.0


def test_the_spectrum_shows_the_two_feature_H_polymer_signature():
    """The whole reason this class exists (ML1999 section 4.1, Figure 6).

    An arm SHOULDER at high frequency and a separate weak cross-bar MAXIMUM at
    low frequency, with a G'' minimum between them. With the ladders
    interleaved there was exactly one maximum and no minimum anywhere in a
    14-decade window.
    """
    Gp, Gpp = comb_spectrum(W_WIDE, G_0_PI, S_A_REF, S_B_REF, PHI_B_REF,
                            TAU_E_PI, n_x=400)
    lpp = np.log10(np.clip(Gpp, 1e-30, None))
    sign = np.sign(np.diff(lpp))
    maxima = int(np.sum((sign[:-1] > 0) & (sign[1:] < 0)))
    minima = int(np.sum((sign[:-1] < 0) & (sign[1:] > 0)))
    assert maxima >= 2, "arm and cross-bar features are not resolved"
    assert minima >= 1, "no G'' minimum between the two relaxations"


def test_the_arm_shoulder_widens_with_arm_molecular_weight():
    """ML1999 Figure 4a, checked against the paper's own words.

    "The shoulder feature at higher frequencies in G'' is a clear signature of
    the arm relaxations; its logarithmic WIDTH INCREASES WITH THE ARM
    MOLECULAR WEIGHT." Figure 4a plots s_a = 4, 6, 8 at fixed s_b = 30.

    This is the external gate this module was held to before being trusted -
    the direct analogue of the Figure 2 potential check that caught the eq-29
    prefactor error in star.py.
    """
    widths = []
    for s_a in (4.0, 6.0, 8.0):
        phi_b = phi_b_from_architecture(s_a, 30.0)
        x = np.linspace(X_EPS, 1.0 - X_EPS, 300)
        ta = tau_arm(x, s_a, 1.0 - phi_b, TAU_E_PI)
        widths.append(np.log10(ta.max() / ta.min()))
    assert np.all(np.diff(widths) > 0), f"shoulder widths not growing: {widths}"


def test_the_cross_bar_peak_strengthens_and_slows_with_the_cross_bar():
    """ML1999 Figure 4b: "lengthening the cross-bar takes the peak to lower
    frequencies, whereas reducing it both speeds up the cross-bar relaxation
    and WEAKENS THE MAGNITUDE of the peak as phi_b reduces."

    Measured on the CROSS-BAR CONTRIBUTION ALONE, and that isolation is the
    whole point of the test. Reading the low-frequency maximum off the FULL
    spectrum gives the opposite answer at small phi_b, because there the
    cross-bar and arm features merge into a single larger peak - see the
    module docstring on the non-fixed maximum count. A naive probe on the full
    spectrum reported this behaviour as REFUTED; it is not.
    """
    from rheofp.models.maxwell import maxwell_spectrum
    import rheofp.models.comb as C

    w = np.logspace(-10, 7, 900)
    heights, positions = [], []
    for s_b in (20.0, 25.0, 30.0):
        phi_b = phi_b_from_architecture(6.0, s_b)
        x = np.linspace(X_EPS, 1.0 - X_EPS, 300)
        dx = x[1] - x[0]
        tb = tau_backbone(x, 6.0, s_b, phi_b, TAU_E_PI)
        g = (G_0_PI * (R_DILUTION + 1.0) * dx
             * phi_b ** (R_DILUTION + 1.0) * (1.0 - x) ** R_DILUTION)
        _, Gpp = maxwell_spectrum(w, g, tb)
        i = int(np.argmax(Gpp))
        heights.append(Gpp[i])
        positions.append(w[i])

    assert np.all(np.diff(heights) > 0), f"peak not strengthening: {heights}"
    assert np.all(np.diff(positions) < 0), f"peak not slowing: {positions}"


def test_the_number_of_loss_peaks_is_not_fixed_for_this_class():
    """A caveat, pinned so no pre-filter rule quietly assumes otherwise.

    Two resolved G'' maxima at phi_b <= 0.40, three at phi_b >= 0.50: at low
    phi_b the cross-bar and arm features MERGE. star.py carries the same shape
    of warning for its two-peak split past Z ~ 40. Any feature keyed on "the"
    loss peak, or on a fixed peak count, will misread a comb.
    """
    def n_maxima(phi_b):
        w = np.logspace(-10, 7, 900)
        _, Gpp = comb_spectrum(w, G_0_PI, 6.0, 30.0, phi_b, TAU_E_PI, n_x=300)
        sign = np.sign(np.diff(np.log10(np.clip(Gpp, 1e-30, None))))
        return int(np.sum((sign[:-1] > 0) & (sign[1:] < 0)))

    assert n_maxima(0.30) == 2
    assert n_maxima(0.60) == 3


def test_lengthening_the_cross_bar_moves_its_peak_to_lower_frequency():
    # Section 2.1, under Figure 4: "lengthening the cross-bar takes the peak to
    # lower frequencies". A directional check the paper states in words.
    def slowest(s_b):
        x = np.linspace(X_EPS, 1.0 - X_EPS, 200)
        return tau_backbone(x, S_A_REF, s_b, PHI_B_REF, TAU_E_PI).max()

    assert slowest(40.0) > slowest(30.0) > slowest(20.0)


def test_the_backbone_terminal_time_is_exponential_in_ARM_length():
    # eq 32/34: the branch-point friction carries tau_a(1), so a modest arm on
    # a long cross-bar still dominates the terminal time. Doubling s_a must
    # move the backbone terminal far more than doubling s_b does.
    def slowest(s_a, s_b):
        x = np.linspace(X_EPS, 1.0 - X_EPS, 200)
        return tau_backbone(x, s_a, s_b, PHI_B_REF, TAU_E_PI).max()

    base = slowest(6.0, 30.0)
    by_arm = slowest(12.0, 30.0) / base
    by_bar = slowest(6.0, 60.0) / base
    assert by_arm > by_bar


# --- x_c: the self-consistent crossover, eq 43 ------------------------------

def test_xc_is_a_smooth_interior_solution_across_the_working_range():
    # eq 43 solves tau_rep(x_c) = tau_b,ret(x_c), self-consistent because
    # tau_rep carries (1-x_c)^2. A discontinuity here was suspected of causing
    # a recovery failure and was REFUTED by measurement - x_c varies smoothly
    # (0.872 -> 0.841) straight through the case that failed. Recorded so the
    # hypothesis is not re-tried.
    xs = [solve_xc(6.0, 20.0, p, 1e-5) for p in
          (0.30, 0.35, 0.38, 0.40, 0.42, 0.45, 0.50)]
    assert all(0.0 < x < 1.0 for x in xs)
    assert np.all(np.diff(xs) < 0)          # monotone, no jumps
    assert max(np.abs(np.diff(xs))) < 0.05  # and smooth


# --- the modulus: eqs 22-24 -------------------------------------------------

def test_terminal_slopes_are_those_of_a_flowing_melt():
    w = np.logspace(-8, -5, 40)
    Gp, Gpp = comb_spectrum(w, G_0_PI, S_A_REF, S_B_REF, PHI_B_REF, TAU_E_PI)
    lw = np.log10(w)
    assert np.polyfit(lw, np.log10(Gp), 1)[0] == pytest.approx(2.0, abs=0.05)
    assert np.polyfit(lw, np.log10(Gpp), 1)[0] == pytest.approx(1.0, abs=0.05)


def test_G_0_is_a_pure_amplitude():
    args = (S_A_REF, S_B_REF, PHI_B_REF, TAU_E_PI)
    w = np.logspace(-4, 4, 40)
    a = comb_spectrum(w, 1.0e5, *args)
    b = comb_spectrum(w, 3.0e5, *args)
    assert np.allclose(b[0] / a[0], 3.0)
    assert np.allclose(b[1] / a[1], 3.0)


def test_tau_e_is_a_pure_time_scale():
    # Every tau in the model is proportional to tau_e, so changing it must
    # translate the spectrum rigidly in log omega and nothing else.
    w = np.logspace(-4, 4, 60)
    a = comb_spectrum(w, G_0_PI, S_A_REF, S_B_REF, PHI_B_REF, 1e-5)
    b = comb_spectrum(w * 10.0, G_0_PI, S_A_REF, S_B_REF, PHI_B_REF, 1e-6)
    assert np.allclose(a[0], b[0], rtol=1e-6)
    assert np.allclose(a[1], b[1], rtol=1e-6)


def test_the_spectrum_is_converged_in_the_quadrature_resolution():
    w = np.logspace(-6, 6, 80)
    ref = comb_spectrum(w, G_0_PI, S_A_REF, S_B_REF, PHI_B_REF, TAU_E_PI,
                        n_x=200)
    fine = comb_spectrum(w, G_0_PI, S_A_REF, S_B_REF, PHI_B_REF, TAU_E_PI,
                         n_x=1600)
    for a, b in zip(ref, fine):
        d = np.abs(np.log10(np.clip(a, 1e-30, None))
                   - np.log10(np.clip(b, 1e-30, None)))
        assert d.max() < 0.05


# --- what the class cannot say ----------------------------------------------

def test_arm_count_is_degenerate_with_the_time_scale():
    """q is NOT a free parameter and must never become one.

    q enters the linear theory only through the branch-point diffusion
    constant (eq 32), where it multiplies tau_a(1). Doubling q and halving
    tau_e is therefore the same curve - so a fitted q would be meaningless.
    Same situation star.py documents for star arm number.
    """
    w = np.logspace(-4, 4, 60)
    a = comb_spectrum(w, G_0_PI, S_A_REF, S_B_REF, PHI_B_REF, TAU_E_PI, q=2.0)
    b = comb_spectrum(w, G_0_PI, S_A_REF, S_B_REF, PHI_B_REF, TAU_E_PI, q=4.0)
    # Not identical curves, but q's effect is a pure shift of the backbone
    # ladder - it cannot produce a shape q=2 could not.
    assert not np.allclose(a[0], b[0])
    x = np.linspace(X_EPS, 1.0 - X_EPS, 100)
    t2 = tau_backbone(x, S_A_REF, S_B_REF, PHI_B_REF, TAU_E_PI, q=2.0)
    t4 = tau_backbone(x, S_A_REF, S_B_REF, PHI_B_REF, TAU_E_PI, q=4.0)
    ratio = t4 / t2
    interior = ratio[(t2 > t2.min() * 1.01)]
    assert np.allclose(interior, interior[0], rtol=1e-6)


def test_the_two_disputed_constants_carry_their_source_values():
    # R: 4/3 in ML1999 Appendix A eq 26; 1 in Kapnistos 2005, who call the
    # question unresolved. p^2: 1/6 in ML1999 eq 32; 1/12 in Kapnistos Table 2.
    # Both are FIXED, not fitted - a free p^2 would absorb exactly the spectral
    # width that s_a and s_b exist to determine. This test exists so a silent
    # change to either constant is visible in the diff.
    assert R_DILUTION == pytest.approx(4.0 / 3.0)
    assert P_SQUARED == pytest.approx(1.0 / 6.0)
    assert Q_FIXED == 2.0


# --- inverse recovery -------------------------------------------------------

@pytest.mark.parametrize("s_a,s_b,phi_b,tau_e", [
    (8.0, 30.0, 0.30, 7e-6),
    (6.0, 30.0, 0.30, 1e-5),
    (8.0, 30.0, 0.30, 1e-4),
    (12.0, 40.0, 0.25, 3e-6),
    (6.0, 20.0, 0.40, 1e-5),
])
def test_planted_parameters_are_recovered_from_clean_data(s_a, s_b, phi_b,
                                                          tau_e):
    w = np.logspace(-4, 4, 60)
    Gp, Gpp = comb_spectrum(w, G_0_PI, s_a, s_b, phi_b, tau_e)
    r = fit_comb(w, Gp, Gpp, n_restarts=N_RESTARTS, seed=1)
    assert r["rms_decades"] < 1e-3
    assert r["s_a"] == pytest.approx(s_a, rel=0.02)
    assert r["s_b"] == pytest.approx(s_b, rel=0.02)
    assert r["phi_b"] == pytest.approx(phi_b, rel=0.02)
    assert r["tau_e"] == pytest.approx(tau_e, rel=0.05)
    assert r["G_0"] == pytest.approx(G_0_PI, rel=0.02)


def test_the_true_vector_is_the_global_minimum_not_merely_a_good_one():
    """REGRESSION for the tau_e bounds artefact.

    fit_comb's tau_e bound used to be centred on 1/median(omega), which for a
    logspace(-4, 4) sweep floors it at 9.88e-05 - so a planted tau_e of 7e-6
    was OUTSIDE the box and the fit pinned on the bound at +1311% error. The
    bound is now anchored to 1/omega_max, since tau_e is the FASTEST time in
    the model. Cost at the true vector beats the pinned point by thirteen
    orders of magnitude, which is what makes this a bounds bug and not a
    degeneracy.
    """
    w = np.logspace(-4, 4, 60)
    Gp, Gpp = comb_spectrum(w, G_0_PI, S_A_REF, S_B_REF, PHI_B_REF, TAU_E_PI)

    def cost(theta):
        mp, mpp = comb_spectrum(w, 10.0**theta[0], *theta[1:4], 10.0**theta[4])
        r = np.concatenate([np.log10(mp) - np.log10(Gp),
                            np.log10(mpp) - np.log10(Gpp)])
        return float(np.sum(r * r))

    true = [np.log10(G_0_PI), S_A_REF, S_B_REF, PHI_B_REF,
            np.log10(TAU_E_PI)]
    pinned = [np.log10(4.581e5), 5.171, 30.61, 0.3242, np.log10(9.879e-05)]
    assert cost(true) < cost(pinned) * 1e-10


def test_twelve_restarts_is_not_enough_for_this_parameter_space():
    """Why N_RESTARTS is 24 and must not be trimmed back.

    The same planted curve recovers exactly at seed 2 and fails at seed 1 with
    12 restarts - a sampling failure, not a degeneracy, since the global
    minimum sits thirteen orders of magnitude below where 12 restarts landed.
    If this test ever starts passing at 12, the basin got easier and the
    constant can be revisited deliberately; it should not drift.
    """
    w = np.logspace(-4, 4, 60)
    Gp, Gpp = comb_spectrum(w, G_0_PI, 6.0, 20.0, 0.40, 1e-5)
    bad = fit_comb(w, Gp, Gpp, n_restarts=12, seed=1)
    good = fit_comb(w, Gp, Gpp, n_restarts=N_RESTARTS, seed=1)
    assert bad["rms_decades"] > 1e-2
    assert good["rms_decades"] < 1e-3


# --- registry / bank wiring -------------------------------------------------

def test_registry_entry_matches_the_house_shape():
    forward, p0, bounds, k = COMB_MODELS["comb"]
    assert forward is model_comb
    assert k == len(p0) == len(bounds) == 5
    Gp, Gpp = forward(np.logspace(-2, 2, 20), p0)
    assert np.all(np.isfinite(Gp)) and np.all(np.isfinite(Gpp))
    assert np.all(Gp > 0) and np.all(Gpp > 0)


def test_model_comb_takes_log10_moduli_and_times():
    # House convention: log10 for moduli and times, linear for counts and
    # fractions - so s_a, s_b and phi_b stay linear.
    w = np.logspace(-2, 2, 30)
    direct = comb_spectrum(w, 1e6, 8.0, 30.0, 0.30, 1e-5)
    viareg = model_comb(w, [6.0, 8.0, 30.0, 0.30, -5.0])
    assert np.allclose(direct[0], viareg[0])
    assert np.allclose(direct[1], viareg[1])


def test_comb_is_NOT_in_the_identifier_bank():
    """DELIBERATELY UNWIRED 2026-09-14, after the check found real-data damage.

    The synthetic cannibalisation check passed on its own terms (every class
    unchanged except sticky_reptation 29->27, real benchmark 6/6). It was
    WRONG to read that as safe, for two reasons now fixed in
    scripts/check_comb_cannibalisation.py:

      * it scored only WHETHER the winning class changed, never BY HOW MUCH,
        so a collapse in winning margin was invisible;
      * it scored real data only against the 6-curve benchmark, which contains
        no star curve at all.

    Wiring `comb` in was then measured directly against MM1998's seven real
    four-arm polyisoprene stars, where the architecture is known from
    synthesis. `star` went 5/7 -> 4/7 (PI4_Ma47k flipped to `comb`), and the
    surviving decisive calls collapsed from margins of 194-225 to 7.6-27.4,
    with Ma44k at dAICc 7.6 leaving `comb` a live contender.

    The cause is physical, not a bug: a comb with a short cross-bar is very
    nearly a star, and `comb` has 5 parameters against `star`'s 3. `star` has
    real validation across three chemistries; `comb` has none yet. Trading a
    confirmed capability for an unconfirmed one is the wrong direction.

    This is not permanent. Real comb data (Kapnistos 2005, McLeish 1999
    Figure 6) is the next task; with it, the question becomes whether a
    PHYSICAL restriction - an entangled-cross-bar requirement, or the
    two-feature signature - separates the classes on real curves. See
    .claude-notes/next-actions.md.
    """
    from rheofp.fitting.identify import ALL_MODELS
    assert "comb" not in ALL_MODELS


def test_a_planted_comb_is_misidentified_while_the_class_is_unwired():
    """What an end user uploading comb data is told TODAY, pinned honestly.

    Measured over 30 planted combs with `comb` absent from the bank: branched
    12/30, critical_gel 10/30, star 6/30, sticky_reptation 2/30 - always
    wrong, never uncertain, and not even consistently wrong in one direction.
    This is the documented "good fit of the WRONG class" failure, and the
    none-of-the-above floor cannot catch it because the most flexible
    candidate present simply absorbs the curve.

    The test asserts the SHAPE of that failure rather than a specific wrong
    label, so it records the cost of the unwired state without becoming
    brittle. It should be deleted by whichever commit wires `comb` in.
    """
    from rheofp.fitting.identify import identify
    w = np.logspace(-3, 4, 70)
    Gp, Gpp = comb_spectrum(w, G_0_PI, 8.0, 30.0, 0.30, 1e-5)
    out = identify(w, Gp, Gpp, n_restarts=8)
    assert out["best"] != "comb"          # unreachable: not in the bank
    assert out["best_rms_log"] < 0.15     # and it fits WELL, which is the trap
