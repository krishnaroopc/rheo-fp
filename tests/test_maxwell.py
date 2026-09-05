import numpy as np

from rheofp.models.maxwell import (
    maxwell_spectrum, wlm_spectrum, fit_maxwell, fit_wlm,
    sticky_maxwell_stack, fit_sticky_stack, branched_spectrum, fit_branched,
    bsw_spectrum, fit_bsw, model_branched, BRANCHED_MODELS,
    model_wormlike_micelle, WLM_MODELS,
)
from rheofp.io.data import load_npz

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


# --- BSW spectrum (branched / LCB melt class) -------------------------------

def test_bsw_spectrum_is_finite_positive_and_broad_in_the_terminal_zone():
    w = np.logspace(-3, 3, 80)
    Gp, Gpp = bsw_spectrum(w, 1e5, 10.0, 1e-2, 0.3, 0.6)
    assert np.all(np.isfinite(Gp)) and np.all(np.isfinite(Gpp))
    assert np.all(Gp > 0) and np.all(Gpp > 0)

    # The reason BSW exists: a broad relaxation SPECTRUM, not one relaxation
    # time. Many active modes keep G'' within a factor of ~2 of G' over a wide
    # frequency range; a single Maxwell mode only does so near its own 1/tau.
    lw = np.log10(w)

    def decades_loss_dominated(gp, gpp):
        m = (gpp / gp) > 0.5
        return np.ptp(lw[m]) if m.sum() > 2 else 0.0

    mx_gp, mx_gpp = maxwell_spectrum(w, [1e5], [10.0])
    assert decades_loss_dominated(Gp, Gpp) > 2 * decades_loss_dominated(mx_gp, mx_gpp)


def test_fit_bsw_recovers_planted_params():
    ref = dict(G_N=8e4, tau_max=50.0, tau_c=5e-2, n_e=0.30, n_g=0.55)
    w = np.logspace(-3, 3, 70)
    Gp, Gpp = bsw_spectrum(w, **ref)
    fit = fit_bsw(w, Gp, Gpp, n_restarts=48, seed=0)
    for k in ref:
        assert _rel(fit[k], ref[k]) < 0.05


def test_model_branched_matches_bsw_and_registry_shape():
    w = np.logspace(-2, 3, 50)
    theta = [np.log10(5e4), np.log10(20.0), np.log10(1e-3), 0.35, 0.55]
    a = model_branched(w, theta)
    b = bsw_spectrum(w, 5e4, 20.0, 1e-3, 0.35, 0.55)
    assert np.allclose(a[0], b[0]) and np.allclose(a[1], b[1])
    fwd, p0, bnds, k = BRANCHED_MODELS["branched"]
    assert k == 5 and len(p0) == 5 and len(bnds) == 5


def test_bsw_fits_real_ldpe_far_better_than_the_3param_branched_model():
    """The reason BSW exists: Pivokonsky (2006) E and B (real LDPE melts) that
    the 3-parameter branched_spectrum cannot represent."""
    d = load_npz("data/pivo2006.npz")
    for name, s in d.items():
        w, Gp, Gpp = s["omega"], s["Gp"], s["Gpp"]

        old = fit_branched(w, Gp, Gpp, n_restarts=24, seed=2)
        ogp, ogpp = branched_spectrum(w, old["Ge"], old["tau_b"], old["sigma"])
        old_rms = np.sqrt(np.mean(np.concatenate([
            (np.log10(ogp) - np.log10(Gp)) ** 2,
            (np.log10(ogpp) - np.log10(Gpp)) ** 2])))

        fit = fit_bsw(w, Gp, Gpp, n_restarts=48, seed=0)
        bgp, bgpp = bsw_spectrum(w, fit["G_N"], fit["tau_max"], fit["tau_c"],
                                 fit["n_e"], fit["n_g"])
        bsw_rms = np.sqrt(np.mean(np.concatenate([
            (np.log10(bgp) - np.log10(Gp)) ** 2,
            (np.log10(bgpp) - np.log10(Gpp)) ** 2])))

        assert bsw_rms < 0.10, f"{name}: BSW RMS {bsw_rms:.3f} dec"
        assert bsw_rms < 0.4 * old_rms, (
            f"{name}: BSW {bsw_rms:.3f} not much better than old {old_rms:.3f}")


def test_wlm_registry_entry_matches_the_bare_forward_model():
    w = np.logspace(-2, 3, 50)
    theta = [np.log10(30.0), np.log10(30.0), np.log10(0.03), 0.8]
    a = model_wormlike_micelle(w, theta)
    b = wlm_spectrum(w, 30.0, 30.0, 0.03, 0.8)
    assert np.allclose(a[0], b[0]) and np.allclose(a[1], b[1])
    fwd, p0, bnds, k = WLM_MODELS["wormlike_micelle"]
    assert k == 4 and len(p0) == 4 and len(bnds) == 4


def test_identify_can_actually_emit_wormlike_micelle():
    """Regression guard for the two-bank asymmetry.

    Before wormlike_micelle was registered, identify() answered a planted
    micellar curve with "branched" at Akaike weight ~1.0 and a ~0.05-decade
    residual - confidently wrong, and NOT flagged by the FLOOR_CHI2 floor,
    because BSW genuinely fits a near-single-Maxwell shape. A missing class
    shows up as a confident wrong answer, never as low confidence.
    """
    from rheofp.fitting.identify import identify, MODEL_ONLY_CLASSES
    from rheofp.data.synth import make_example

    rng = np.random.default_rng(5)
    hits = 0
    for _ in range(4):
        ex = make_example(rng, "wormlike_micelle", n_curves=1)
        w, Gp, Gpp, _ = ex["curves"][0]
        hits += identify(w, Gp, Gpp, n_restarts=8)["best"] == "wormlike_micelle"
    assert hits >= 3, f"only {hits}/4 planted micelles identified"
    assert "wormlike_micelle" in MODEL_ONLY_CLASSES


def test_identify_routes_real_ldpe_to_branched_and_reports_terminal_regime():
    """End-to-end: identify() now has a branched candidate that wins on the
    real LDPE melts instead of them defaulting to rouse_screened."""
    from rheofp.fitting.identify import identify, MODEL_ONLY_CLASSES
    d = load_npz("data/pivo2006.npz")
    for name, s in d.items():
        out = identify(s["omega"], s["Gp"], s["Gpp"])
        assert out["best"] == "branched", f"{name} -> {out['best']}"
        assert "branched" in MODEL_ONLY_CLASSES
        # model-only: the useful output is the regime, and it must be terminal
        assert out["ranking"][0]["name"] == "branched"
