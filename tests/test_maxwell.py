import numpy as np

from rheofp.models.maxwell import (
    maxwell_spectrum, wlm_spectrum, fit_maxwell, fit_wlm,
    sticky_maxwell_stack, fit_sticky_stack, branched_spectrum, fit_branched,
)

OMEGA = np.logspace(-2, 3, int((3 - (-2)) * 12) + 1)


def _rel(a, b):
    return abs(a - b) / abs(b)


def test_fit_maxwell_single_mode_recovers_planted_params():
    Gp, Gpp = maxwell_spectrum(OMEGA, [1000.0], [0.5])
    fit = fit_maxwell(OMEGA, Gp, Gpp, n_modes=1)
    assert _rel(fit["G"][0], 1000.0) < 1e-3
    assert _rel(fit["tau"][0], 0.5) < 1e-3


def test_fit_maxwell_three_mode_prony_recovers_planted_params():
    G3, t3 = np.array([2000.0, 500.0, 80.0]), np.array([0.01, 0.3, 5.0])
    Gp3, Gpp3 = maxwell_spectrum(OMEGA, G3, t3)
    fit = fit_maxwell(OMEGA, Gp3, Gpp3, n_modes=3, n_restarts=30, seed=3)
    for i in range(3):
        assert _rel(fit["G"][i], G3[i]) < 1e-2
        assert _rel(fit["tau"][i], t3[i]) < 1e-2


def test_fit_wlm_recovers_planted_params():
    wp = dict(G0=30.0, tau_rep=30.0, tau_br=0.03, beta=0.8)
    Gp_w, Gpp_w = wlm_spectrum(OMEGA, wp["G0"], wp["tau_rep"], wp["tau_br"], wp["beta"])
    fit = fit_wlm(OMEGA, Gp_w, Gpp_w, n_restarts=20)
    tau_dom = np.sqrt(wp["tau_rep"] * wp["tau_br"])
    assert _rel(fit["G0"], wp["G0"]) < 1e-2
    assert _rel(fit["tau"], tau_dom) < 1e-2


def test_fit_sticky_stack_recovers_planted_params():
    sp = dict(G=[5000.0], tau_ref=[1.0], Ea=60e3, T_ref=298.15,
              T_list=[278.15, 288.15, 298.15, 308.15, 318.15])
    stack = sticky_maxwell_stack(OMEGA, sp["G"], sp["tau_ref"], sp["Ea"], sp["T_list"], sp["T_ref"])
    sGp = [s[0] for s in stack]
    sGpp = [s[1] for s in stack]
    fit = fit_sticky_stack(OMEGA, sGp, sGpp, sp["T_list"], sp["T_ref"], n_modes=1)
    assert _rel(fit["G"][0], sp["G"][0]) < 1e-2
    assert _rel(fit["Ea"], sp["Ea"]) < 1e-2


def test_fit_branched_recovers_planted_params_and_reaches_plateau():
    ref = dict(Ge=1.0e5, tau_b=10.0, sigma=2.5)
    omega = np.logspace(-5, 3, 110)
    Gp, Gpp = branched_spectrum(omega, ref["Ge"], ref["tau_b"], ref["sigma"])
    fit = fit_branched(omega, Gp, Gpp, n_restarts=20, seed=2)
    assert _rel(fit["Ge"], ref["Ge"]) < 0.05
    assert _rel(fit["tau_b"], ref["tau_b"]) < 0.15
    assert _rel(fit["sigma"], ref["sigma"]) < 0.15
    assert Gp.max() / ref["Ge"] > 0.9
