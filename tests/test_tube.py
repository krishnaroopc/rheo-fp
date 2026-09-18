import numpy as np

from rheofp.models.maxwell import branched_spectrum, fit_branched
from rheofp.models.solutions import REP_BNDS, model_reptation_lm
from rheofp.models.tube import (
    HF_P_SPLIT, Z_of_sample, _early_term, _Gstar_hf_rouse, eps_star,
    linear_melt_forward, tau_R, valid_window,
)


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


# --- numerical-accuracy regressions (2026-09-17) ---------------------------
#
# Both of these pin a CLOSED FORM against the brute-force sum/integral it
# replaced. Neither was caught by the behavioural tests above, which is how the
# G" truncation below survived: every assertion here is on absolute accuracy,
# not on a slope or an ordering.


def test_early_term_matches_brute_force_quadrature():
    """eq-13 early term: closed form vs the 4000-point trapezoid it replaced.

    The old code integrated A eps^-1.25 exp(-eps t) on a fixed grid. The closed
    form is A t^0.25 Gamma(-1/4, es t). They must agree to the quadrature's own
    error, which is ~1e-5 relative at 4000 points.
    """
    Z, te = 20.0, 1e-5
    es = eps_star(Z, te)
    A = 0.306 / (Z * te**0.25)
    t = np.logspace(np.log10(1e-3 * te), np.log10(1e2), 40)

    epsg = np.logspace(np.log10(es), np.log10(es) + 13, 4000)
    wq = A * epsg**(-1.25)
    brute = np.array([np.trapezoid(wq * np.exp(-epsg * tt), epsg) for tt in t])

    got = _early_term(t, Z, te, es)
    big = brute > 1e-12 * brute.max()      # ignore where both have underflowed
    assert np.allclose(got[big], brute[big], rtol=2e-4)


def test_hf_rouse_tail_is_converged_where_a_plain_truncation_was_not():
    """The 3rd sum of eq 19 must include its tail, not stop at a cutoff.

    tau_p = tau_R/(2p^2) makes G"'s summand fall off only as 1/p^2, so the
    REMAINDER of the sum falls off as 1/P - slowly enough that the old
    p_max = sqrt(tau_R wmax / 2e-4) cutoff left ~3.9e-3 decades of G" on the
    table, and doubling that cutoff kept moving the answer. This pins the
    hybrid (partial sum + polygamma tail) against a reference long enough to
    be converged, in the worst corner: large tau_R, small Z.
    """
    Z, Ge = 2.0, 1e5
    te = 1e4 / (3.0 * Z**3)            # large tau_d -> the expensive corner
    w = np.logspace(-2, 3, 60)

    Zi = int(round(Z))
    tR = tau_R(Z, te)
    p = np.arange(Zi, 4_000_000, dtype=float)
    tau = tR / (2.0 * p**2)
    ref_Gp = np.array([(Ge / Z) * ((wi * tau)**2 / (1 + (wi * tau)**2)).sum()
                       for wi in w])
    ref_Gpp = np.array([(Ge / Z) * ((wi * tau) / (1 + (wi * tau)**2)).sum()
                        for wi in w])

    Gp, Gpp = _Gstar_hf_rouse(w, Z, te, Ge)
    assert np.max(np.abs(np.log10(Gp) - np.log10(ref_Gp))) < 1e-4
    assert np.max(np.abs(np.log10(Gpp) - np.log10(ref_Gpp))) < 1e-3

    # ...and the naive cutoff really is the thing that was wrong: summing only
    # to HF_P_SPLIT, with no tail, is more than an order of magnitude worse.
    p_cut = np.arange(Zi, HF_P_SPLIT + 1, dtype=float)
    tau_cut = tR / (2.0 * p_cut**2)
    cut_Gpp = np.array([(Ge / Z) * ((wi * tau_cut) / (1 + (wi * tau_cut)**2)).sum()
                        for wi in w])
    cut_err = np.max(np.abs(np.log10(cut_Gpp) - np.log10(ref_Gpp)))
    got_err = np.max(np.abs(np.log10(Gpp) - np.log10(ref_Gpp)))
    assert cut_err > 10 * got_err


def test_hf_rouse_is_finite_and_positive_across_the_fitting_bounds():
    """Every corner L-BFGS-B can reach must give finite, positive moduli.

    The fitter walks the whole of REP_BNDS, including corners no real melt
    occupies, and a NaN or a negative modulus there poisons the objective
    rather than merely costing accuracy.

    This caught a real regression: with a FIXED split point, the closed-form
    tail was applied where its small parameter was not small (Z = 2 with
    tau_d = 1e5 s puts w tau_R/2 at ~8e6, so w tau_p is still ~2 at p = 2000).
    The alternating series then diverges and G' overshoots NEGATIVE. The split
    is now raised until w tau_P <= HF_TAIL_WT, which is what makes the
    expansion legitimate rather than merely cheap.
    """
    w = np.logspace(-2, 3, 60)
    (lGe_lo, lGe_hi), (ltd_lo, ltd_hi), (Z_lo, Z_hi) = REP_BNDS
    for lGe in (lGe_lo, 3.0, lGe_hi):
        for ltd in (ltd_lo, 1.0, ltd_hi):
            for Z in (Z_lo, 2.5, 20.0, Z_hi):
                Gp, Gpp = model_reptation_lm(w, [lGe, ltd, Z])
                where = f"lGe={lGe} ltau_d={ltd} Z={Z}"
                assert np.all(np.isfinite(Gp)), f"non-finite G' at {where}"
                assert np.all(np.isfinite(Gpp)), f"non-finite G\" at {where}"
                assert np.all(Gp > 0), f"non-positive G' at {where}"
                assert np.all(Gpp > 0), f"non-positive G\" at {where}"
