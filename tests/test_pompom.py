import numpy as np
import pytest

from rheofp.io.data import load_npz
from rheofp.models.maxwell import maxwell_spectrum, fit_maxwell
from rheofp.models.pompom import build_xpp_table

# Published nonlinear params (Pivokonsky et al. 2006, Tables 2/3): lambda_b/lambda_s, q.
NONLINEAR = {
    "E": [(2.4, 1), (2.2, 1), (2.2, 2), (1.8, 3), (1.8, 4),
          (1.3, 5), (1.3, 6), (1.3, 6), (1.2, 6), (1.2, 7)],
    "B": [(3.4, 1), (2.8, 1), (2.6, 2), (1.8, 3), (1.8, 5),
          (1.3, 7), (1.3, 8), (1.2, 8), (1.1, 9), (1.1, 9)],
}
DECADE_TOL = 0.10


@pytest.mark.parametrize("sample", ["E", "B"])
def test_fit_maxwell_recovers_real_ldpe_spectrum(sample):
    d = load_npz("data/pivo2006.npz")[sample]
    omega, Gp_data, Gpp_data = d["omega"], d["Gp"], d["Gpp"]

    fit = fit_maxwell(omega, Gp_data, Gpp_data, n_modes=10, n_restarts=12, seed=42)
    assert fit["success"]

    Gp_fit, Gpp_fit = maxwell_spectrum(omega, fit["G"], fit["tau"])
    err_gp = np.abs(np.log10(Gp_fit) - np.log10(Gp_data)).mean()
    err_gpp = np.abs(np.log10(Gpp_fit) - np.log10(Gpp_data)).mean()
    assert max(err_gp, err_gpp) < DECADE_TOL


@pytest.mark.parametrize("sample", ["E", "B"])
def test_build_xpp_table_assembles_published_nonlinear_params(sample):
    ratio, q = zip(*NONLINEAR[sample])
    n_modes = len(q)
    g_fit = np.linspace(1, 2, n_modes)
    tau_fit = np.logspace(-3, 3, n_modes)

    rows = build_xpp_table(sample, g_fit, tau_fit, use_published=True,
                            pub_q=np.array(q), pub_ratio=np.array(ratio),
                            pub_alpha=0.5 / np.array(q, float))

    assert len(rows) == n_modes
    for i, row in enumerate(rows):
        assert row["q_i"] == q[i]
        assert row["tau_0b/tau_0s"] == ratio[i]
        assert row["tau_0s_i (s)"] == pytest.approx(tau_fit[i] / ratio[i])
        assert row["alpha_i"] == pytest.approx(0.5 / q[i])
