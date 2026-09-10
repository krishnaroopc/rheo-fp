"""Convert the digitized Milner & McLeish (1998) four-arm PI star data to .npz.

Source: Milner & McLeish (1998), Macromolecules 31, 7479
(doi:10.1021/ma980060d), Figures 1 (G'') and 2 (G'). SEVEN monodisperse
FOUR-ARM polyisoprene star melts, time-temperature superposed to 25 C, with
arm molecular weights Ma from 11 400 to 105 000. Me = 5000 g/mol (the value
ref 5 and this paper both use for PI), so Z = Ma/Me spans ~2.3 to 21.

The underlying measurements are Fetters, Kiss, Pearson, Quack & Vitus (1993),
Macromolecules 26, 647 (doi:10.1021/ma00056a015); MM1998 replots them as
master curves and fits them with the Milner-McLeish theory. So this is the
theory's OWN validation set, which is exactly why it is the right test of
rheofp's transcription of it: MM report excellent agreement at all seven arm
lengths with no adjustable parameters, so a correct implementation must
recover Z here.

WHY THIS DATASET, GIVEN SANTANGELO ALREADY EXISTS. It supplies the one thing
Santangelo 1999 lacks - a RESOLVED TERMINAL ZONE. Measured low-frequency
slopes here are G' ~ 1.9-2.0 and G'' ~ 0.9-1.0, i.e. the omega^2 / omega^1
melt limit, for six of the seven curves. Santangelo's are 1.1 / 0.55 because
its window stops before its (polydisperse) samples flow, and `Z` - the
spectrum-WIDTH parameter - then absorbs the truncation and inflates 6-8x.
See scripts/prep_santangelo.py and next-actions for that negative result.
Curve 1 (Ma = 105k, the longest arm) is the exception at 1.61/0.80: its
terminal sits at the very edge of the window, so treat its Z as the least
trustworthy of the seven.

COLUMN ORDER IS REVERSED RELATIVE TO THE CAPTION - the trap here. Figure 1's
caption lists 10^-3 Ma = 11.4, 17, 36.7, 44, 47.5, 95, 105 "in order of
increasing terminal time". Increasing terminal time means the terminal moves
to LOWER frequency, so the LEFTMOST curve is the LARGEST arm. The
spreadsheet's w1/gp1 is the leftmost curve, hence Ma = 105k, and the caption's
list must be read backwards. Verified from the data rather than assumed: the
G'' terminal peak moves monotonically 0.32 -> 21.9 rad/s from curve 1 to
curve 7 (2026-09-09).

UNITS. The paper's ordinates are log G in dyn/cm^2, and the digitized values
are in those units (curve plateaus land at 3.1-4.2e6 dyn/cm^2 = 310-420 kPa,
matching PI's known plateau modulus ~0.4 MPa; read as Pa they would be
3-4 MPa, an order of magnitude too stiff). Converted here by x0.1 -> Pa.
Abscissa is log omega in s^-1, already rad/s.

G' and G'' were digitized independently (different point counts and omega
values), but save_npz stores ONE omega per sample, so both are interpolated
onto a common per-sample log grid over their overlap - linear in log-log,
exact for power-law segments, the same choice ml/dataset.resample_log_grid
makes.

Output data/mm1998.npz IS committed so validation runs without the gitignored
original.  Re-run after re-digitizing:
    uv run python scripts/prep_mm1998.py
"""
import os

import numpy as np
import pandas as pd

from rheofp.io.data import save_npz

OUT_NPZ = "data/mm1998.npz"
SRC = "originals/mm1998.xlsx"

DYN_CM2_TO_PA = 0.1
TREF_C = 25.0
TREF_K = TREF_C + 273.15

# Me for PI as used by both MM1998 and Fetters 1993.
ME_PI = 5000.0

# Curve index (left to right on the figures) -> arm molecular weight.
# REVERSED from the caption's list; see the module docstring.
MA_BY_CURVE = {1: 105000.0, 2: 95000.0, 3: 47500.0, 4: 44000.0,
               5: 36700.0, 6: 17000.0, 7: 11400.0}

N_GRID = 60


def _curve(df, i, kind):
    col_w, col_g = f"w{i}", f"{kind}{i}"
    if col_w not in df.columns or col_g not in df.columns:
        raise KeyError(f"missing column {col_w!r}/{col_g!r} in sheet {kind!r}")
    d = df[[col_w, col_g]].apply(pd.to_numeric, errors="coerce").dropna()
    w = d[col_w].to_numpy(float)
    g = d[col_g].to_numpy(float)
    keep = np.isfinite(w) & np.isfinite(g) & (w > 0) & (g > 0)
    w, g = w[keep], g[keep]
    order = np.argsort(w)
    return w[order], g[order]


def _common_grid(w_gp, gp, w_gpp, gpp, n=N_GRID):
    lo = max(w_gp.min(), w_gpp.min())
    hi = min(w_gp.max(), w_gpp.max())
    if not (hi > lo):
        raise ValueError("G' and G'' windows do not overlap")
    grid = np.logspace(np.log10(lo), np.log10(hi), n)
    interp = lambda w, g: 10.0 ** np.interp(
        np.log10(grid), np.log10(w), np.log10(g))
    return grid, interp(w_gp, gp), interp(w_gpp, gpp)


def main():
    if not os.path.exists(SRC):
        raise FileNotFoundError(
            f"{SRC} not found. It is gitignored/per-machine; "
            f"{OUT_NPZ} is committed so validation runs without it.")
    print(f"reading {SRC}")
    gp_sheet = pd.read_excel(SRC, sheet_name="gp")
    gpp_sheet = pd.read_excel(SRC, sheet_name="gpp")

    dataset = {}
    for i in sorted(MA_BY_CURVE):
        ma = MA_BY_CURVE[i]
        w_gp, gp = _curve(gp_sheet, i, "gp")
        w_gpp, gpp = _curve(gpp_sheet, i, "gpp")
        grid, gp_i, gpp_i = _common_grid(w_gp, gp, w_gpp, gpp)

        z = ma / ME_PI
        name = f"PI4_Ma{int(ma / 1000)}k"
        dataset[name] = dict(
            omega=grid,                          # rad/s (a_T * omega, Tref 25C)
            Gp=gp_i * DYN_CM2_TO_PA,             # Pa
            Gpp=gpp_i * DYN_CM2_TO_PA,
            T_K=TREF_K,
            conc=np.nan,                         # melt
        )

        k = min(10, len(grid) // 4)
        s_gp = np.polyfit(np.log10(grid[:k]), np.log10(gp_i[:k]), 1)[0]
        s_gpp = np.polyfit(np.log10(grid[:k]), np.log10(gpp_i[:k]), 1)[0]
        print(f"{name}: 4-arm star, Ma={ma:.0f}, Z=Ma/Me={z:.2f}")
        print(f"  G' {len(w_gp):3d} pts  G'' {len(w_gpp):3d} pts "
              f"-> {len(grid)} on a common grid; "
              f"omega {grid.min():.3g}-{grid.max():.3g} rad/s "
              f"({np.log10(grid.max() / grid.min()):.2f} dec)")
        print(f"  terminal slopes  G' {s_gp:.2f}  G'' {s_gpp:.2f} "
              f"(melt limit 2.0 / 1.0)")
        print(f"  plateau G' max {gp_i.max() * DYN_CM2_TO_PA / 1e3:.0f} kPa")

    save_npz(OUT_NPZ, dataset)
    print(f"wrote {OUT_NPZ}  ({len(dataset)} samples)")
    print("Z = Ma/Me is the independently known ground truth for fit_star; "
          "the number of ARMS (4) is not recoverable from LVE and must not be "
          "claimed - see rheofp/models/star.py.")


if __name__ == "__main__":
    main()
