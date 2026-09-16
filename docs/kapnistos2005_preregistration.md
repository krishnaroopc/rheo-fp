# Pre-registration: what `comb` should do on Kapnistos 2005

**Written 2026-09-16, BEFORE any Kapnistos curve has been fitted.** The data
were digitized, unit-checked and plotted first (that is how the two sheet
defects below were found), but `fit_comb`, `identify()` and the neural head
have not been run on a single one of these nine curves, and will not be until
this file is committed.

This matters more here than on any previous dataset. `s_a`, `s_b` and `phi_b`
are all computable from the paper's Table 1, so a post-hoc reading would be
worth nothing — I could compute them, then "predict" them. The Pryke
pre-registration (`docs/pryke2001_preregistration.md`) is the template and the
precedent; it landed partly wrong and was left standing, which is the point.

**Do not edit the predictions below after seeing results.** Record outcomes in
a separate "OUTCOME" section underneath, and let the diff show what was wrong.

---

## The dataset

`originals/ma050644x.pdf` — Kapnistos, Vlassopoulos, Roovers & Leal,
*Macromolecules* **38**, 7852–7862 (2005), doi:10.1021/ma050644x.
Model comb homopolymers: a linear backbone with ~17–31 grafted linear
branches. Two chemistries, two figures, nine digitized curves
(`data/kapnistos2005.npz`, committed).

| sample | chem | M_b | M_a | q | s_a | s_b | φ_b | s_b·φ_b | decades |
|---|---|---|---|---|---|---|---|---|---|
| c6bb-PS | PS | 275k | — | — | — | 16.2 | 1.00 | 16.2 | 8.35 |
| c612-PS | PS | 275k | 6.5k | 31 | **0.38** | 16.2 | 0.577 | 9.34 | 8.34 |
| c622-PS | PS | 275k | 11.7k | 30 | **0.69** | 16.2 | 0.439 | 7.11 | 9.15 |
| c632-PS | PS | 275k | 25.7k | 25 | **1.51** | 16.2 | 0.300 | 4.85 | 8.97 |
| c642-PS | PS | 275k | 47k | 29 | 2.76 | 16.2 | 0.168 | 2.72 | 8.94 |
| c652-PS | PS | 275k | 98k | 29 | 5.76 | 16.2 | 0.088 | 1.43 | 6.37 |
| lc3-PBd | PBd | 50k | 7k | 17 | 3.86 | 27.5 | 0.296 | 8.15 | 11.25 |
| lc1-PBd | PBd | 50k | 11.3k | 18 | 6.23 | 27.5 | 0.197 | 5.44 | 10.31 |
| lc2-PBd | PBd | 50k | 23.2k | 17.8 | 12.78 | 27.5 | 0.108 | 2.98 | 9.34 |

M_e = 17 000 (PS) / 1815 g/mol (PBd), T_ref = 170 °C / 0 °C, all from p.7853.
φ_b here is `s_b/(s_b + q·s_a)`, the comb form; note `comb.py`'s
`phi_b_from_architecture` uses the **H-polymer** `s_b/(s_b + 2q·s_a)` with
`Q_FIXED = 2`, which is wrong for a q≈30 comb and must not be used to score
these (see P6).

**Bold `s_a` values sit below `S_A_BOUNDS`' floor of 2.0** — three of the six
PS combs have unentangled branches and are *unfittable in principle* by the
current bounds. That is a pre-existing, deliberate floor mirroring
`star.py`'s, and it is not to be quietly widened to make this dataset look
better. See P5.

## What is being tested

**Not** "does `comb` fit combs". The live question is the one from
2026-09-14: `comb` is built, tested and deliberately **out** of `identify()`'s
bank because wiring it in took `star` from 5/7 to 4/7 on MM1998 and collapsed
its margins from ΔAICc 194–225 to 7.6–27.4. This dataset is the real comb
evidence that was named as the precondition for revisiting that.

---

## PREDICTIONS

### P1 — the primary claim

**With `comb` wired in, `identify()` returns `comb` for at least 5 of the 6
entangled-branch samples** (c642-PS, c652-PS, lc1-PBd, lc2-PBd, lc3-PBd, and
c632-PS at s_a 1.51 as the marginal sixth).

Reasoning: these have `s_a` at or above the floor, `s_b·φ_b` from 1.4 to 8.2,
and the digitized curves show the two-plateau structure the model predicts.
**Confidence: moderate.** This is the first real comb data the class has seen;
every prior validation is ML1999's own figures and planted parameters.

### P2 — the control is the decisive test, and it cuts the other way

**`c6bb-PS`, the linear backbone, must NOT be returned as `comb`.**
It should come back `reptation` (most likely) or `branched`.

This is the strongest single test in the dataset: same figure, same
instrument, same lab, same chemistry, differing from the combs *only* in
architecture. A model with k=5 that labels a linear melt a comb is a model
that wins by flexibility, and **a `comb` call on c6bb-PS is on its own
sufficient grounds to leave the class unwired**, whatever P1 does.

**Confidence: moderate-to-low that it passes.** `branched` (BSW, k=3) already
absorbs things it should not, and c6bb-PS has an 8.35-decade window with real
high-frequency structure for a 5-parameter model to chase.

### P3 — the star cannibalisation must not recur

**Re-running MM1998's seven stars and Pryke's two with `comb` wired in must
leave `star` at ≥ 5/7 on MM1998 AND keep the surviving margins above
ΔAICc 50.** That is `test_star.py`'s existing assertion, and it is not to be
lowered to accommodate this.

Prediction: **it will still fail.** The 2026-09-14 measurement was 4/7 with
margins at 7.6–27.4, and nothing in `comb.py` has changed since. Real comb
data does not, by itself, fix a comb-impersonates-star problem.

**This is the prediction I most expect to be proved right and most want to be
wrong.** If P1 passes and P3 fails, the answer is not to wire it in anyway —
it is P6.

### P4 — parameter recovery will be poor, and that is expected

**Fitted `s_a`, `s_b`, `φ_b` will NOT match the architectural values**, and
should be reported as recovered-to-order-of-magnitude at best. Specifically I
predict **median |s_a error| > 50%** across the six entangled samples.

Reasoning: `comb.py`'s own docstring already records ML1999's Table 2 fitting
φ_b at 0.63 against a chemistry value of 0.13, and s_a at 16 against 27 — the
*authors* could not recover these from their own data. A three-way degeneracy
among `s_a`, `s_b`, `φ_b` and `tau_e` is documented there.

**Consequence, pre-committed: `s_a`, `s_b` and `φ_b` are NOT reportable
outputs**, exactly as `Z` is not for `star`. The class may say "comb"; it may
not say "with 29 branches of 6 entanglements each". Note the number of
branches `q` is not a parameter at all — it is fixed at `Q_FIXED = 2`.

### P5 — the three unentangled-branch combs are excluded in advance

**c612-PS (s_a 0.38), c622-PS (0.69) and c632-PS (1.51) sit below
`S_A_BOUNDS[0] = 2.0` and are excluded from P1's score**, except c632-PS which
P1 names as a marginal sixth.

They are *predicted to fail*, and failure there is **not** evidence against the
class — it is the floor doing its job. The paper itself says c612 and c622
"exhibit a single rubbery plateau", i.e. no comb signature to find.

**Do NOT widen `S_A_BOUNDS` to catch them.** That floor rests on the same
measurement as `star.py`'s Z floor of 4: below a couple of entanglements the
retraction barrier is under a few k_BT and there is no architecture-specific
shape left. Widening it after seeing this data would be exactly the
threshold-tuning this project pre-registers against.

### P6 — the real question: is there a physical separator?

Task item 5 asks whether a **physical** restriction separates `comb` from
`star` without a tuned threshold. The two candidates with a basis:

1. **Require an entangled cross-bar**: `s_b·φ_b ≥ 1` (already present as
   `S_B_PHI_MIN`). All nine samples pass, so this does **not** discriminate
   here and I predict it is **insufficient** on its own.
2. **Require the two-feature signature** — an arm shoulder AND a separate
   cross-bar peak — which a star cannot produce, having no cross-bar.

**Prediction: (2) is the one that works**, because it rests on a positive
observation (two features *seen*) rather than an absence. But it must be
checked against the project's own pre-filter principle: a discard is sound
only when it rests on a positive observation. "No second peak → not a comb"
is the `has_shoulder` missing-evidence fallacy again and **must not be
implemented as a discard**. It may gate *adding* `comb` to the ballot; it may
never remove another class.

I also predict the merged-peak regime bites: `comb.py` records two resolved
maxima at φ_b ≤ 0.40 and three at φ_b ≥ 0.50. **Seven of the nine samples
have φ_b ≤ 0.40**, so most of this dataset sits in the merged regime where the
two-feature test is hardest to apply.

### P7 — the two-brain signal

The network has **never seen a comb** (`synth.py` does not generate the class;
the checkpoint is 10-class). So on all nine curves the neural head must be
read as out-of-distribution, and a confident low `abstain_p` means nothing —
the documented OOD blind spot.

**Prediction: the two brains disagree on a majority (≥ 5/9).** If instead they
agree confidently on a wrong class, that is the "good fit of the WRONG class"
mode again and should be recorded as such.

---

## Scoring rules, fixed in advance

- **Baseline first**: score all nine with `comb` **absent**, before wiring
  anything in. Expect confident wrong answers (synthetic measurement:
  `branched` 12/30, `critical_gel` 10/30, `star` 6/30).
- P1 scores over the six entangled samples only, per P5.
- P2 is pass/fail on one curve and can veto on its own.
- P3 is measured with `scripts/check_comb_cannibalisation.py`, which now
  reports margins and includes `REAL_CLASS_VALIDATION` — the two flaws that
  made the 2026-09-14 reading wrong.
- A tie on rms at equal k goes to the **lower** k, and is recorded as a tie,
  not a win. `star` joined the zimm/rouse degenerate cluster that way.
- If P1 passes and P3 fails, the decision is **not** to wire in. It is to
  build P6's separator, or to leave `comb` out and keep the honest note that
  an uploaded comb is confidently misidentified.

## Known defects in the digitized source, recorded before scoring

Both found by plotting before fitting, both corrected in
`scripts/prep_kapnistos2005.py` rather than by re-digitizing, so the raw sheet
stays as the user produced it:

1. **Fig1a's G′ and G″ columns are swapped** (terminal slopes read 1.0/2.0 as
   labelled; 1.95–2.15 / 0.77–1.09 swapped). Fig2a's are not.
2. **The caption's decade shifts are descending and it lists five factors for
   six samples.** The ladder that collapses the data is 1e5→1 (Fig1a) and
   1e2→1 (Fig2a).

The independent check on both: after unshifting, plateau moduli land at
1.94–2.43e5 Pa (PS, lit. 2.0e5) and 1.09–1.26e6 Pa (PBd, lit. 1.15e6) — values
the correction never saw. c632/c642-PS read *low* (0.16x, 0.31x) after the
G′/G″ overlap crop moves the tan-δ minimum onto the **diluted backbone**
plateau G_b rather than G_N. That is the paper's own Figure 4 effect and is
itself weak evidence for the two-plateau structure P6 depends on.

## OUTCOME

*(empty — to be filled after the measurements, without editing anything
above)*
