"""Common-omega-grid interpolation utility (from interpolate_rheology.ipynb).

Resamples one or more (omega, G', G'') datasets with mismatched frequency
grids onto a shared log-spaced omega grid, so multi-dataset comparisons and
downstream fitting can operate on aligned points.

Note: the original notebook's raw input (pivo2006.xlsx, sheet "Sheet1", a
4-columns-per-dataset layout: [w_gp, gp, w_gpp, gpp]) is stale - that sheet
no longer exists in the current pivo2006.xlsx (only "fig2" does, in the
standard convention format). This script migrates the interpolation
algorithm as reusable functions; main() demonstrates it against the
already-converted data/interpolated_rheology.npz.

Run directly: python scripts/prep_interpolate.py
"""
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

from rheofp.io.data import load_npz

N_POINTS = 100
INTERP_KIND = "linear"
LOG_OMEGA = True


def common_omega_grid(omega_arrays, n_points=N_POINTS, log_omega=LOG_OMEGA):
    """Build a shared omega grid spanning the union of several datasets."""
    all_omega = np.concatenate(omega_arrays)
    if log_omega:
        w_common = np.unique(np.round(np.log10(all_omega), decimals=10))
        w_common = 10**w_common
    else:
        w_common = np.unique(all_omega)
    w_common = np.sort(w_common)
    if len(w_common) > n_points:
        if log_omega:
            w_common = np.logspace(np.log10(w_common.min()), np.log10(w_common.max()), n_points)
        else:
            w_common = np.linspace(w_common.min(), w_common.max(), n_points)
    return w_common


def make_interp(w_orig, y_orig, kind=INTERP_KIND):
    """Build an interpolator after sorting and deduplicating the input grid."""
    idx = np.argsort(w_orig)
    ws, ys = w_orig[idx], y_orig[idx]
    _, ui = np.unique(ws, return_index=True)
    ws, ys = ws[ui], ys[ui]
    return interp1d(ws, ys, kind=kind, bounds_error=True), ws.min(), ws.max()


def interpolate_dataset(w_common, omega, Gp, Gpp, kind=INTERP_KIND):
    """Resample one (omega, Gp, Gpp) dataset onto w_common, within its own range."""
    f_gp, lo_gp, hi_gp = make_interp(omega, Gp, kind)
    f_gpp, lo_gpp, hi_gpp = make_interp(omega, Gpp, kind)
    lo, hi = max(lo_gp, lo_gpp), min(hi_gp, hi_gpp)
    if lo > hi:
        return None
    mask = (w_common >= lo) & (w_common <= hi)
    w_sub = w_common[mask]
    return dict(mask=mask, w_sub=w_sub, gp=f_gp(w_sub), gpp=f_gpp(w_sub))


def main():
    dataset = load_npz("data/interpolated_rheology.npz")
    print(f"Loaded {len(dataset)} sample(s) from data/interpolated_rheology.npz: {list(dataset)}")

    w_common = common_omega_grid([d["omega"] for d in dataset.values()])
    print(f"Common omega grid: {len(w_common)} points  [{w_common.min():.4g}, {w_common.max():.4g}]")

    fig, ax = plt.subplots(figsize=(8, 6))
    colors = plt.cm.tab10.colors
    for i, (label, d) in enumerate(dataset.items()):
        res = interpolate_dataset(w_common, d["omega"], d["Gp"], d["Gpp"])
        if res is None:
            print(f"  {label}: G' and G'' omega ranges don't overlap - skipping")
            continue
        print(f"  {label}: {res['mask'].sum()} shared omega points "
              f"[{res['w_sub'].min():.4g}, {res['w_sub'].max():.4g}]")
        c = colors[i % len(colors)]
        ax.loglog(res["w_sub"], res["gp"], "-", color=c, lw=1.8, label=f"{label} G'")
        ax.loglog(res["w_sub"], res["gpp"], "--", color=c, lw=1.8, label=f"{label} G''")

    ax.set_xlabel(r"$\omega$ [rad/s]")
    ax.set_ylabel("Modulus [Pa]")
    ax.set_title("Interpolated G' and G'' - all datasets")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", ls=":", alpha=0.4)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
