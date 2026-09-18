"""Forward-physics validation for the des Cloizeaux TDD-DR model.

Validation-first: these check the forward model against the PAPER'S OWN
analytic statements before anything is fitted, and before it is wired into
`identify()`. See `docs/tdd_preregistration.md` for P1.
"""
import numpy as np
import pytest

from rheofp.models import tdd


# --- the g(y) fluctuation function -----------------------------------------

def test_simplified_g_matches_the_exact_series_at_small_y():
    """vR2002 Table 1 prints BOTH the exact series
    g(y) = sum_n (1-exp(-n^2 y))/n^2 and a 'simplified form'. The simplified
    form is what this module uses, so it has to reproduce the series - but
    ONLY where the approximation is valid, see the next test."""
    y = np.logspace(-4, -0.8, 40)
    approx = tdd.g_dc(y)
    exact = tdd.g_dc_series(y)
    rel = np.abs(approx - exact) / np.abs(exact)
    assert rel.max() < 0.02, f"max relative error {rel.max():.4f}"


def test_the_simplified_g_DIVERGES_from_the_series_at_large_y():
    """A LIMIT of the paper's simplified form, pinned so nobody 'fixes' the
    test above by widening its range.

    The exact series saturates at g(inf) = sum_n 1/n^2 = pi^2/6 = 1.6449.
    The simplified closed form grows without bound (it goes as ~sqrt(pi y) for
    large y). They part company around y ~ 0.2 and are 5x apart by y = 100.

    This is harmless HERE only because g enters U(t) as g(H t/tau_rep)/H
    divided by H, and by the time y is large the t/tau_rep term dominates U
    completely - checked by `test_U_reduces_to_doi_edwards_at_long_times`.
    It would NOT be harmless if g were ever used on its own.
    """
    assert tdd.g_dc_series(np.array([1e3]))[0] == pytest.approx(np.pi**2 / 6, rel=1e-3)
    assert tdd.g_dc(np.array([1e3]))[0] > 10 * np.pi**2 / 6


def test_g_has_the_right_small_y_limit():
    """As y -> 0 every term -> n^2 y / n^2 = y, so g(y) -> y * sum_n 1
    diverges; the physical content is the leading sqrt(pi y) behaviour of the
    simplified form. Check g is positive and grows sublinearly in y."""
    y = np.logspace(-6, -2, 20)
    g = tdd.g_dc(y)
    assert np.all(g > 0)
    # sublinear: g/y must DECREASE as y grows in this regime
    assert np.all(np.diff(g / y) < 0)


def test_g_is_monotone_increasing():
    y = np.logspace(-4, 3, 200)
    assert np.all(np.diff(tdd.g_dc(y)) > 0)


# --- the U(t) and F(t) kernel ----------------------------------------------

def test_U_reduces_to_doi_edwards_at_long_times():
    """The g(y)/H term saturates (g grows sublinearly), so at t >> tau_rep
    U(t) -> t/tau_rep, i.e. plain Doi-Edwards. That is the whole claim of the
    'time-dependent' diffusion: it is only time-dependent EARLY."""
    Z, tr = 20.0, 1.0
    t = np.array([1e3, 1e4, 1e5]) * tr
    U = tdd.U_of_t(t, Z, tr)
    ratio = U / (t / tr)
    assert np.all(ratio < 1.02), ratio
    assert ratio[-1] < ratio[0], "should approach DE from above"


def test_F_starts_at_one_and_decays_to_zero():
    Z, tr = 20.0, 1.0
    assert tdd.F_tdd(np.array([1e-12]), Z, tr)[0] == pytest.approx(1.0, abs=2e-2)
    assert tdd.F_tdd(np.array([1e4]), Z, tr)[0] < 1e-6


def test_F_is_monotone_decreasing():
    t = np.logspace(-8, 4, 300)
    F = tdd.F_tdd(t, 20.0, 1.0)
    assert np.all(np.diff(F) <= 1e-15)


def test_tdd_relaxes_faster_than_plain_doi_edwards():
    """The fluctuation term ADDS to U, and F ~ exp(-U), so TDD must relax
    faster than DE at every time. This is the sign check that catches a
    dropped minus sign in g."""
    Z, tr = 20.0, 1.0
    t = np.logspace(-6, 2, 50)
    U_tdd = tdd.U_of_t(t, Z, tr)
    U_de = t / tr
    assert np.all(U_tdd >= U_de)


# --- P1: the shape invariants of an entangled linear melt ------------------

@pytest.mark.parametrize("Z", [8.0, 20.0, 40.0])
def test_terminal_slopes_are_two_and_one(Z):
    """P1. Any liquid must go as G' ~ w^2, G'' ~ w^1 at low frequency."""
    w = np.logspace(-8, -6, 12) / 1.0
    Gp, Gpp = tdd.Gstar(w, Z, 1.0, 1e6)
    sp = np.polyfit(np.log10(w), np.log10(Gp), 1)[0]
    spp = np.polyfit(np.log10(w), np.log10(Gpp), 1)[0]
    assert sp == pytest.approx(2.0, abs=0.02), sp
    assert spp == pytest.approx(1.0, abs=0.02), spp


def test_plateau_increases_monotonically_with_Z():
    """P1. More entanglements -> the plateau is better developed. This is the
    check that would catch Z doing nothing at all.

    Measured on the BARE kernel: with Rouse on, G' keeps rising past G_N at
    high frequency, so `max()` reads the Rouse wing rather than the plateau
    and the comparison is not about entanglement any more.
    """
    w = np.logspace(-6, 4, 300)
    peaks = [tdd.Gstar(w, Z, 1.0, 1e6, rouse=False)[0].max()
             for Z in (5, 10, 20, 40, 80)]
    assert np.all(np.diff(peaks) > 0), peaks


def test_plateau_approaches_Ge_with_the_bare_kernel():
    """With Rouse OFF the TDD kernel alone cannot exceed G_N, so G_N is the
    curve maximum. (With Rouse ON it can - see the next test.)"""
    w = np.logspace(-6, 6, 400)
    Gp, _ = tdd.Gstar(w, 40.0, 1.0, 1e6, rouse=False)
    assert Gp.max() < 1e6 * 1.001
    assert Gp.max() > 1e6 * 0.75


def test_Ge_is_the_plateau_level_not_the_curve_maximum():
    """Same caveat `star.py` carries: once the Rouse modes are added G' rises
    ABOVE G_N at high frequency. Anyone reading a fitted Ge as 'the highest G'
    on the curve' is wrong, and this pins that."""
    w = np.logspace(-6, 8, 600)
    Gp, _ = tdd.Gstar(w, 40.0, 1.0, 1e6, rouse=True)
    assert Gp.max() > 1e6


def test_there_is_a_single_G_double_prime_minimum():
    """P1. A well-entangled melt shows ONE loss minimum, between the terminal
    peak and the high-frequency Rouse rise. Two would mean the ladder is
    aliasing; ZERO means the Rouse term is missing, which is exactly the bug
    this caught on the bare kernel (G'' decayed as w^-0.23 forever).

    Window starts above the terminal peak: below it G'' falls monotonically
    toward w^1, so a window opening there puts the minimum on the edge.
    """
    w = np.logspace(-2, 6, 800)
    _, Gpp = tdd.Gstar(w, 40.0, 1.0, 1e6)
    lg = np.log10(Gpp)
    # count interior local minima, ignoring numerical wiggle
    is_min = (lg[1:-1] < lg[:-2] - 1e-9) & (lg[1:-1] < lg[2:] - 1e-9)
    assert is_min.sum() == 1, f"found {is_min.sum()} minima"


def test_the_bare_kernel_has_NO_rouse_rise():
    """Pins WHY `_rouse_modes` exists. van Ruymbeke add Rouse by an explicit
    linear mixing rule because the TDD kernel does not contain it; with it off
    G'' decays monotonically at high frequency instead of turning up."""
    w = np.logspace(2, 6, 60)
    _, Gpp = tdd.Gstar(w, 40.0, 1.0, 1e6, rouse=False)
    slope = np.polyfit(np.log10(w), np.log10(Gpp), 1)[0]
    assert slope < 0, f"bare kernel should decay, got slope {slope:+.3f}"


def test_rouse_term_produces_the_high_frequency_rise():
    w = np.logspace(2, 6, 60)
    _, Gpp = tdd.Gstar(w, 40.0, 1.0, 1e6, rouse=True)
    slope = np.polyfit(np.log10(w), np.log10(Gpp), 1)[0]
    assert slope > 0.2, f"expected a Rouse rise, got slope {slope:+.3f}"


# --- scaling contracts ------------------------------------------------------

def test_Ge_is_a_pure_amplitude_scale():
    w = np.logspace(-4, 3, 40)
    a = tdd.Gstar(w, 20.0, 1.0, 1e5)
    b = tdd.Gstar(w, 20.0, 1.0, 1e6)
    assert np.allclose(b[0], 10 * a[0], rtol=1e-12)
    assert np.allclose(b[1], 10 * a[1], rtol=1e-12)


def test_tau_rep_is_a_pure_frequency_shift():
    """Doubling tau_rep must translate the curve on log w, nothing else."""
    w = np.logspace(-4, 3, 60)
    Gp1, Gpp1 = tdd.Gstar(w, 20.0, 1.0, 1e6)
    Gp2, Gpp2 = tdd.Gstar(w / 10.0, 20.0, 10.0, 1e6)
    assert np.allclose(Gp1, Gp2, rtol=1e-9)
    assert np.allclose(Gpp1, Gpp2, rtol=1e-9)


# --- the two properties this model was chosen FOR --------------------------

def test_is_exactly_deterministic():
    """The reason for the swap. `tube.Gstar` samples 20 chains and repeats
    are not bit-identical; this must be, or the L-BFGS-B gradients are
    differencing noise again."""
    w = np.logspace(-3, 3, 50)
    a = tdd.Gstar(w, 17.3, 2.5, 4e5)
    b = tdd.Gstar(w, 17.3, 2.5, 4e5)
    assert np.array_equal(a[0], b[0])
    assert np.array_equal(a[1], b[1])


def test_matches_direct_quadrature_of_the_exact_definition():
    """THE REFEREE. This is the test that caught the real bug.

    G'(w) = w int_0^inf G(t) sin(w t) dt is the definition, with no spectrum
    assumption anywhere. scipy's weight='sin' quadrature handles the
    oscillation analytically per cycle, so it is an independent ground truth
    for whatever the Prony ladder produces.

    An earlier finite-difference ladder passed every shape test above and was
    still 0.12-0.30 decades wrong here. Only G' is refereed: the companion
    cosine integral for G'' does not converge in this form (G(0) is finite),
    and forcing it overflows.
    """
    from scipy.integrate import quad

    Z, tau_rep, Ge = 20.0, 1.0, 1e6

    def Gt_scalar(t):
        return float(tdd.G_of_t(np.array([t]), Z, tau_rep, Ge)[0])

    for w in (1e-2, 1e-1, 1.0, 10.0, 100.0):
        ref, _ = quad(Gt_scalar, 0, np.inf, weight="sin", wvar=w, limit=400)
        ref *= w
        # rouse=False: the referee integrates G_of_t, which is the TDD kernel
        # alone. The Rouse modes are added OUTSIDE the ladder, analytically.
        got = tdd.Gstar(np.array([w]), Z, tau_rep, Ge, rouse=False)[0][0]
        assert abs(np.log10(got / ref)) < 5e-3, (
            f"w={w}: ladder {got:.6g} vs quadrature {ref:.6g}")


def test_prony_ladder_is_converged():
    """The ladder discretization must not be what sets accuracy. Doubling the
    modes may not move the answer by more than 1e-3 decades."""
    w = np.logspace(-4, 3, 60)
    Gp, Gpp = tdd.Gstar(w, 20.0, 1.0, 1e6, rouse=False)
    old_p, old_t = tdd.N_PRONY, tdd.N_TFIT
    try:
        tdd.N_PRONY, tdd.N_TFIT = 2 * old_p, 2 * old_t
        Gp2, Gpp2 = tdd.Gstar(w, 20.0, 1.0, 1e6, rouse=False)
    finally:
        tdd.N_PRONY, tdd.N_TFIT = old_p, old_t
    assert np.abs(np.log10(Gp / Gp2)).max() < 1e-3
    assert np.abs(np.log10(Gpp / Gpp2)).max() < 1e-3


def test_odd_mode_sum_is_converged():
    w = np.logspace(-4, 3, 60)
    Gp, Gpp = tdd.Gstar(w, 20.0, 1.0, 1e6, rouse=False)
    old = tdd._P_ODD
    try:
        tdd._P_ODD = np.arange(1, 401, 2)
        Gp2, Gpp2 = tdd.Gstar(w, 20.0, 1.0, 1e6, rouse=False)
    finally:
        tdd._P_ODD = old
    assert np.abs(np.log10(Gp / Gp2)).max() < 1e-3
    assert np.abs(np.log10(Gpp / Gpp2)).max() < 1e-3


def test_is_far_cheaper_than_the_tube_model():
    """The other reason for the swap, pinned so a future 'small' change that
    reintroduces a loop gets caught.

    HONEST NUMBER: this is ~8x, not the ~200x a first probe suggested. That
    probe used a finite-difference ladder which turned out to be WRONG (see
    `_prony_from_Gt`); the NNLS solve that replaced it is what costs the
    difference. 8x is still the difference between identify() at ~56 s and at
    ~10 s. The test asserts 4x so it fails on a real regression, not on the
    machine being busy.
    """
    import time
    from rheofp.models import tube

    w = np.logspace(-3, 3, 60)
    tdd.Gstar(w, 20.0, 1.0, 1e6)
    t0 = time.perf_counter()
    for _ in range(50):
        tdd.Gstar(w, 20.0, 1.0, 1e6)
    t_tdd = (time.perf_counter() - t0) / 50

    tube.Gstar(w, 20.0, 1e-4, 1e6, 1.0)
    t0 = time.perf_counter()
    for _ in range(5):
        tube.Gstar(w, 20.0, 1e-4, 1e6, 1.0)
    t_tube = (time.perf_counter() - t0) / 5

    assert t_tdd < t_tube / 4, f"tdd {t_tdd*1e3:.3f} ms vs tube {t_tube*1e3:.3f} ms"


# --- why this module is NOT in the bank ------------------------------------

def test_tdd_is_deliberately_not_in_the_identifier_bank():
    """PINS A DECISION, not a behaviour. See docs/tdd_preregistration.md.

    TDD-DR was built to replace `tube.py` as the shipped `reptation` because
    identify() spends 94.2% of its runtime in that one candidate. It was
    REJECTED on its own pre-registered criteria:

      P3 FAILED 2/3 - rms 0.0471/0.0383 against tube's 0.0315/0.0298 on
         Katzarova's two longer monodisperse polystyrenes (bar: +0.005 dec).
      P4 outcome (c) - it made the standing BSW fault WORSE, dAICc +147.7 and
         +87.6 against tube's +51.6 and +27.7.

    Freeing the fixed M*/Me (k=4) does beat BSW 3/3, and that is a TRAP: M*/Me
    pins to its bound at 60 (the paper's PS value is 8.7) and Z error blows out
    to +50%/+60% from +5%. Winning by flexibility while destroying the physical
    parameter is the `comb` veto exactly.

    If a future change wires `tdd` in, this test should fail and the
    pre-registration must be re-read first.
    """
    from rheofp.fitting import identify as ident

    assert "tdd" not in ident.ALL_MODELS
    forward = ident.ALL_MODELS["reptation"][0]
    assert forward.__name__ == "model_reptation_lm", (
        "the shipped `reptation` must remain the Likhtman-McLeish tube model")


def test_free_mstar_would_pin_to_its_bound():
    """The measured reason the k=4 escape hatch was refused: with M*/Me free,
    the optimum runs AWAY from the paper's PS value of 8.7 into the bound at
    60, which means the data does not identify it - it is absorbing misfit.

    That full finding needs the real Katzarova curves and lives in
    `scripts/check_tdd_vs_tube.py`. What is pinned HERE is its precondition:
    that M*/Me materially moves the curve. If it did not, freeing it could not
    have bought the rms it did, and the recorded diagnosis would be wrong.
    """
    w = np.logspace(-3, 3, 60)
    base = tdd.Gstar(w, 20.0, 1.0, 1e6)
    old = tdd.MSTAR_OVER_ME
    try:
        tdd.MSTAR_OVER_ME = 60.0
        alt = tdd.Gstar(w, 20.0, 1.0, 1e6)
    finally:
        tdd.MSTAR_OVER_ME = old
    shift = np.abs(np.log10(alt[0] / base[0])).max()
    assert shift > 0.1, (
        f"M*/Me barely moves the curve ({shift:.4f} dec) - if that were true, "
        "freeing it could not have bought the rms it did")
