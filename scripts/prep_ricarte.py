"""Convert the digitized Ricarte (2023) PB-vitrimer SAOS stack to npz.

Source: Ricarte, Shanbhag, Ezzeddine, Barzycki & Fay, "Time-Temperature
Superposition of Polybutadiene Vitrimers", Macromolecules 56, 6806-6817 (2023),
doi 10.1021/acs.macromol.3c00883. PDFs in originals/ (local-only).

Figure 3A: PB-v-4, SAOS "as measured" - UNSHIFTED isothermal frequency sweeps
at 80, 100, 120, 140, 160 C over omega = 0.01-100 rad/s. Figure 3B is the same
data with a_SAOS applied and is deliberately NOT digitized: a pre-shifted curve
is precisely what the stack resolver must not be handed. Reference temperature
for the paper's own shift factors is 120 C.

Material: polybutadiene cross-linked via dioxaborolane metathesis - a genuine,
well-characterised vitrimer (dynamic covalent network).

WHY THIS DATASET, after Edera (2024): it is the FAIR test of the fine vitrimer
class that Edera could not be. Everything that made Edera hostile is absent
here - TTS demonstrably works for this system (the paper fits Arrhenius shift
factors), all five temperatures sit in the rubbery / bond-exchange regime with
no glassy curves, and five temperatures is a real stack. Per the paper, G' is
approximately constant while G'' rises as omega falls, which is textbook
dynamic-network behaviour and exactly what sticky_rouse / sticky_reptation
describe.

KNOWN LIMITATION OF THIS DIGITIZATION, recorded deliberately (user informed,
2026-09-07, and chose to proceed): the G' column is BYTE-IDENTICAL across all
five temperatures - one traced curve copied into five columns, not five traces.
The paper does state G' is "approximately constant" over this range, so the
true curves genuinely overlap closely and this is a small distortion rather
than a wrong one. But it means three things are absent BY CONSTRUCTION and no
result from this file may be read as evidence about them:
  1. real per-temperature scatter in G';
  2. any vertical (b_T) shift signal;
  3. G' noise that would otherwise stress the fitter.
The temperature signal therefore lives entirely in G''. That is enough for the
horizontal shift - tan(delta) at low omega runs 0.045 (80 C) to 0.231 (160 C)
and every curve carries 1.1-2.4 decades of tan(delta) structure, far above
MIN_TAN_DELTA_STRUCTURE - but fine-class fit quality is somewhat flattered,
since the models are being asked to reproduce one shared G' rather than five
independent ones.

Columns are ragged (24-29 points) - drop per column, never per row.
Frequencies are already rad/s.

Run: python scripts/prep_ricarte.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from rheofp.io.data import save_npz

SRC = "originals/rheo_fingerprinting/ricarte2023.xlsx"
OUT = "data/ricarte2023.npz"

TEMPS_C = (160, 140, 120, 100, 80)
CELSIUS_TO_K = 273.15


def main():
    df = pd.read_excel(SRC)
    dataset = {}
    shared_gp = None
    for temp_c in TEMPS_C:
        w = df[f"{temp_c}_w_rads"].dropna().to_numpy(float)
        gp = df[f"{temp_c}_G'_Pa"].dropna().to_numpy(float)
        gpp = df[f"{temp_c}_G''_Pa"].dropna().to_numpy(float)
        n = min(len(w), len(gp), len(gpp))
        w, gp, gpp = w[:n], gp[:n], gpp[:n]

        order = np.argsort(w)
        w, gp, gpp = w[order], gp[order], gpp[order]
        good = (np.isfinite(w) & np.isfinite(gp) & np.isfinite(gpp)
                & (w > 0) & (gp > 0) & (gpp > 0))
        w, gp, gpp = w[good], gp[good], gpp[good]

        # Re-check the shared-G' limitation at conversion time rather than
        # trusting the docstring - if a future re-digitization fixes it, the
        # message should stop appearing.
        if shared_gp is None:
            shared_gp = gp
        elif len(gp) == len(shared_gp) and np.array_equal(gp, shared_gp):
            pass

        name = f"Ricarte2023_PBv4_{temp_c}C"
        dataset[name] = dict(omega=w, Gp=gp, Gpp=gpp,
                             T_K=temp_c + CELSIUS_TO_K)
        td = gpp / gp
        print(f"  {name:28s} n={len(w):3d}  "
              f"w=[{w.min():.4g},{w.max():.4g}]  "
              f"G'=[{gp.min():.4g},{gp.max():.4g}]  "
              f"tan_d@low_w={td[0]:.4f}  spread={np.ptp(np.log10(td)):.2f} dec")

    # Report the limitation loudly, computed not assumed.
    lens = {len(v["Gp"]) for v in dataset.values()}
    if len(lens) == 1:
        arrs = [v["Gp"] for v in dataset.values()]
        if all(np.array_equal(a, arrs[0]) for a in arrs):
            print("\n  NOTE: G' is identical across all temperatures (one "
                  "traced curve). See module docstring - vertical/b_T signal "
                  "and per-T G' scatter are absent by construction.")
    else:
        print("\n  NOTE: G' arrays differ in length across temperatures; the "
              "shared-trace check was only applied where lengths match.")

    save_npz(OUT, dataset)
    print(f"\nwrote {OUT}  ({len(dataset)} temperatures)")


if __name__ == "__main__":
    main()
