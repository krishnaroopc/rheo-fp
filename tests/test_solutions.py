import numpy as np
import pytest

from rheofp.models.solutions import MODELS
from rheofp.fitting.identify import identify

TRUTH = {
    "zimm": [2.0, 0.5, 30],
    "rouse_screened": [2.5, 0.5, 40],
    "reptation": [3.5, 2.0, 25],
    "sticky_rouse": [3.0, 2.0, -1.0, 30],
    "sticky_reptation": [3.5, 4.0, 20, 1.5],
}


@pytest.mark.parametrize("true_name,theta", list(TRUTH.items()))
def test_identify_recovers_planted_regime(true_name, theta):
    w = np.logspace(-3, 4, 60)
    Gp, Gpp = MODELS[true_name][0](w, np.array(theta, float))
    out = identify(w, Gp, Gpp)
    assert out["best"] == true_name


@pytest.mark.parametrize("name", list(MODELS.keys()))
def test_model_forward_is_finite_and_nonnegative(name):
    w = np.logspace(-3, 4, 60)
    forward, p0, _bounds, _k = MODELS[name]
    Gp, Gpp = forward(w, np.array(p0, float))
    assert np.all(np.isfinite(Gp)) and np.all(np.isfinite(Gpp))
    assert np.all(Gp >= 0) and np.all(Gpp >= 0)


def test_a_sub_noise_rms_change_can_still_move_the_AICc_decision():
    """PINS THE 2026-09-19 RESTART FINDING, which is a trap for any future
    speed or approximation work. See docs/per_model_restarts_preregistration.md.

    Cutting `reptation`'s restarts from 12 to 4 changes its rms by ~1e-3
    decades - an ORDER OF MAGNITUDE BELOW tube.py's own 1.3e-2 sampling noise,
    and on the three real Katzarova melts by exactly zero. By any fit-quality
    measure the search is converged.

    It is not. Scored on the full identify() winner and margin, that same
    sub-noise difference produced a FLIPPED WINNER (1 of 8 planted reptation
    curves, star -> branched) and moved dAICc margins by up to 32.6 units.

    The lesson, and the reason this test exists: **an approximation validated
    on rms can still move the reported class.** Score the winner and the
    margin, never the residual. A cheap check that looks at rms alone will
    certify a change that silently reclassifies material.

    This test does not re-run that measurement (it costs minutes per curve).
    It pins the ARITHMETIC that makes it possible: AICc is n*log(sse/n), so
    d(AICc) = n * d(log sse), and with n = 2*60 points a 1e-3 relative change
    in sse moves AICc by ~0.12 units per point-pair - i.e. tens of units once
    the residual itself shifts by a few tenths of a percent.
    """
    n_pts = 60
    n_data = 2 * n_pts
    rms_a, rms_b = 0.02093, 0.02123          # measured: planted curve 0, @12 vs @4
    sse_a, sse_b = rms_a**2 * n_data, rms_b**2 * n_data
    d_aicc = n_data * (np.log(sse_b / n_data) - np.log(sse_a / n_data))

    # a 0.14% rms change is worth several AICc units on its own...
    assert abs(rms_b - rms_a) / rms_a < 0.02, "this is a sub-2% rms change"
    assert abs(d_aicc) > 1.0, (
        f"a sub-noise rms change moves AICc by {d_aicc:.2f} units - if this "
        "ever drops below 1.0 the pipeline's sensitivity has changed and the "
        "restart finding should be re-measured")
