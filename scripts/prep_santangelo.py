"""Convert the digitized Santangelo, Roland & Puskas (1999) star-PIB SAOS data.

Source: Santangelo, Roland & Puskas (1999), Macromolecules 32, 1972
(doi:10.1021/ma9815556), Figures 1 (G') and 2 (G''). Two six-arm star
polyisobutylenes plus a LINEAR PIB control, all at Tref = 80 C:

    L176   linear,      Mw 176 000, Mw/Mn 1.6
    S217   6-arm star,  Mw 217 000, Mw/Mn 1.19,  Ma/Me = 4
    S490   6-arm star,  Mw 490 000, Mw/Mn 1.18,  Ma/Me = 9

Me = 9400 g/mol, G_N^0 = 290 kPa (their eq 6 integration, Fig. 4).

WHY THIS DATASET: it is the first real-data test of the `star` class, and it
carries its own linear control - so it tests the discrimination the class
exists to make (star vs linear melt), not merely whether a star curve can be
fitted. Ma/Me is measured independently (SEC/MALLS + the plateau modulus), so
`Z` from fit_star has a ground truth to be checked against.

THREE THINGS ABOUT THESE AXES, ALL DELIBERATE
1. *The plotted abscissa is a_T*omega and the ordinate b_T*G, at Tref = 80 C.*
   Figures 1/2 are MASTER CURVES: each sample's points are already shifted onto
   one reference temperature. The `_150` / `_4` / `_90` / `_-18` / `_-10`
   suffixes in the source spreadsheet are therefore PROVENANCE (which isotherm
   the points were read from - the paper plots only the two extremes of the
   measured range for clarity), NOT a temperature at which to interpret the
   data. Both isotherms of a sample are concatenated here into a single 80 C
   curve. Confirmed with the user 2026-09-09.
2. *b_T is not removed and cannot be.* Each isotherm was scaled by its own
   b_T before plotting, and only b_T(80 C) = 1 exactly. For PIB b_T spans
   ~0.85-1.2 over the whole 170-degree range (their Fig. 3), so on a log
   modulus axis this is a minor distortion. Consequence, and it is the honest
   reading: `G_N` recovered from these curves is approximate - check it loosely
   against 290 kPa, do NOT treat it as a validation criterion. `Z` is set by
   the SHAPE of the loss peak and the spectrum width in log-omega, which a
   near-unity multiplicative b_T does not move, so Z is the real test.
3. *a_T is a pure horizontal translation in log-omega*, so it shifts the fitted
   tau_e (a nuisance parameter) and not Z.

FIT WINDOW - READ BEFORE USING THIS DATA. Above a_T*omega ~ 1e3 every sample
climbs steeply past G_N toward ~1e3 kPa: that is the GLASS TRANSITION ZONE
encroaching, which the paper itself flags ("on the high-frequency side of the
terminal peak, there is overlapping with the glass transition zone"). The
Milner-McLeish star model has no glassy mode - it terminates at the plateau -
so fitting through that rise would force tau_e to absorb glassy physics and
corrupt Z. The full digitized range is stored here unmodified; `FIT_OMEGA_MAX`
is exported alongside as the recommended upper bound, and consumers should
window explicitly rather than silently. Deciding this in the prep script keeps
the judgement visible instead of buried in a fitting heuristic.

G' and G'' were digitized independently (different point counts, different
omega values), but save_npz stores ONE omega per sample. They are therefore
interpolated onto a common per-sample log grid spanning their overlap -
linear in log-log, which is exact for power-law segments, the same choice
ml/dataset.resample_log_grid makes.

Units in the source sheet: omega in 1/s (already rad/s - the paper's axis is
a_T*omega in s^-1), moduli in kPa -> converted to Pa here.

Output data/santangelo1999.npz IS committed so validation runs without the
gitignored original.  Re-run after re-digitizing:
    uv run python scripts/prep_santangelo.py
"""
import os

import numpy as np
import pandas as pd

from rheofp.io.data import save_npz

OUT_NPZ = "data/santangelo1999.npz"
SRC = "originals/santangelo1999.xlsx"

KPA_TO_PA = 1e3
TREF_C = 80.0
TREF_K = TREF_C + 273.15

# sample -> the two isotherms digitized for it (provenance labels, see above).
# Sheet headers use "S176" for the LINEAR L176; renamed on output to match the
# paper's Table 1, since calling the linear control "S..." invites exactly the
# misreading this dataset exists to test against.
SAMPLES = {
    "S490": ("150", "4"),
    "S217": ("90", "-18"),
    "S176": ("90", "-10"),
}
RENAME = {"S176": "L176"}

# Independently measured, for validate/test to check the fit against.
ARMS_PER_MOLECULE = {"S490": 6, "S217": 6, "L176": None}   # None = linear
Z_ARM_REPORTED = {"S490": 9.0, "S217": 4.0, "L176": None}  # Ma/Me, their Table 1
G_N_REPORTED_PA = 290e3

# Upper bound of the usable window: above this the glass transition zone
# dominates and the star model cannot represent it. See the module docstring.
FIT_OMEGA_MAX = 1e3

N_GRID = 60


def _read_pairs(df, sample, kind, temps):
    """Concatenate a sample's isotherms into one (omega, G) master curve."""
    w, g = [], []
    for t in temps:
        wc, gc = f"{sample}_w_{t}", f"{sample}_{kind}_{t}"
        if wc not in df.columns or gc not in df.columns:
            raise KeyError(f"missing column {wc!r}/{gc!r} in sheet {kind!r}")
        d = df[[wc, gc]].apply(pd.to_numeric, errors="coerce").dropna()
        w += list(d[wc].to_numpy(float))
        g += list(d[gc].to_numpy(float))
    w, g = np.asarray(w), np.asarray(g)
    keep = np.isfinite(w) & np.isfinite(g) & (w > 0) & (g > 0)
    w, g = w[keep], g[keep]
    order = np.argsort(w)
    return w[order], g[order]


def _common_grid(w_gp, gp, w_gpp, gpp, n=N_GRID):
    """Interpolate both moduli onto one log grid over their shared window."""
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
    for sample, temps in SAMPLES.items():
        w_gp, gp = _read_pairs(gp_sheet, sample, "gp", temps)
        w_gpp, gpp = _read_pairs(gpp_sheet, sample, "gpp", temps)
        grid, gp_i, gpp_i = _common_grid(w_gp, gp, w_gpp, gpp)

        name = RENAME.get(sample, sample)
        dataset[name] = dict(
            omega=grid,                    # rad/s, = a_T * omega at Tref
            Gp=gp_i * KPA_TO_PA,           # Pa, = b_T * G'
            Gpp=gpp_i * KPA_TO_PA,
            T_K=TREF_K,                    # the master curve's reference T
            conc=np.nan,                   # melt
        )

        z = Z_ARM_REPORTED[name]
        kind = "linear control" if z is None else f"6-arm star, Ma/Me = {z:g}"
        n_fit = int((grid <= FIT_OMEGA_MAX).sum())
        print(f"{name}: {kind}")
        print(f"  G'  {len(w_gp):3d} pts   G'' {len(w_gpp):3d} pts   "
              f"-> {len(grid)} on a common grid")
        print(f"  omega {grid.min():.4g} - {grid.max():.4g} rad/s "
              f"({np.log10(grid.max() / grid.min()):.2f} decades); "
              f"{n_fit} pts at or below FIT_OMEGA_MAX={FIT_OMEGA_MAX:g}")
        print(f"  G' {gp_i.min():.4g} - {gp_i.max():.4g} kPa   "
              f"G'' {gpp_i.min():.4g} - {gpp_i.max():.4g} kPa")

    save_npz(OUT_NPZ, dataset)
    print(f"wrote {OUT_NPZ}  ({len(dataset)} samples)")
    print(f"note: G_N^0 reported by the paper = {G_N_REPORTED_PA / 1e3:g} kPa; "
          f"b_T is baked into these moduli, so treat a recovered G_N as "
          f"approximate (see module docstring).")


if __name__ == "__main__":
    main()
