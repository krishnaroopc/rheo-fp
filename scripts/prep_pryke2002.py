"""Convert the digitized Pryke et al. (2002) three-arm 1,2-PBD star data to .npz.

Source: Pryke, Blackwell, McLeish & Young (2002), Macromolecules 35, 467-472
(doi:10.1021/ma010350l), Figure 2 - master curves at 333 K for symmetric
THREE-ARM 1,2-polybutadiene star melts. Two of the four panels are digitized
here, the two well-entangled ones:

    arm M_w = 38 900  ->  Z = M_a/M_e = 11.0
    arm M_w = 78 600  ->  Z = M_a/M_e = 22.1

with M_e = 3550 g/mol and G_0 = 0.765 MPa, tau_e = 1.02e-5 s from the paper's
Table 2. Z is therefore INDEPENDENTLY KNOWN, not fitted - the same property
that makes MM1998 the right test of the star transcription.

WHY THIS DATASET. It is the first star MELT of independent chemistry. All
prior star validation here is polyisoprene (data/mm1998.npz) or
polyisobutylene (data/santangelo1999.npz), so `star` has never been shown to
survive a change of chemistry. It is also a direct Milner-McLeish test run by
McLeish himself, against the same three parameters this module fits.
Predictions were pre-registered in docs/pryke2001_preregistration.md BEFORE
these curves were digitized; score against that file, not against hindsight.

UNITS. Confirmed with the user who digitized the figure: abscissa is s^-1
(i.e. already rad/s - NOT Hz despite the `_w_Hz` column headers, which are
shorthand), ordinate is Pa. No conversion is applied. The check that settles
it is the 38.9K plateau, which lands just under the paper's own
G_0 = 0.765 MPa; read as dyn/cm^2 it would sit 6x below G_0, and no rescaling
of the axis puts both samples anywhere else. Note G' rises ABOVE G_0 at high
frequency on both samples (3.3-3.8x) - that is the arm-Rouse term, not a unit
error: G_0 is the plateau LEVEL, not the curve maximum. See
rheofp/models/star.py.

>>> THE TERMINAL-ZONE SPLIT, WHICH IS THE POINT OF THIS DATASET <<<

The two samples sit on OPPOSITE sides of the class's measured operating
envelope, and that is recorded here so it is not rediscovered as a bug:

  38.9K (Z 11.0): terminal slopes G' 1.96 / G'' 0.95 against the melt limit
      of 2.0 / 1.0. Flow is fully resolved. `terminal_reached` is True.

  78.6K (Z 22.1): terminal slopes G' 0.38 / G'' 0.17. The G''/G' crossover
      falls ON THE LOWEST DIGITIZED POINT (ratio 1.17 at omega = 1.14e-3
      s^-1, 0.81 at the next point up), i.e. the published window ENTERS the
      terminal zone and stops. Confirmed against Figure 2 by the user: there
      is no more data to the left; this is the figure's own limit, NOT a
      truncated trace.

That distinction matters because prediction P4 makes `terminal_reached` - not
Z - the predictor of whether the class succeeds on real data (5/5 where flow
is observed, 1/5 where it is not, across MM1998 + Santangelo). So a miss on
the 78.6K sample must be scored SPLIT under P4 and must NOT be reported as a
flat failure of P1's primary claim; a miss on the 38.9K sample, which does
reach flow, WOULD be the genuine problem ranked #1 in the pre-registration.
Both curves are kept exactly as digitized - no truncation, no reweighting -
because trimming to make a result look better is the failure mode this
project pre-registers against.

G' and G'' were digitized independently (different point counts and omega
values), so they are interpolated onto a common per-sample log grid over
their overlap - linear in log-log, exact for power-law segments, the same
choice ml/dataset.resample_log_grid makes. Note this CROPS each sample to the
overlap: the 78.6K crossover point at 1.14e-3 survives because G'' extends to
1.60e-3 and the grid starts at the higher of the two minima, so the reported
grid floor is 1.60e-3 rather than 1.14e-3.

Output data/pryke2002.npz IS committed so validation runs without the
gitignored original. Re-run after re-digitizing:
    uv run python scripts/prep_pryke2002.py
"""
import os

import numpy as np
import pandas as pd

from rheofp.io.data import save_npz

OUT_NPZ = "data/pryke2002.npz"
SRC = "originals/pryke2002.xlsx"

TREF_K = 333.0          # master-curve reference temperature, paper Table 2
ME_PBD = 3550.0         # g/mol, 1,2-polybutadiene, paper Table 2
G0_PAPER = 0.765e6      # Pa
TAU_E_PAPER = 1.02e-5   # s

N_GRID = 60

# column-prefix in the sheet -> arm molecular weight (g/mol)
MA_BY_PREFIX = {"38.9": 38900.0, "78.6": 78600.0}


def _curve(df, prefix, kind):
    """Pull one (omega, G) pair. Duplicate `<p>_w_Hz` headers are de-duplicated
    by pandas into `<p>_w_Hz` / `<p>_w_Hz.1`, so the G' and G'' abscissae are
    matched positionally to their own ordinate column."""
    gcol = f"{prefix}_{kind}_Pa"
    if gcol not in df.columns:
        raise KeyError(f"missing column {gcol!r}")
    gi = list(df.columns).index(gcol)
    wcol = df.columns[gi - 1]
    if not str(wcol).startswith(f"{prefix}_w"):
        raise KeyError(f"column left of {gcol!r} is {wcol!r}, not a {prefix} omega")

    d = df[[wcol, gcol]].apply(pd.to_numeric, errors="coerce").dropna()
    w = d[wcol].to_numpy(float)
    g = d[gcol].to_numpy(float)
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
    df = pd.read_excel(SRC, sheet_name="Sheet1")

    dataset = {}
    for prefix in sorted(MA_BY_PREFIX, key=lambda p: MA_BY_PREFIX[p]):
        ma = MA_BY_PREFIX[prefix]
        w_gp, gp = _curve(df, prefix, "gp")
        w_gpp, gpp = _curve(df, prefix, "gpp")
        grid, gp_i, gpp_i = _common_grid(w_gp, gp, w_gpp, gpp)

        z = ma / ME_PBD
        name = f"PBD3_Ma{int(ma / 1000)}k"
        dataset[name] = dict(
            omega=grid,          # rad/s (a_T * omega, Tref 333 K)
            Gp=gp_i,             # Pa
            Gpp=gpp_i,
            T_K=TREF_K,
            conc=np.nan,         # melt
        )

        k = min(10, len(grid) // 4)
        s_gp = np.polyfit(np.log10(grid[:k]), np.log10(gp_i[:k]), 1)[0]
        s_gpp = np.polyfit(np.log10(grid[:k]), np.log10(gpp_i[:k]), 1)[0]
        # crossover on the RAW trace, before the overlap crop
        gpp_on_gp = 10.0 ** np.interp(np.log10(w_gp), np.log10(w_gpp),
                                      np.log10(gpp))
        ratio_lo = gpp_on_gp[0] / gp[0]

        print(f"{name}: 3-arm star, Ma={ma:.0f}, Z=Ma/Me={z:.2f}")
        print(f"  G' {len(w_gp):3d} pts  G'' {len(w_gpp):3d} pts "
              f"-> {len(grid)} on a common grid; "
              f"omega {grid.min():.3g}-{grid.max():.3g} rad/s "
              f"({np.log10(grid.max() / grid.min()):.2f} dec)")
        print(f"  terminal slopes  G' {s_gp:.2f}  G'' {s_gpp:.2f} "
              f"(melt limit 2.0 / 1.0)")
        print(f"  G''/G' at the lowest raw point: {ratio_lo:.2f} "
              f"({'crossover reached' if ratio_lo > 1 else 'still G'' < G'''})")
        print(f"  plateau: max G' {gp_i.max() / 1e6:.2f} MPa "
              f"= {gp_i.max() / G0_PAPER:.1f}x the paper's G_0 "
              f"({G0_PAPER / 1e6:.3f} MPa; G' exceeds G_0 by design, arm-Rouse)")

    save_npz(OUT_NPZ, dataset)
    print(f"wrote {OUT_NPZ}  ({len(dataset)} samples)")
    print("Z = Ma/Me is independently known ground truth; the number of ARMS "
          "(3) is NOT recoverable from LVE and must not be claimed. Z itself "
          "remains a non-reportable output (pre-registration P3).")
    print("Score against docs/pryke2001_preregistration.md, splitting on "
          "terminal_reached (P4) - the 78.6K window stops AT its crossover.")


if __name__ == "__main__":
    main()
