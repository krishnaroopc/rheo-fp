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
