# A second independent LDPE, and the correction it forces

**Measured 2026-09-21.** The user objected — correctly — that the claim
"a CORRECT `branched` call also violates the `n_e` range" rested on **one
dataset** (Pivokonsky's E and B), and that one dataset was carrying the whole
argument against making the plausibility checks eliminate candidates.

## The second dataset, and why it needed no digitizing

**Verbeeten, Peters & Baaijens (2001), *J. Rheol.* 45, 823, TABLE III** —
already in the repo at `originals/archive/verbeeten2001_extended_pompom.pdf`,
archived under the 2026-07-04 XPP scope decision and overlooked since.

Table III tabulates a **6-mode Maxwell spectrum** for **BASF Lupolen 1810H
LDPE at 150 °C**, derived by the authors from a continuous relaxation spectrum
of Hachmann (1996):

| i | G_0,i (Pa) | λ_0b,i (s) |
|---|---|---|
| 1 | 2.1662e4 | 1.0000e-1 |
| 2 | 9.9545e3 | 6.3096e-1 |
| 3 | 3.7775e3 | 3.9811e0 |
| 4 | 9.6955e2 | 2.5119e1 |
| 5 | 1.1834e2 | 1.5849e2 |
| 6 | 4.1614e0 | 1.0000e3 |

Σg_i = 3.649e4 Pa; τ spans 4.0 decades.

**A Prony spectrum gives G*(ω) exactly**, so this is a literature-exact LVE
curve with **no figure digitizing and no reading error** — a better class of
evidence than a digitized master curve. It is also genuinely independent of
Pivokonsky: different resin (Lupolen 1810H vs the Pivokonsky melts), different
laboratory, different decade, and a different characterisation route
(continuous-spectrum inversion rather than direct SAOS).

Lupolen 1810H/1840H is the standard substitute for the **IUPAC A** LDPE
reference, so this is about as canonical as real LDPE gets.

## >>> THE RESULT, AND IT CORRECTS ME <<<

BSW fitted to this curve (60 points, ω = 1e-3..1e2 rad/s, 40 restarts,
seed 0), with the `n_e` ceiling progressively widened:

| n_e ceiling | fitted n_e | fitted n_g | rms (decades) |
|---|---|---|---|
| **0.90 (shipped)** | **0.6295** | 0.8115 | 0.10798 |
| 0.95 | 0.6056 | 0.8113 | 0.10821 |
| 1.20 | 1.0794 | 0.7978 | 0.10564 |
| 2.00 | 2.0000 ← at | 0.7995 | 0.10177 |

**At the shipped bound, `n_e` = 0.63 — comfortably INSIDE both the bound and
the 0.10–0.80 literature range.** It does **not** pin, and the range check
would stay **quiet** on this curve.

### What this changes

1. **"Real LDPE always violates the range" is WRONG, and I asserted it.** It
   is true of Pivokonsky E and B and false of Lupolen 1810H. Corrected here
   and wherever it was stated as general.

2. **The n=1 objection was right.** One dataset was carrying a
   load-bearing argument. With n=2 the picture is that LDPE *can* sit inside
   the range, so the Pivokonsky behaviour is a property of **those two
   curves** — not of branched melts, and not of the `branched` class as such.

3. **It correspondingly WEAKENS my objection to the elimination loop.** The
   "it would break your only real branched validation" argument now applies
   to Pivokonsky only, and does not generalise to LDPE. That objection is
   still real (Pivokonsky is committed real data and elimination would break
   both curves) but it is narrower than I claimed.

4. **A caution that cuts the other way, though:** `n_e` here rises to 1.08 and
   then 2.00 as the ceiling is lifted, with rms improving monotonically
   (0.10798 → 0.10177). So BSW *wants* to leave its physical range on this
   curve too — the shipped bound is simply not tight enough to catch it. The
   underlying over-flexibility is reproduced on the second dataset even
   though the flag does not fire.

5. **The rms is poor: 0.108 decades**, against 0.062/0.056 on Pivokonsky and
   ~0.02 on well-fitted real curves. BSW fits this canonical LDPE noticeably
   worse. Read with care, since this curve is a 6-mode Prony reconstruction
   rather than raw measurement, and a 4-decade window over a 4-decade
   spectrum crops both ends.

## Status

**Not added to `data/` and not wired into any test.** It is a measurement that
corrects a claim, recorded so the correction is not lost. Converting it into a
committed dataset would be a reasonable next step — it is cheap, since the
numbers are exact — but it is a scope decision, not something to slip in
during a measurement.

## Other candidates found, not yet pursued

* **Hachmann (1996)** and **Kraft (1996)** theses — the primary
  characterisations behind Table III (shear and elongation at 150 °C).
* **IUPAC A LDPE** — Meissner (1972, 1975), Münstedt & Laun (1979). The
  classic reference LDPE; Verbeeten also fits it, so a second tabulated
  spectrum may exist in the same EPAPS supplement
  (E-JORHD2-45-013104) they cite for the other two materials.
* **Statoil 870H HDPE** — also in Verbeeten §IV, useful as a *linear*
  polyethylene control against an LDPE.
* Kessner/Münstedt and Wagner's HMMSF papers on LDPE melts carry LVE master
  curves, but as figures needing digitizing.

---

# The Statoil 870H HDPE control, and why it is NOT a fourth BSW data point

Same paper, **TABLE IV**: a 7-mode Maxwell spectrum for **Statoil 870H HDPE at
170 °C**, also exact numbers. A *linear* polyethylene, so it looked like a free
control — if `branched` beat `reptation` on a linear PE, that would be the BSW
fault reproduced on a fourth independent linear melt.

**First pass looked damning:** `identify()` returns **`branched` at weight
1.000, ΔAICc 216 over `reptation`**, with both safety checks firing
(`n_e` = 0.90, at the ceiling).

**>>> But it does NOT support that reading, and the confound check is the
reason. <<<** Before claiming it, two things were tested — both of them my own
doing rather than the data's:

1. **Was the window mine?** `reptation`'s rms of 0.2357 is far worse than the
   ~0.03 it achieves on Katzarova, which smelled like cropping.
2. **Is the material actually monodisperse-linear?**

Measured across five windows:

| window (rad/s) | reptation rms | branched rms | winner |
|---|---|---|---|
| 1e-4 … 1e2 | 0.2357 | 0.0941 | branched |
| 1e-3 … 1e2 | 0.1618 | 0.0503 | branched |
| 1e-2 … 1e3 | 0.2264 | 0.0254 | branched |
| 1e-4 … 1e3 | 0.2842 | 0.1092 | branched |
| 1e-5 … 1e1 | 0.2334 | 0.0385 | branched |

**`reptation` fits badly in EVERY window (0.16-0.28); `branched` fits well in
all of them (0.025-0.109). So it is not a window artifact — and that is
exactly why it cannot be used as a BSW data point.**

The spectrum spans **5.7 decades in τ and 4.2 decades in modulus**. A
monodisperse linear melt's is ~1-2 decades. Verbeeten say outright that this
resin is "very elastic", that "it is difficult to identify a satisfying
relaxation spectrum", and that its spectrum came from **creep**, not SAOS.
Commercial HDPE is polydisperse.

**Conclusion: this is a broad, polydisperse commercial resin, and `branched`
winning is arguably the HONEST answer rather than the fault.** The label
"HDPE = linear = should be `reptation`" was my own assumption from the
chemistry, not something the data supports. Recorded because the reasoning is
the reusable part: **"linear chemistry" does not imply "monodisperse linear
melt", and a broad commercial resin is not a control for the BSW fault.**

It does, however, sharpen a different question — see below.

## >>> WHAT THESE TWO MATERIALS TOGETHER SUGGEST <<<

Not "BSW is a bad branched model". Something more awkward:

* canonical LDPE (Lupolen): BSW fits at rms **0.108** — poorly;
* Pivokonsky LDPE: `n_e` pinned at its ceiling, chasing 2.0 when freed;
* Katzarova monodisperse linear PS: `branched` beats the CORRECT physics 3/3;
* polydisperse HDPE: `branched` wins, and that is probably right.

The common thread is that **`branched` wins whenever the spectrum is BROAD**,
and breadth is produced by long-chain branching AND by polydispersity AND by
comb/star architectures alike. That is a statement about what SAOS can
resolve, not about BSW's functional form.

**So the open question is not only "is there a better branched model?" but
"is `branched` an identifiable ARCHITECTURE class from SAOS at all, or is it
really a REGIME (broad spectrum) that several architectures share?"** If the
latter, no forward model fixes it, and the honest fix is a reporting one:
say "broad spectrum — consistent with long-chain branching or with
polydispersity; SAOS alone cannot separate them" instead of asserting
`branched`. Note the project already retired a "model-only tier" that did
something like this (2026-09-07), on evidence that did not include any of the
four measurements above.

**That is a SCOPE decision for the user, not a code change to make
unilaterally.** Nothing here has been acted on.
