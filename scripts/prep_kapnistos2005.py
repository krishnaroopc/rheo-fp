"""Convert the digitized Kapnistos et al. (2005) comb data to .npz.

Source: Kapnistos, Vlassopoulos, Roovers & Leal (2005), Macromolecules 38,
7852-7862 (doi:10.1021/ma050644x), Figures 1a and 2a - master curves for model
comb homopolymers with LINEAR backbones and grafted linear branches.

    Figure 1a  polystyrene,   backbone M_b = 275 kg/mol, T_ref = 170 C
    Figure 2a  1,4-polybutadiene, backbone M_b = 50 kg/mol, T_ref = 0 C

This is the first real COMB dataset in the project. `rheofp/models/comb.py`
has until now been validated only against ML1999's own figures and planted
parameters; the class is deliberately NOT in `identify()`'s bank because
wiring it in cost `star` real-data accuracy (MM1998 5/7 -> 4/7). This dataset
exists to decide that question on evidence. Predictions were pre-registered in
docs/kapnistos2005_preregistration.md BEFORE anything was fitted - score
against that file, not against hindsight.

WHY THIS DATASET. Every parameter `fit_comb` estimates except tau_e is
INDEPENDENTLY KNOWN here from Table 1's molecular weights:
    s_a   = M_a / M_e        entanglements per arm
    s_b   = M_b / M_e        entanglements along the cross-bar
    phi_b = s_b / (s_b + q s_a)   cross-bar volume fraction
That is a far stronger test than a curve-shape match, and it is the same
property that made MM1998 the right test of `star`.

M_e and T_ref are the paper's own, page 7853: M_e = 17 000 g/mol (PS) and
1815 g/mol (PBd), both flagged there as "typical literature values" (refs
20,21), not measured in this work; T_ref = 170 C (PS), 0 C (PBd), from the WLF
paragraph in the right-hand column. NOTE the paper defines
M_e = (4/5)[rho(T) R T / G_N(T)] (page 7855, right column) - the 4/5
convention. s_a and s_b are entanglement COUNTS, so a mismatched convention
would propagate straight into the predictions above.

>>> TWO DEFECTS IN THE DIGITIZED SHEET, CORRECTED HERE <<<

Both were found by plotting before fitting (2026-09-16) and are corrected in
code so that originals/kapnistos2005.xlsx stays exactly as digitized and the
correction stays auditable. Neither is a digitizing error to be re-done.

(1) **Fig1a's G' and G'' columns are SWAPPED; Fig2a's are not.** As labelled,
    every Fig1a sample gives low-frequency slopes G' ~ 1.0 / G'' ~ 2.0, which
    is the terminal law backwards. Swapped, all six read G' 1.95-2.15 and
    G'' 0.77-1.09. Fig2a as labelled already reads G' 1.35-1.50 /
    G'' 0.86-1.00, and has G'' > G' throughout, matching the printed figure.
    So the swap is applied to Fig1a ONLY - see SWAP_GP_GPP below.

(2) **The caption's decade shifts are DESCENDING, and it lists one too few.**
    Figure 1's caption says "multiplied by 1, 10, 10^2, 10^3, and 10^4" naming
    c6bb first, but c6bb is the HIGHEST curve in the panel and the caption
    gives five factors for six samples. The ladder that actually collapses the
    data is 1e5 down to 1 (c6bb -> c652). Figure 2 is likewise 1e2 down to 1.

    The independent check, which the shift fit never saw: after unshifting,
    the plateau modulus read at the tan-delta minimum lands at

        PS   1.94, 1.95, 2.43, 3.12, 6.16, 1.98 x 1e5 Pa   (lit. 2.0e5)
        PBd  1.09, 1.10, 1.26 x 1e6 Pa                     (lit. 1.15e6)

    Four of six PS and all three PBd within ~10% of a literature value that is
    not in the fit. c642-PS reading 3x high is EXPECTED, not an error: for the
    long-branch samples the tan-delta minimum tracks the DILUTED backbone
    plateau G_b rather than G_N - that is the paper's own Figure 4 effect.

UNITS. Axes are log(a_T omega / rad s^-1) and log(G/Pa), so the abscissa is
already rad/s (NOT Hz) and the ordinate already Pa. The user digitized in
linear units with the caption shift left in; only the shift is removed here.

Output data/kapnistos2005.npz IS committed so validation runs without the
gitignored original. Re-run after re-digitizing:
    uv run python scripts/prep_kapnistos2005.py
"""
import os

import numpy as np
import pandas as pd

from rheofp.io.data import save_npz

OUT_NPZ = "data/kapnistos2005.npz"
SRC = "originals/kapnistos2005.xlsx"

N_GRID = 60

ME_PS = 17000.0          # g/mol, paper p.7853 ("typical literature value")
ME_PBD = 1815.0          # g/mol, paper p.7853
TREF_PS_K = 443.15       # 170 C, paper p.7853 WLF paragraph
TREF_PBD_K = 273.15      # 0 C,   paper p.7853 WLF paragraph
GN_PS = 2.0e5            # Pa, literature plateau modulus - a CHECK, not a fit
GN_PBD = 1.15e6          # Pa

# Sheet layout: pairwise columns (w1, gp, w2, gpp) per sample, left-to-right in
# the order the figure caption names them top-to-bottom.
#   name, M_b, M_a, q, M_e, decade shift as PLOTTED (divide it out)
# `q` is branches per backbone (Table 1); M_a None marks the linear control.
FIG1A = [
    ("c6bb-PS", 275e3, None, None, ME_PS, 1e5),
    ("c612-PS", 275e3, 6.5e3, 31.0, ME_PS, 1e4),
    ("c622-PS", 275e3, 11.7e3, 30.0, ME_PS, 1e3),
    ("c632-PS", 275e3, 25.7e3, 25.0, ME_PS, 1e2),
    ("c642-PS", 275e3, 47.0e3, 29.0, ME_PS, 1e1),
    ("c652-PS", 275e3, 98.0e3, 29.0, ME_PS, 1e0),
]
# Figure 2's caption order is lc3, lc1, lc2 - NOT numeric order.
FIG2A = [
    ("lc3-PBd", 50e3, 7.0e3, 17.0, ME_PBD, 1e2),
    ("lc1-PBd", 50e3, 11.3e3, 18.0, ME_PBD, 1e1),
    ("lc2-PBd", 50e3, 23.2e3, 17.8, ME_PBD, 1e0),
]
SHEETS = [
    ("Fig1a", FIG1A, TREF_PS_K, GN_PS, True),    # True -> swap G'/G''
    ("Fig2a", FIG2A, TREF_PBD_K, GN_PBD, False),
]


def _pairs(df, index, swap):
    """Pull the (w1, gp, w2, gpp) quadruple for the `index`-th sample.

    Columns run in blocks of four separated by a blank spacer column, so the
    n-th sample's block starts at 5*index. When `swap` is set the two ordinate
    columns are exchanged (Fig1a defect (1) in the module docstring).
    """
    block = df.iloc[:, 5 * index: 5 * index + 4]
    if block.shape[1] != 4:
        raise ValueError(f"sample {index} has {block.shape[1]} columns, want 4")
    w1, g1, w2, g2 = (block.iloc[:, i] for i in range(4))
    if swap:
        (w1, g1), (w2, g2) = (w2, g2), (w1, g1)

    def clean(w, g):
        d = pd.concat([w, g], axis=1).apply(pd.to_numeric, errors="coerce").dropna()
        wv = d.iloc[:, 0].to_numpy(float)
        gv = d.iloc[:, 1].to_numpy(float)
        keep = np.isfinite(wv) & np.isfinite(gv) & (wv > 0) & (gv > 0)
        wv, gv = wv[keep], gv[keep]
        order = np.argsort(wv)
        return wv[order], gv[order]

    return clean(w1, g1), clean(w2, g2)


def _common_grid(w_gp, gp, w_gpp, gpp, n=N_GRID):
    """Interpolate independently-digitized G' and G'' onto one log grid.

    Linear in log-log, exact for power-law segments - the same choice
    ml/dataset.resample_log_grid makes. This CROPS each sample to the overlap
    of the two abscissae.
    """
    lo = max(w_gp.min(), w_gpp.min())
    hi = min(w_gp.max(), w_gpp.max())
    if not (hi > lo):
        raise ValueError("G' and G'' windows do not overlap")
    grid = np.logspace(np.log10(lo), np.log10(hi), n)
    interp = lambda w, g: 10.0 ** np.interp(np.log10(grid), np.log10(w), np.log10(g))
    return grid, interp(w_gp, gp), interp(w_gpp, gpp)


def _plateau_at_tand_min(grid, gp, gpp):
    """G' where tan(delta) is minimal - the plateau proxy used as a unit check.

    For the long-branch samples this tracks the DILUTED backbone plateau G_b,
    not G_N (the paper's Figure 4), so a high reading is physics, not an error.
    """
    i = int(np.argmin(gpp / gp))
    return float(gp[i]), float(grid[i])


def main():
    if not os.path.exists(SRC):
        raise FileNotFoundError(
            f"{SRC} not found. It is gitignored/per-machine; "
            f"{OUT_NPZ} is committed so validation runs without it.")
    print(f"reading {SRC}")

    dataset = {}
    for sheet, rows, tref, gn_lit, swap in SHEETS:
        df = pd.read_excel(SRC, sheet_name=sheet)
        print(f"\n=== {sheet}  (T_ref {tref - 273.15:.0f} C, "
              f"G'/G'' swapped: {swap}) ===")
        for index, (name, mb, ma, q, me, shift) in enumerate(rows):
            (w_gp, gp_raw), (w_gpp, gpp_raw) = _pairs(df, index, swap)
            gp_raw, gpp_raw = gp_raw / shift, gpp_raw / shift
            grid, gp, gpp = _common_grid(w_gp, gp_raw, w_gpp, gpp_raw)

            s_b = mb / me
            s_a = None if ma is None else ma / me
            phi_b = 1.0 if ma is None else s_b / (s_b + q * s_a)

            dataset[name] = dict(
                omega=grid,      # rad/s (a_T * omega at T_ref)
                Gp=gp,           # Pa, caption shift removed
                Gpp=gpp,
                T_K=tref,
                conc=np.nan,     # melt
            )

            k = min(10, len(grid) // 4)
            sl_gp = np.polyfit(np.log10(grid[:k]), np.log10(gp[:k]), 1)[0]
            sl_gpp = np.polyfit(np.log10(grid[:k]), np.log10(gpp[:k]), 1)[0]
            plateau, w_plateau = _plateau_at_tand_min(grid, gp, gpp)
            ratio_lo = gpp[0] / gp[0]

            arch = ("LINEAR CONTROL (no branches)" if s_a is None else
                    f"s_a={s_a:.2f} s_b={s_b:.1f} q={q:g} phi_b={phi_b:.3f} "
                    f"s_b*phi_b={s_b * phi_b:.2f}")
            print(f"{name}: {arch}")
            print(f"  G' {len(w_gp):3d} pts  G'' {len(w_gpp):3d} pts -> "
                  f"{len(grid)} on a common grid; omega "
                  f"{grid.min():.3g}-{grid.max():.3g} rad/s "
                  f"({np.log10(grid.max() / grid.min()):.2f} dec)")
            print(f"  terminal slopes  G' {sl_gp:.2f}  G'' {sl_gpp:.2f} "
                  f"(melt limit 2.0 / 1.0)")
            print(f"  G''/G' at the lowest point: {ratio_lo:.2f} "
                  f"({'crossover reached' if ratio_lo > 1 else 'G-prime still above'})")
            print(f"  plateau proxy {plateau:.2e} Pa at {w_plateau:.2e} rad/s "
                  f"= {plateau / gn_lit:.2f}x literature G_N ({gn_lit:.2e})")

    save_npz(OUT_NPZ, dataset)
    print(f"\nwrote {OUT_NPZ}  ({len(dataset)} samples)")
    print("s_a, s_b and phi_b above are INDEPENDENTLY KNOWN from Table 1, not "
          "fitted - they are the ground truth to score against.")
    print("c6bb-PS is the LINEAR BACKBONE control, same figure and instrument: "
          "if `comb` labels it a comb, that is decisive against wiring in.")
    print("Score against docs/kapnistos2005_preregistration.md. Nothing in "
          "this script fits anything; keep it that way.")


if __name__ == "__main__":
    main()
