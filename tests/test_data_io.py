import numpy as np
import pandas as pd
import pytest

from rheofp.io.data import load_xlsx, save_npz, load_npz


@pytest.fixture
def sample_xlsx(tmp_path):
    omega = np.logspace(-2, 2, 20)
    Gp = omega**2 / (1 + omega**2) * 1000
    Gpp = omega / (1 + omega**2) * 1000
    df = pd.DataFrame({
        "omega": omega,
        "Sample1 G' (Pa)": Gp,
        "Sample1 G'' (Pa)": Gpp,
    })
    path = tmp_path / "test_data.xlsx"
    df.to_excel(path, sheet_name="Sheet1", index=False)
    return path, omega, Gp, Gpp


def test_load_xlsx_parses_sample_and_convention_columns(sample_xlsx):
    path, omega, Gp, Gpp = sample_xlsx
    data = load_xlsx(path)
    assert list(data.keys()) == ["Sample1"]
    np.testing.assert_allclose(data["Sample1"]["omega"], omega)
    np.testing.assert_allclose(data["Sample1"]["Gp"], Gp)
    np.testing.assert_allclose(data["Sample1"]["Gpp"], Gpp)


def test_load_xlsx_omega_hz_conversion(sample_xlsx):
    path, omega, Gp, Gpp = sample_xlsx
    data = load_xlsx(path, omega_hz=True)
    np.testing.assert_allclose(data["Sample1"]["omega"], omega * 2 * np.pi)


def test_npz_roundtrip_is_exact(tmp_path):
    dataset = {
        "A": dict(omega=np.array([1.0, 2.0, 3.0]), Gp=np.array([10.0, 20.0, 30.0]),
                  Gpp=np.array([1.0, 2.0, 3.0]), T_K=298.15, conc=0.05),
    }
    path = tmp_path / "roundtrip.npz"
    save_npz(path, dataset)
    loaded = load_npz(path)
    assert set(loaded.keys()) == {"A"}
    np.testing.assert_allclose(loaded["A"]["omega"], dataset["A"]["omega"])
    np.testing.assert_allclose(loaded["A"]["Gp"], dataset["A"]["Gp"])
    np.testing.assert_allclose(loaded["A"]["Gpp"], dataset["A"]["Gpp"])
