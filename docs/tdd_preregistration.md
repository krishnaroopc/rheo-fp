# Pre-registration: replacing `reptation`'s forward model with TDD-DR

Written 2026-09-18, **before any fit was run**, per the project's
cannibalisation protocol. Commit this file before the outcome exists.

## What is being proposed

`identify()`'s `reptation` candidate currently calls `model_reptation_lm` ->
`tube.Gstar`, the verbatim Likhtman-McLeish (2002) tube model. The proposal is
to replace the forward model with the **des Cloizeaux time-dependent diffusion
(TDD) kernel under double reptation (DR)**, as specified in van Ruymbeke &
Keunings (2002, Macromolecules 35, 2689) Table 1 eq 4 + eqs 1/5, and restated
in Chaudhuri & Lele (2020, J. Rheol. 64, 1) eqs 1-5.

## Why

1. **Cost.** Measured 2026-09-18: `identify()` spends **94.2% of its runtime in
   `reptation` alone** (4940 forward calls x 10.67 ms = 52.7 s of a 56.0 s
   call). Every other candidate costs ~0.03 ms/call. TDD is closed-form:
   measured **0.053 ms/call** via a Prony ladder, a **~210x** speedup, which
   would take `identify()` from ~56 s to ~3.5 s.
2. **Determinism.** `tube.R_of_t` Monte-Carlo samples `LM_NCHAINS = 20` chains.
   Its ~1.3e-2 decade sampling noise exceeds AICc margins the bank decides on -
   this is what forced the PS105 requalification to be WITHDRAWN on 2026-09-18.
   TDD has no sampling at all, so that entire failure mode disappears.
3. **Published preference.** van Ruymbeke section V concludes TDD+DR
   "performs better than the fluctuations relaxation function" on
   well-entangled chains, and is "the only model that is able to correctly
   predict the intermediate region between reptation and Rouse relaxation."

## Parameterisation (fixed in advance)

- Bank vector stays **(log10 Ge, log10 tau_d, Z)**, so **k = 3 is unchanged**
  and AICc stays comparable to every other candidate. This is the same
  contract `model_reptation_lm` already honours.
- `beta = 2.25`, NOT 2. van Ruymbeke fit this consistently across all their PS
  samples (section IV) and p.2698 attributes it to multi-chain entanglements.
  Fixed, not fitted.
- `M*/Me = 8.7`, the paper's own best-fit value **for polystyrene** (p.2698).
  Fixed, not fitted, justified by the paper's explicit statement that "the
  quality of the fit is not very sensitive to the exact value of M*". Note it
  is chemistry-dependent (20 for PC, 47 for PE) - recorded as a known limit,
  not silently ignored.
- `H = M/M* = Z * (Me/M*)`, so H is derived from Z, introducing no new
  parameter.

## KNOWN LIMIT, recorded before measuring

van Ruymbeke section "Relaxation of Short Chains" (p.2694): TDD-DR relaxes
chains below **~4 Me** TOO FAST, a documented failure they patch with an
admittedly empirical tau_rept -> tau_rept/beta rescale below 4 Me. Katzarova's
shortest chain is Z = 7.9, comfortably above 4, so the benchmark below does not
probe this. **If TDD is wired in, the empirical short-chain correction is NOT
included in the first version** - it would be an unvalidated patch. Any future
low-Z melt is out of the validated envelope.

## Pre-registered predictions

Judged against the three Katzarova 2018 monodisperse polystyrenes
(`data/katzarova2018.npz`, true Z = 29.5 / 15.5 / 7.9), plus the standing 6/6
real-data benchmark.

- **P1 (forward validity).** The TDD forward model reproduces the shape
  invariants an entangled linear melt must have: terminal slopes 2.0/1.0 to
  within 0.02, a plateau that increases monotonically with Z, and a single G''
  minimum. PASS/FAIL.
- **P2 (parameter recovery).** On planted noiseless curves, TDD recovers a
  planted Z to within **15%** across Z = 8..40. This is the bar `tube.py`
  clears (28.9/16.0/9.6 against 29.5/15.5/7.9 = -2%/+3%/+22%). FAIL if worse
  than 25%.
- **P3 (real linear melts).** On Katzarova's three PS curves, TDD's rms is
  **no worse than `tube.py`'s by more than 0.005 decades** (tube: 0.0314 /
  0.0300 / 0.0222). TDD need not WIN; it must not lose materially.
- **P4 (the BSW fault - the real question).** `branched` (BSW) currently beats
  the correct physics on ALL THREE Katzarova melts (dAICc 50.7 / 28.9 / 12.1).
  **No prediction is registered that TDD closes this.** It is recorded as the
  question the experiment asks, with three possible outcomes stated in advance
  so none can be rationalised after the fact:
    - (a) TDD wins some/all -> the fault was partly the forward model's
      inaccuracy, and the finding is a genuine improvement.
    - (b) TDD loses all three by a similar margin -> the fault is confirmed to
      be about BSW's flexibility, NOT about reptation's accuracy. This is a
      USEFUL negative result and must be reported as such, not buried.
    - (c) TDD loses by a LARGER margin -> TDD is worse physics here despite
      being faster, and the swap should be rejected on accuracy.
  Outcome (b) does **not** by itself veto the swap, because the speed and
  determinism gains stand on their own; outcome (c) does veto it.
- **P5 (no cannibalisation).** Standard protocol: n=30 planted cropped noisy
  curves per class, identical seeds both banks. No class may lose more than
  2 curves, and the 6/6 real-data benchmark must hold at 6/6. Any `reptation`
  margin under ~1e-2 decades is to be treated as noise per the standing rule.

## Veto conditions (any one kills the swap)

1. P3 fails: TDD is materially worse than `tube.py` on real monodisperse PS.
2. P4 outcome (c).
3. P5 fails: the 6/6 benchmark drops, or any class loses >2 of 30.
4. TDD wins a linear melt for the WRONG reason - i.e. it also outfits a curve
   it should not (the `comb` veto precedent: the c6bb-PS linear control). The
   analogue here: TDD must NOT start absorbing `star` or `branched` curves.

## What happens to `tube.py` either way

`tube.py` is **retained regardless of outcome**. It is validated Batch 2 work,
it is the reference the TDD implementation is checked against, and it remains
the honest answer to "which model?" if TDD is rejected. `model_reptation` (the
old hand-rolled approximation) also stays as-is.

---

# OUTCOME (recorded 2026-09-18, after the runs)

**VERDICT: the swap is REJECTED. `tube.py` stays as the shipped `reptation`.**
`rheofp/models/tdd.py` is retained as a validated forward model, not wired
into the bank. Measured by `scripts/check_tdd_vs_tube.py`; numbers in
`docs/tdd_vs_tube_2026-09-18.json`.

## P1 — PASS

24 tests in `tests/test_tdd.py`. Terminal slopes 2.00/1.00 to <0.02, plateau
monotone in Z, a single G'' minimum, exact `Ge`/`tau_rep` scaling contracts.
Two real bugs were caught by validation rather than by inspection:

1. **The finite-difference Prony ladder was wrong.** `g_i = -diff(G)` conserves
   mass but misplaces it and does NOT converge (N=96 -> 1536 moved G' by 0.09
   decades and kept drifting). Against a referee of direct oscillatory
   quadrature of the exact definition, it was off by 0.12-0.30 decades. NNLS
   matches to <1e-4. Geometric-midpoint placement did not help. The referee is
   now a permanent test.
2. **The bare TDD kernel has no Rouse rise** - G'' decays as w^-0.23 where
   `tube.py` turns up, and has NO G'' minimum at any Z. van Ruymbeke add Rouse
   separately by an explicit linear mixing rule (p.2692, Table 2 eq 8); without
   it a fitter distorts Z to cover the gap, the failure already diagnosed in
   `star.py`.

## P2 — PASS, decisively

Planted-parameter recovery: **exact** noiseless (|Z err| 0.0% at Z = 8..40),
and **max 2.1%, median 0.6%** under 2% multiplicative noise. Better than
`tube.py`, which reaches +22% on its shortest chain.

## P3 — **FAIL on 2 of 3.** This is a veto condition.

| sample | TDD rms | tube rms | diff | bar |
|---|---|---|---|---|
| PS392 | 0.0471 | 0.0315 | **+0.0155** | FAIL |
| PS206 | 0.0383 | 0.0298 | **+0.0085** | FAIL |
| PS105 | 0.0209 | 0.0205 | +0.0005 | OK |

The bar was +0.005 decades. TDD is materially worse than the incumbent on the
two longer chains. Checked and NOT a fitting artifact: 10/30/60 restarts give
identical answers to 4 decimals.

**METHOD CORRECTION, recorded because the first run of this comparison was
wrong.** The first version of `check_tdd_vs_tube.py` used a hand-rolled
multi-restart loop instead of `identify()`'s own `fit_model`. That made EVERY
model look worse - `reptation` 0.0446/0.0422 and `branched` 0.0353/0.0369,
against 0.0315/0.0298 and 0.0250/0.0261 through the shipped fitter - and did
not reproduce the project's recorded numbers. The table above is through
`fit_model` and DOES reproduce them (tube 0.0315/0.0298 vs the recorded
0.0314/0.0300; tube-BSW +51.6/+27.7 vs the recorded 50.7/28.9). **The verdict
was the same either way**, but the numbers are only quotable from this run.
General rule: score through the shipped fitter, never a local reimplementation.

## P4 — outcome **(c)**, the vetoing one

dAICc = TDD - BSW, positive means BSW still wins (lower AICc wins):

| sample | TDD - BSW | tube - BSW |
|---|---|---|
| PS392 | **+147.7** | +51.6 |
| PS206 | **+87.6** | +27.7 |
| PS105 | -1.7 | -7.2 |

TDD does not close the BSW fault; it makes the margin **~3x worse** on the two
longer chains. Pre-registered outcome (c) - "TDD is worse physics here despite
being faster" - and (c) was registered in advance as a veto.

(PS105's -1.7 is inside the ~1e-2-decade noise band the standing rule says to
distrust for `reptation` margins, and is not claimed as a win.)

## The near-miss that makes this worth writing down

`M*/Me` fixed at the paper's PS value of 8.7 is what binds. Freeing it (k=4)
gives rms 0.0316 / 0.0335 / 0.0285 and **beats BSW 3/3** at dAICc -28.7 /
-25.6 / -8.9. That looks like the result the project has been chasing since
2026-09-17, and it must NOT be taken:

- `M*/Me` **pins to its upper bound at 60.0** on both long chains. The paper's
  value for PS is 8.7; 47 is PE's, for a polymer with Me = 1500 rather than
  18500. A parameter that runs to its bound is not identified by the data, it
  is absorbing misfit.
- **Z error blows up from +4.6%/+6.5% to +50.2%/+60.4%.** The fit buys its rms
  by destroying the one physical quantity the class exists to report.

That is winning by flexibility while wrecking the physical parameter - the
exact failure for which `comb` was vetoed (it fit the LINEAR control c6bb-PS
better than any real comb), and the exact shape of the BSW fault itself. Taking
it would be adopting the disease as the cure. **Not done.**

## What was gained anyway

- **The speed diagnosis stands and is the durable finding**: `identify()`
  spends **94.2%** of its runtime in `reptation` alone (4940 calls x 10.67 ms).
  Any future speedup must target that one candidate; nothing else matters.
- The honest speed number for TDD is **~8x**, not the ~210x first probed - that
  probe used the ladder that turned out to be wrong.
- `tdd.py` + 24 tests are a validated, deterministic, published-model
  implementation available if a POLYDISPERSE or BLEND class is ever built,
  which is TDD-DR's actual strength (Chaudhuri & Lele's whole paper) and is
  the standing open question Katzarova's three blends represent.
- A reusable referee: quadrature of the exact definition catches ladder bugs
  that every shape test passes.

## Consequence if adopted

`synth.py` imports the same registry, so the GENERATOR changes too and the
**neural checkpoint goes stale** - every accuracy figure in CLAUDE.md would
predate it and a retrain is required before any of them can be quoted again.
This is the same situation the 2026-09-17 tube.py swap created.
