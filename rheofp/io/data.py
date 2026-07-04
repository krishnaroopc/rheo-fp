"""Canonical data I/O for rheo-fp.

Data convention (see CLAUDE.md): column 0 of a sheet is omega, followed by
paired columns named "<sample> G' (Pa)" / "<sample> G'' (Pa)". One sheet per
dataset. Values are stored per-sample as a dict with keys: omega, Gp, Gpp,
and optional metadata (T_K, conc).

load_xlsx() is used only for one-time conversion of the original xlsx sources
into the open .npz format below - it is not part of any path shipped to end
users of the public repo.
"""
from __future__ import annotations

import numpy as np


def load_xlsx(path, sheet=None, meta_sheet=None, omega_hz=False):
    """Load one sheet of SAOS data (+ optional metadata) from an xlsx file.

    Returns {sample: dict(omega, Gp, Gpp, T_K, conc)}, sorted by omega with
    non-finite rows dropped.
    """
    import pandas as pd

    xls = pd.ExcelFile(path)
    target = sheet if sheet is not None else xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=target)

    omega = pd.to_numeric(df.iloc[:, 0], errors="coerce").to_numpy(float)
    if omega_hz:
        omega = omega * 2.0 * np.pi

    meta = {}
    if meta_sheet is not None and meta_sheet in xls.sheet_names:
        m = pd.read_excel(xls, sheet_name=meta_sheet)
        for _, row in m.iterrows():
            meta[str(row.iloc[0])] = dict(
                T_K=float(row["T_K"]) if "T_K" in row and row["T_K"] is not None else np.nan,
                conc=float(row["conc"]) if "conc" in row and row["conc"] is not None else np.nan,
            )

    out = {}
    cols = list(df.columns[1:])
    for i in range(0, len(cols) - 1, 2):
        gp_col, gpp_col = cols[i], cols[i + 1]
        sample = str(gp_col).split(" G'")[0].strip()

        gp = pd.to_numeric(df[gp_col], errors="coerce").to_numpy(float)
        gpp = pd.to_numeric(df[gpp_col], errors="coerce").to_numpy(float)

        mask = np.isfinite(omega) & np.isfinite(gp) & np.isfinite(gpp) & (omega > 0)
        order = np.argsort(omega[mask])

        md = meta.get(sample, dict(T_K=np.nan, conc=np.nan))
        out[sample] = dict(
            omega=omega[mask][order],
            Gp=gp[mask][order],
            Gpp=gpp[mask][order],
            **md,
        )
    return out


def save_npz(path, dataset):
    """Write a {sample: dict(omega, Gp, Gpp, T_K, conc)} dataset to .npz.

    Each sample's arrays/scalars are namespaced as "<sample>__<field>" since
    .npz is a flat key-value store.
    """
    flat = {}
    samples = list(dataset.keys())
    flat["__samples__"] = np.array(samples, dtype=object)
    for sample, fields in dataset.items():
        for key, value in fields.items():
            flat[f"{sample}__{key}"] = np.asarray(value)
    np.savez(path, **flat)


def load_npz(path):
    """Read a dataset written by save_npz() back into
    {sample: dict(omega, Gp, Gpp, T_K, conc)}.
    """
    with np.load(path, allow_pickle=True) as npz:
        samples = list(npz["__samples__"])
        out = {}
        for sample in samples:
            prefix = f"{sample}__"
            fields = {
                key[len(prefix):]: npz[key]
                for key in npz.files
                if key.startswith(prefix)
            }
            out[sample] = fields
        return out
