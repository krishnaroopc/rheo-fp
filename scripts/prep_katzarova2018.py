"""Convert the digitized Katzarova et al. (2018) bidisperse PS data to .npz.

Source: Katzarova, Kashyap, Schieber & Venerus (2018), "Linear viscoelastic
behavior of bidisperse polystyrene blends: experiments and slip-link
predictions", Rheologica Acta 57, 327-338 (doi:10.1007/s00397-018-1079-7).
Master curves at T_0 = 150 C (TTS from 130/150/170 C, WLF c1=6.8, c2=97.8).

    Fig. 1  three monodisperse melts        PS392, PS206, PS105
    Fig. 2  three 50/50-by-weight blends    2a = HM, 2b = HL, 2c = ML

Paper Table 1 (component characterization):

    PS105   M_w = 105 kDa   M_w/M_n = 1.03
    PS206   M_w = 206 kDa   M_w/M_n = 1.04
    PS392   M_w = 392 kDa   M_w/M_n = 1.06

WHY THIS DATASET. It is the real-data test of whether a `blend` class can be
built at all, and it was chosen for one property no other candidate has: each
panel of Fig. 2 plots a blend TOGETHER WITH BOTH of its pure components, so
the monodisperse control and the blend come from the same instrument, the same
sample prep and the same figure. That control is the veto. `comb` was retired
on exactly this test - it fit the LINEAR backbone control better than any real
comb in the same figure (CLAUDE.md, Kapnistos 2005) - and a 4-parameter blend
model containing the monodisperse case as its w->1 limit is at least as
capable of that failure. Predictions are pre-registered in
docs/katzarova2018_preregistration.md BEFORE any fit; score against that file.

>>> THE KNOWN TRUTH HERE IS COMPOSITION, AND IT IS FIXED AT 0.5 <<<

All three blends are 50/50 BY WEIGHT, so w_L = 0.5 exactly for every one -
known, never fitted. That is the dataset's strength and its limit:

  - it can test "is this one species or two" and "does the model outfit a
    monodisperse chain", which are the two questions that decide the class;
  - it CANNOT test whether composition is recoverable, because there is no
    composition sweep. Do not read a recovered w ~ 0.5 as evidence that w is
    identifiable - with every sample planted at 0.5, a fitter that always
    returned 0.5 would score perfectly. The sweep lives in Struglinski &
    Graessley 1985 (originals/struglinski_graessley1985_polydispersity_blends.pdf,
    5 series x 7-10 compositions,
    phi_L 0.025-0.90), which is the SECOND test and is deliberately not
    digitized yet.

Component molecular weights ARE independently known (Table 1 above), so Z_1
and Z_2 are ground truth via M_e = 13.3 kg/mol for PS (Fetters et al. 1994,
the value Nielsen et al. 2006 use for the same polymer). Z = 7.9 / 15.5 / 29.5
for PS105 / PS206 / PS392.

UNITS. Confirmed with the user who digitized the figures: abscissa is rad/s
(the paper's own axis label), ordinate is kPa (the paper's own axis label) and
is converted to Pa here by x1000. The check that settles it: the plateau sits
near 2e5 Pa, which is the accepted PS plateau modulus (~200 kPa); read as Pa
the melts would be softer than water-thin. Note G' rises ABOVE the plateau at
high frequency on every curve - that is the Rouse zone, not a unit error, and
it is the same feature documented for star melts in rheofp/models/star.py.

G' and G'' were digitized independently (different point counts and omega
values, since they are separate marker series in the figure), so they are
interpolated onto a common per-sample log grid over their overlap - linear in
log-log, exact for power-law segments, the same choice
ml/dataset.resample_log_grid makes and the same one used for Pryke 2002.
This CROPS each sample to the overlap; the per-sample crop is printed.

One duplicated abscissa exists in the source (PS105 G' has two points at
omega = 0.0258 with G' = 0.2562 / 0.2889 kPa) - overlapping markers in the
figure, not a transcription error. np.interp requires an increasing abscissa,
so exact duplicates are averaged in log space before interpolation.

Output data/katzarova2018.npz IS committed so validation runs without the
gitignored original. Re-run after re-digitizing:
    uv run python scripts/prep_katzarova2018.py
"""
import os

import numpy as np
import pandas as pd

from rheofp.io.data import save_npz

OUT_NPZ = "data/katzarova2018.npz"
SRC = "originals/katzarova2018.xlsx"

TREF_K = 423.15          # 150 C master-curve reference, paper "Rheology experiments"
ME_PS = 13300.0          # g/mol, polystyrene (Fetters 1994; used by Nielsen 2006)
KPA_TO_PA = 1.0e3

N_GRID = 60

# Fig. 1 sheet: column prefix -> (sample name, M_w g/mol, PDI from Table 1)
PURE = {
    "392": ("PS392", 392.0e3, 1.06),
    "206": ("PS206", 206.0e3, 1.04),
    "105": ("PS105", 105.0e3, 1.03),
}

# Fig. 2 sheet: column prefix -> (name, panel, long component, short component)
# Panel order is 2a/2b/2c = b1/b2/b3, confirmed by the user who digitized it.
# Paper Fig. 2 caption: a = blend HM, b = blend HL, c = blend ML.
BLENDS = {
    "b1": ("HM", "2a", "PS392", "PS206"),
    "b2": ("HL", "2b", "PS392", "PS105"),
    "b3": ("ML", "2c", "PS206", "PS105"),
}

W_LONG = 0.5   # every blend is 50/50 BY WEIGHT - known truth, never fitted


def _curve(df, prefix, kind):
    """Pull one (omega, G) pair from the `<prefix>_w1/_gp` `<prefix>_w2/_gpp`
    layout. G' and G'' carry their own abscissa because they were traced as
    separate marker series."""
    wcol = f"{prefix}_w1" if kind == "gp" else f"{prefix}_w2"
    gcol = f"{prefix}_{kind}"
    for c in (wcol, gcol):
        if c not in df.columns:
            raise KeyError(f"missing column {c!r} in sheet")

    d = df[[wcol, gcol]].apply(pd.to_numeric, errors="coerce").dropna()
    w = d[wcol].to_numpy(float)
    g = d[gcol].to_numpy(float)
    keep = np.isfinite(w) & np.isfinite(g) & (w > 0) & (g > 0)
    w, g = w[keep], g[keep]
    order = np.argsort(w)
    return w[order], g[order] * KPA_TO_PA


def _dedupe(w, g):
    """Average exact duplicate abscissae in log space. Overlapping markers in
    the figure produce these; np.interp needs an increasing abscissa."""
    uniq, inv = np.unique(w, return_inverse=True)
    if len(uniq) == len(w):
        return w, g
    out = np.array([10.0 ** np.mean(np.log10(g[inv == i]))
                    for i in range(len(uniq))])
    return uniq, out


def _common_grid(w_gp, gp, w_gpp, gpp, n=N_GRID):
    w_gp, gp = _dedupe(w_gp, gp)
    w_gpp, gpp = _dedupe(w_gpp, gpp)
    lo = max(w_gp.min(), w_gpp.min())
    hi = min(w_gp.max(), w_gpp.max())
    if not (hi > lo):
        raise ValueError("G' and G'' windows do not overlap")
    grid = np.logspace(np.log10(lo), np.log10(hi), n)
    interp = lambda w, g: 10.0 ** np.interp(
        np.log10(grid), np.log10(w), np.log10(g))
    return grid, interp(w_gp, gp), interp(w_gpp, gpp)


def _report(name, grid, gp, gpp, w_gp, w_gpp, extra):
    k = min(10, len(grid) // 4)
    s_gp = np.polyfit(np.log10(grid[:k]), np.log10(gp[:k]), 1)[0]
    s_gpp = np.polyfit(np.log10(grid[:k]), np.log10(gpp[:k]), 1)[0]
    raw_lo = min(w_gp.min(), w_gpp.min())
    raw_hi = max(w_gp.max(), w_gpp.max())
    ratio_lo = gpp[0] / gp[0]   # both already on `grid`

    print(f"{name}: {extra}")
    print(f"  G' {len(w_gp):3d} pts  G'' {len(w_gpp):3d} pts "
          f"-> {len(grid)} on a common grid; "
          f"omega {grid.min():.3g}-{grid.max():.3g} rad/s "
          f"({np.log10(grid.max() / grid.min()):.2f} dec)")
    print(f"  overlap crop: raw span {np.log10(raw_hi / raw_lo):.2f} dec "
          f"-> kept {np.log10(grid.max() / grid.min()):.2f} dec")
    print(f"  terminal slopes  G' {s_gp:.2f}  G'' {s_gpp:.2f} "
          f"(melt limit 2.0 / 1.0)")
    print(f"  G''/G' at the lowest gridded point: {ratio_lo:.2f} "
          f"({'flowing' if ratio_lo > 1 else 'NOT past crossover'})")
    print(f"  max G' {gp.max() / 1e3:.0f} kPa "
          f"(PS plateau ~200 kPa; G' exceeds it in the Rouse zone by design)")


def main():
    if not os.path.exists(SRC):
        raise FileNotFoundError(
            f"{SRC} not found. It is gitignored/per-machine; "
            f"{OUT_NPZ} is committed so validation runs without it.")
    print(f"reading {SRC}")
    fig1 = pd.read_excel(SRC, sheet_name="Fig1")
    fig2 = pd.read_excel(SRC, sheet_name="Fig2")

    dataset = {}

    print("\n--- Fig. 1: monodisperse components (the CONTROLS) ---")
    for prefix, (name, mw, pdi) in sorted(
            PURE.items(), key=lambda kv: -kv[1][1]):
        w_gp, gp = _curve(fig1, prefix, "gp")
        w_gpp, gpp = _curve(fig1, prefix, "gpp")
        grid, gp_i, gpp_i = _common_grid(w_gp, gp, w_gpp, gpp)
        z = mw / ME_PS
        dataset[name] = dict(
            omega=grid, Gp=gp_i, Gpp=gpp_i,
            T_K=TREF_K, conc=np.nan,
            Mw_long=mw, Mw_short=np.nan, w_long=1.0,
            Z_long=z, Z_short=np.nan, PDI=pdi, is_blend=0.0,
        )
        _report(name, grid, gp_i, gpp_i, w_gp, w_gpp,
                f"monodisperse, M_w={mw / 1e3:.0f} kDa, PDI={pdi}, "
                f"Z=M_w/M_e={z:.1f}")

    print("\n--- Fig. 2: 50/50 blends (w_long = 0.5, KNOWN) ---")
    for prefix in ("b1", "b2", "b3"):
        name, panel, long_c, short_c = BLENDS[prefix]
        mw_l = PURE[[k for k, v in PURE.items() if v[0] == long_c][0]][1]
        mw_s = PURE[[k for k, v in PURE.items() if v[0] == short_c][0]][1]
        w_gp, gp = _curve(fig2, prefix, "gp")
        w_gpp, gpp = _curve(fig2, prefix, "gpp")
        grid, gp_i, gpp_i = _common_grid(w_gp, gp, w_gpp, gpp)
        dataset[name] = dict(
            omega=grid, Gp=gp_i, Gpp=gpp_i,
            T_K=TREF_K, conc=np.nan,
            Mw_long=mw_l, Mw_short=mw_s, w_long=W_LONG,
            Z_long=mw_l / ME_PS, Z_short=mw_s / ME_PS,
            PDI=np.nan, is_blend=1.0,
        )
        _report(name, grid, gp_i, gpp_i, w_gp, w_gpp,
                f"Fig. {panel}, 50/50 {long_c}+{short_c}, "
                f"Z={mw_l / ME_PS:.1f}/{mw_s / ME_PS:.1f}, w_long=0.5")

    save_npz(OUT_NPZ, dataset)
    print(f"\nwrote {OUT_NPZ}  ({len(dataset)} samples: "
          f"3 monodisperse controls + 3 blends)")
    print("w_long = 0.5 is known ground truth for all three blends, but it is "
          "the SAME for all three - a fitter that always returns 0.5 scores "
          "perfectly here. Composition recovery needs Struglinski & Graessley "
          "1985, which is not digitized.")
    print("Score against docs/katzarova2018_preregistration.md. The three "
          "monodisperse curves are the VETO: a blend model that beats the "
          "linear-melt class on PS105/PS206/PS392 is winning by flexibility, "
          "which is how `comb` was retired.")


if __name__ == "__main__":
    main()
