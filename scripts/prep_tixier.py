"""Convert the digitized Tixier et al. (2004) critical-gel SAOS data to .npz.

Source: Tixier, Tordjeman, Cohen-Solal & Mutin (2004), J. Rheol. 48(1), 39,
Fig. 2/4 - a near-sol-gel-threshold end-linked PDMS network, native SAOS
G'(omega) / G''(omega). At/near the gel point G' and G'' are parallel power
laws in omega with a frequency-independent loss tangent tan(delta) =
tan(pi u / 2); Tixier measures u = 0.69-0.75 (NOT the universal 1/2 - u
varies with crosslinker functionality / Mn, their Table II).

Digitized by hand (WebPlotDigitizer / engauge) into originals/tixier.xlsx
(gitignored, per-machine). Moduli in that sheet are already in Pa, so no unit
conversion here (unlike prep_darby.py). The digitized curve has power-law
slopes ~0.75 for both G' and G'' and tan(delta) ~ 2.5 flat across the window,
consistent with Tixier's system III (u_III = 0.75).

Output data/tixier2004.npz IS committed so the validation runs without the
gitignored original. Re-run after re-digitizing:  python scripts/prep_tixier.py
"""
import os

import numpy as np
import pandas as pd

from rheofp.io.data import save_npz

OUT_NPZ = "data/tixier2004.npz"
SRC_CANDIDATES = ["originals/tixier.xlsx", "originals/tixier.ods"]

# single digitized curve; keyed to match its measured exponent
SAMPLE_NAME = "Tixier2004_gel"


def _find_source():
    for path in SRC_CANDIDATES:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        f"no Tixier source spreadsheet found. Expected one of {SRC_CANDIDATES}."
    )


def main():
    src = _find_source()
    print(f"reading {src}")
    df = pd.read_excel(src)
    omega = df.iloc[:, 0].to_numpy(float)
    gp = df.iloc[:, 1].to_numpy(float)   # already Pa
    gpp = df.iloc[:, 2].to_numpy(float)  # already Pa

    mask = np.isfinite(omega) & np.isfinite(gp) & np.isfinite(gpp) & (omega > 0)
    order = np.argsort(omega[mask])
    dataset = {SAMPLE_NAME: dict(
        omega=omega[mask][order],
        Gp=gp[mask][order],
        Gpp=gpp[mask][order],
        T_K=np.nan,
        conc=np.nan,
    )}

    w = dataset[SAMPLE_NAME]["omega"]
    gpv, gppv = dataset[SAMPLE_NAME]["Gp"], dataset[SAMPLE_NAME]["Gpp"]
    slope_gp = np.polyfit(np.log10(w), np.log10(gpv), 1)[0]
    slope_gpp = np.polyfit(np.log10(w), np.log10(gppv), 1)[0]
    print(f"{SAMPLE_NAME}: {len(w)} pts  omega {w.min():.3g}-{w.max():.3g} rad/s")
    print(f"  power-law slopes  G' {slope_gp:.3f}  G'' {slope_gpp:.3f}  "
          f"(parallel -> critical gel)")
    print(f"  tan(delta) {np.median(gppv / gpv):.2f} (median), "
          f"spread {np.ptp(np.log10(gppv / gpv)):.3f} decades")

    save_npz(OUT_NPZ, dataset)
    print(f"wrote {OUT_NPZ}")


if __name__ == "__main__":
    main()
