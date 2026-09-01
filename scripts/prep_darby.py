"""Convert the digitized Darby et al. (2022) silicone SAOS data to .npz.

Source: Darby, Cai, Mason & Pham (2022), J. Appl. Polym. Sci. 139, e52412,
Figure 1a - overlaid G'(omega) / G''(omega) for Sylgard 184 (10:1), Solaris
(1:1), and Ecoflex 00-30 (1:1) at factory-recommended mixing ratios,
0.1-100 rad/s, room temperature, LVE (0.1% strain).

The paper does not share data ("Research data are not shared"), so the curves
were digitized by hand from Fig. 1a (WebPlotDigitizer) into originals/darby.ods
(gitignored, per-machine). This script is the single conversion point:

  * modulus columns in the spreadsheet are in kPa; this script multiplies by
    1000 to store Pa (the repo-wide convention - see rheofp/io/data.py);
  * output is data/darby2022.npz in the canonical save_npz layout, which IS
    committed so the validation runs without the gitignored original.

pandas needs `odfpy` to read .ods and it is not in the locked env (this is a
one-off prep step, not a shipped path). If only the .ods is present, convert
it once:  libreoffice --headless --convert-to xlsx originals/darby.ods

Re-run after any re-digitizing:  python scripts/prep_darby.py
"""
import os

import numpy as np
import pandas as pd

from rheofp.io.data import save_npz

OUT_NPZ = "data/darby2022.npz"
KPA_TO_PA = 1000.0

# .xlsx preferred (readable with the locked openpyxl); .ods only if odfpy is
# somehow available.
SRC_CANDIDATES = ["originals/darby.xlsx", "originals/darby.ods"]

# spreadsheet column prefix -> canonical sample name (mixing ratio kept in the
# name; all three are the factory-recommended ratio for that kit)
SAMPLES = {
    "Sy": "SY184_10-1",
    "So": "Solaris_1-1",
    "Ec": "EF0030_1-1",
}


def _find_source():
    for path in SRC_CANDIDATES:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        "no Darby source spreadsheet found. Expected one of "
        f"{SRC_CANDIDATES}. If you have darby.ods only, run:\n"
        "  libreoffice --headless --convert-to xlsx originals/darby.ods"
    )


def main():
    src = _find_source()
    print(f"reading {src}")
    df = pd.read_excel(src)
    # first column is omega in rad/s; the digitized header uses curly quotes
    # and a "<prefix> G'/G''" layout rather than the strict io.data convention,
    # so map columns positionally by prefix instead of via load_xlsx().
    omega = df.iloc[:, 0].to_numpy(float)
    cols = list(df.columns[1:])

    dataset = {}
    for prefix, name in SAMPLES.items():
        gp_col = next(c for c in cols if c.startswith(prefix) and "’’" not in c and "''" not in c)
        gpp_col = next(c for c in cols if c.startswith(prefix) and ("’’" in c or "''" in c))
        gp = df[gp_col].to_numpy(float) * KPA_TO_PA
        gpp = df[gpp_col].to_numpy(float) * KPA_TO_PA

        mask = np.isfinite(omega) & np.isfinite(gp) & np.isfinite(gpp) & (omega > 0)
        order = np.argsort(omega[mask])
        dataset[name] = dict(
            omega=omega[mask][order],
            Gp=gp[mask][order],
            Gpp=gpp[mask][order],
            T_K=np.nan,   # Darby does not state the rheometry temperature
            conc=np.nan,
        )
        w = dataset[name]["omega"]
        g = dataset[name]["Gp"]
        print(f"{name:14s} {len(w):2d} pts  omega {w.min():.3g}-{w.max():.3g} rad/s  "
              f"G' {g.min()/1e3:.1f}-{g.max()/1e3:.1f} kPa")

    save_npz(OUT_NPZ, dataset)
    print(f"wrote {OUT_NPZ}")


if __name__ == "__main__":
    main()
