import numpy as np

from rheofp.models.maxwell import branched_spectrum, fit_branched
from rheofp.models.tube import Z_of_sample, linear_melt_forward, valid_window


def _rel(a, b):
    return abs(a - b) / abs(b)


def test_linear_melt_terminal_slopes_are_physical():
    Ge, te, Mw = 2.0e5, 1e-3, 300_000.0
    omega_full = np.logspace(-4, 1, 80)
    Gp, Gpp = linear_melt_forward(omega_full, Ge, te, Mw, nchains=60, rng=np.random.default_rng(0))
    lo = omega_full < 1e-2
    sGp = np.polyfit(np.log(omega_full[lo]), np.log(Gp[lo]), 1)[0]
    sGpp = np.polyfit(np.log(omega_full[lo]), np.log(Gpp[lo]), 1)[0]
    assert 1.6 < sGp < 2.3
    assert 0.7 < sGpp < 1.2


def test_linear_melt_valid_window_stays_below_plateau():
    Ge, te, Mw = 2.0e5, 1e-3, 300_000.0
    wlo, whi = valid_window(Ge, te, Mw)
    omega_valid = np.logspace(np.log10(wlo), np.log10(whi), 120)
    _, Gppv = linear_melt_forward(omega_valid, Ge, te, Mw, nchains=80, rng=np.random.default_rng(1))
    assert Gppv.max() < Ge


def test_branched_recovers_planted_params_and_reaches_plateau():
    ref = dict(Ge=1.0e5, tau_b=10.0, sigma=2.5)
    omega = np.logspace(-5, 3, 110)
    Gp, Gpp = branched_spectrum(omega, ref["Ge"], ref["tau_b"], ref["sigma"])
    fit = fit_branched(omega, Gp, Gpp, n_restarts=20, seed=2)
    assert _rel(fit["Ge"], ref["Ge"]) < 0.05
    assert _rel(fit["tau_b"], ref["tau_b"]) < 0.15
    assert _rel(fit["sigma"], ref["sigma"]) < 0.15
    assert Gp.max() / ref["Ge"] > 0.9


def test_branched_more_loss_dominated_than_linear_in_valid_window():
    Ge, te, Mw = 2.0e5, 1e-3, 300_000.0
    wlo, whi = valid_window(Ge, te, Mw)
    omega = np.logspace(np.log10(wlo), np.log10(whi), 200)
    Gp_lin, Gpp_lin = linear_melt_forward(omega, Ge, te, Mw, nchains=80, rng=np.random.default_rng(1))
    tau_term = 1.0 / omega[np.argmax(Gpp_lin)]
    Gp_br, Gpp_br = branched_spectrum(omega, Ge, tau_term, sigma=2.5)

    def td_span(omega, Gp, Gpp):
        td = Gpp / np.maximum(Gp, 1e-300)
        r = omega[td > 1.0]
        return np.log10(r.max() / r.min()) if len(r) > 2 else 0.0

    s_lin = td_span(omega, Gp_lin, Gpp_lin)
    s_br = td_span(omega, Gp_br, Gpp_br)
    assert s_br > s_lin
    assert Gpp_lin.max() < Ge
    assert Gpp_br.max() < Ge


def test_z_of_sample_is_positive():
    assert Z_of_sample(300_000.0, 2.0e5) > 0
