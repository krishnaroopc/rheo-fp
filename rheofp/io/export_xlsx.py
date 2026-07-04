"""On-demand xlsx export for human inspection.

Not part of any automated path - call this manually when you (a human) want
to open a converted dataset in Excel to eyeball it. Everything else in the
package reads/writes the canonical .npz format via rheofp.io.data.
"""
from __future__ import annotations

import pandas as pd

from rheofp.io.data import load_npz


def export_npz_to_xlsx(npz_path, xlsx_path, sheet_name="Sheet1"):
    """Write a dataset (as produced by rheofp.io.data.save_npz) back out to
    xlsx for manual inspection: one "<sample> omega" / "<sample> G' (Pa)" /
    "<sample> G'' (Pa)" column triple per sample.

    Samples are not assumed to share a common omega grid (they often don't -
    each is independently masked/sorted during xlsx->npz conversion), so this
    is per-sample columns rather than the single-shared-omega convention used
    on the way in. Columns are padded with NaN to the longest sample's length.

    For local inspection only - never called by the package's normal code
    paths, and the output should not be committed to the repository.
    """
    dataset = load_npz(npz_path)

    columns = {}
    for sample, fields in dataset.items():
        columns[f"{sample} omega"] = pd.Series(fields["omega"])
        columns[f"{sample} G' (Pa)"] = pd.Series(fields["Gp"])
        columns[f"{sample} G'' (Pa)"] = pd.Series(fields["Gpp"])

    df = pd.DataFrame(columns)  # pandas pads shorter Series with NaN
    df.to_excel(xlsx_path, sheet_name=sheet_name, index=False)
    return xlsx_path
