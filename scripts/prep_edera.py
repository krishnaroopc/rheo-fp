"""Convert the digitized Edera (2024) epoxy-vitrimer SAOS panels to npz.

Source: Edera, Chappuis, Cloitre & Tournilhac, "Resolving the relaxation
complexity of vitrimers: time-temperature superpositions of a time-temperature
non-equivalent system", Polymer (2024); preprint arXiv:2401.10569.

Figure 3a-d is the reason this paper was chosen: it plots RAW, UNSHIFTED
per-temperature frequency sweeps, which almost every vitrimer paper omits in
favour of a master curve alone. Fig 3g is the TTS master curve built from them
and is deliberately NOT digitized - a pre-shifted curve is exactly what the
stack resolver must not be handed.

Caption: "Raw data from SAOS tests performed at T = 180 C, 85 C, 75 C, 30 C,
from right to left in the range of angular frequencies [0.01-100 rad/s]."

Panel -> temperature was confirmed against the moduli themselves (user
confirmed 2026-09-07), since the caption orders curves, not panel labels:

    a  180 C   G' 8-9 MPa      tan_d 0.028   rubbery plateau
    b   85 C   G' 10-200 MPa   tan_d 0.667   alpha-relaxation (tan_d peak)
    c   75 C   G' 50-700 MPa   tan_d 0.500   transition
    d   30 C   G' ~1 GPa       tan_d 0.010   glassy

G' rises monotonically as T falls and tan_d peaks in b, consistent with the
paper's statement that G' drops around 80 C. Reading the panels the other way
would make the material stiffen on heating, which is unphysical.

Two caveats recorded with the data rather than discovered later:

1. This material is THERMO-RHEOLOGICALLY COMPLEX by the paper's own central
   claim - two relaxations with different activation energies (glassy ~680
   kJ/mol, vitrimeric ~130 kJ/mol), so time-temperature EQUIVALENCE fails.
   rheofp's resolve_melt_vs_network assumes one horizontal shift aligns the
   spectra. That assumption is violated here on purpose: the point is to see
   what the resolver does when its premise does not hold, not to hand it an
   easy case.

2. The 30 C panel is GLASSY (G' ~1 GPa). The glassy regime was dropped from
   the taxonomy, so that curve is out-of-scope material and is kept as an
   out-of-distribution probe for the report layer, not as a classification
   target.

Frequencies are already rad/s - no Hz conversion.

Run: python scripts/prep_edera.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from rheofp.io.data import save_npz

SRC = "originals/edera2024.xlsx"
OUT = "data/edera2024.npz"

# panel -> (temperature in C, short note). Confirmed against the moduli.
PANELS = {
    "a": (180.0, "rubbery plateau, bond exchange active"),
    "b": (85.0, "alpha-relaxation, tan_delta peak"),
    "c": (75.0, "glass-to-rubber transition"),
    "d": (30.0, "glassy - OUT OF TAXONOMY, kept as an OOD probe"),
}
CELSIUS_TO_K = 273.15


def main():
    df = pd.read_excel(SRC)
    dataset = {}
    for panel, (temp_c, note) in PANELS.items():
        # Panels have unequal length (a and d carry one point fewer), so drop
        # per-column rather than per-row - a shared dropna would truncate the
        # longer panels to the shortest.
        w = df[f"{panel}_w_rads"].dropna().to_numpy(float)
        gp = df[f"{panel}_G'_Pa"].dropna().to_numpy(float)
        gpp = df[f"{panel}_G''_Pa"].dropna().to_numpy(float)
        n = min(len(w), len(gp), len(gpp))
        if not (len(w) == len(gp) == len(gpp)):
            print(f"  ! panel {panel}: ragged columns "
                  f"({len(w)}/{len(gp)}/{len(gpp)}) - truncating to {n}")
        w, gp, gpp = w[:n], gp[:n], gpp[:n]

        order = np.argsort(w)
        w, gp, gpp = w[order], gp[order], gpp[order]
        good = np.isfinite(w) & np.isfinite(gp) & np.isfinite(gpp) & (w > 0) \
            & (gp > 0) & (gpp > 0)
        w, gp, gpp = w[good], gp[good], gpp[good]

        name = f"Edera2024_{temp_c:.0f}C"
        dataset[name] = dict(omega=w, Gp=gp, Gpp=gpp,
                             T_K=temp_c + CELSIUS_TO_K)
        print(f"  {name:20s} n={len(w):3d}  "
              f"w=[{w.min():.4g},{w.max():.4g}] rad/s  "
              f"G'=[{gp.min():.3g},{gp.max():.3g}] Pa  "
              f"tan_d={np.median(gpp / gp):.3f}   {note}")

    save_npz(OUT, dataset)
    print(f"\nwrote {OUT}  ({len(dataset)} temperatures)")


if __name__ == "__main__":
    main()
