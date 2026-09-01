import numpy as np
import pytest

from rheofp.io.data import load_npz
from rheofp.models.maxwell import maxwell_spectrum
from rheofp.models.network import (
    chasset_thirion_spectrum, critical_gel_spectrum,
    fit_chasset_thirion, fit_critical_gel, tan_delta_spread,
)
from rheofp.fitting.identify import identify, signature_features, NETWORK_CLASSES

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
