# Pre-registration: a PER-MODEL restart budget

Written 2026-09-19, **before the convergence measurement was read**, per the
project's protocol. Commit this before any outcome exists.

## The question

`identify()` fits all ten candidates with `N_RESTARTS = 12`. That is one global
number, and it is necessarily set by the HARDEST search in the bank. Measured
2026-09-18: `reptation` is **94.2%** of a call (4940 forward evaluations x
10.67 ms of 56.0 s); the other nine cost ~0.03 ms/call. The full suite now
takes **3 h 47 m**, ~17x the 13:34 recorded for the same PC on 2026-09-09.

So the lever is not "lower `N_RESTARTS`" - `scripts/check_restart_count.py`
asks that, and `.claude-notes/next-actions.md` already records the criticism
that it is **bank-wide and therefore mis-aimed**: it would risk all ten
searches, including the k=5 models that may genuinely need 12, to save under a
second on eight of them.

The right lever is a **per-model budget**: keep 12 where the search is hard,
lower it only where the fit is measurably already converged. `fit_model`
already takes `n_restarts` per call, so this is a lookup, not a redesign.

## Why this is a science change, not a speed change

Restarts exist so a multimodal objective is not scored at a local minimum. Cut
them too far and a model's fit gets WORSE, its AICc rises, and **a different
class wins**. That error is invisible: it looks like an ordinary result. The
`comb` and TDD episodes are the precedent - both were rejected precisely
because a better-fitting wrong answer is the project's characteristic failure.

So the budget must be set from a measured convergence point, per model, and
gated on the criteria below.

## What will be measured first (no criteria attached, this is just input)

`scripts/measure_restart_convergence.py`: for each model, fit at
n_restarts = 1,2,3,4,6,8,12 and find the smallest arm whose rms matches the
12-restart rms to within rtol 1e-6, over several planted curves per class plus
the real benchmark curves.

## The budget rule, FIXED NOW

For each model, the budget is **twice its measured convergence point, floored
at 4 and capped at 12**:

    budget(model) = clip(2 * conv(model), 4, 12)

The 2x is deliberate headroom against curves not in the measurement set, and
the floor of 4 means no model is ever cut to the bone however easy it looks on
the sample. A model whose convergence point is not reached at 12 on ANY tested
curve keeps 12. **This formula is fixed before the numbers are read so the
budget cannot be reverse-engineered from a desired speedup.**

## Pre-registered criteria - do NOT renegotiate after seeing numbers

ADOPT the per-model budget only if ALL THREE hold:

- **P1 - no flipped winners.** On n=30 planted cropped noisy curves per class,
  identical seeds in both arms, every curve's winning class is unchanged
  against the 12-restart reference. A single flip fails P1: the premise is
  that these searches are ALREADY converged, so any change disproves it.
- **P2 - real data holds.** The 6/6 literature benchmark is unchanged, AND the
  three Katzarova monodisperse melts return the same class at a dAICc within
  1.0 of the 12-restart value. (The second half is new and deliberate: the 6/6
  set contains no monodisperse linear melt, the blind spot that hid the broken
  `reptation` approximation for most of the project's life.)
- **P3 - the margins are unchanged.** For every curve in P1, |dAICc(winner,
  runner-up) at the budget - the same at 12| <= 1.0. A winner that survives on
  a collapsed margin is a regression the winner-only check would miss - this is
  exactly the flaw found in `check_comb_cannibalisation.py`, which "scored only
  WHETHER the winner changed, never BY HOW MUCH".

## Veto conditions

Any one kills the change:
1. P1, P2 or P3 fails and cannot be fixed by RAISING the budget of the
   offending model (raising is allowed; the formula is a starting point, not a
   floor to defend).
2. The measured saving on the full suite is under 2x. Below that the risk to
   the science is not worth it, and the honest answer is "the cost is the tube
   model, go fix that instead".

## What is NOT being changed

- `N_RESTARTS = 12` stays as the DEFAULT for any model without an entry, and
  as the explicit value callers can still pass. The change is additive.
- No forward model, bound, or bank membership is touched.
- `scripts/check_restart_count.py` is left in place. Its bank-wide question is
  superseded, not deleted; its criteria P1/P2 are the ancestors of these.

---

# OUTCOME (2026-09-19): **VETOED by criterion 2. Nothing was changed.**

Measured by `scripts/measure_restart_convergence.py`. The criteria above were
committed at `f833426` before these numbers were read.

## The convergence table

Smallest restart count whose rms matches the 12-restart rms to rtol 1e-6,
over 3 planted curves per class:

| model | conv points | worst | budget | cost @12 |
|---|---|---|---|---|
| zimm | 1, 8, 1 | 8 | 12 | 0.05 s |
| rouse_screened | 12, 1, 8 | **12** | 12 | 0.04 s |
| reptation | 8, **12**, 2 | **12** | 12 | **68.58 s** |
| sticky_rouse | 1, 6, 3 | 6 | 12 | 0.20 s |
| sticky_reptation | 1, 3, **12** | **12** | 12 | 0.45 s |
| cured_elastomer | 1, 1, 1 | 1 | 4 | 0.05 s |
| critical_gel | 1, 1, 1 | 1 | 4 | 0.03 s |
| wormlike_micelle | 1, 1, 2 | 2 | 4 | 0.11 s |
| branched | **12**, 4, 1 | **12** | 12 | 0.65 s |
| star | 6, 2, 1 | 6 | 12 | 1.26 s |

Applying the pre-registered formula `clip(2*conv, 4, 12)`:

    TOTAL at 12 restarts: 71.42 s
    TOTAL at the budget:  71.29 s
    SPEEDUP: 1.00x  ->  veto condition 2 (saving < 2x) TRIGGERED

## Why it fails, and it is not a near miss

**`reptation` needs 12 restarts on its own planted curves.** It is 96% of the
cost (68.58 s of 71.42 s) and its worst convergence point is the maximum
tested, so the one model that matters keeps its full budget. Every model the
formula does cut - `cured_elastomer`, `critical_gel`, `wormlike_micelle` -
costs **under 0.11 s**. The change saves 0.13 s of a 71 s call.

This is not fixable by tuning the formula. Even zeroing the budget of all nine
cheap models entirely would leave 68.58 s of 71.42 s, a ceiling of **1.04x**.

## The follow-up check that closed the door properly

The convergence table alone would have been a WEAK reason to stop, and an
earlier draft of this outcome overstated it. Two corrections, both measured:

**(i) "`reptation` needs 12 restarts" is an ARTIFACT of the rtol.** On the
three REAL Katzarova melts it converges at 1-2 restarts with EXACTLY zero
penalty:

    PS392   1:0.03155  2:0.03155  4:0.03155  ... 12:0.03155   penalty 0 everywhere
    PS206   1:0.02984  2:0.02984  4:0.02984  ... 12:0.02984   penalty 0 everywhere
    PS105   1:0.02215  2:0.02045  4:0.02045  ... 12:0.02045   converged by 2

The "12" came only from PLANTED curves, where the 4-restart rms penalty is
~3e-4 to 2.8e-3 decades - an order of magnitude BELOW `tube.py`'s own 1.3e-2
sampling noise. **RTOL = 1e-6 measures convergence far more tightly than the
forward model can resolve**, which is a flaw in the instrument, not a property
of the search. That briefly looked like it rescued a `reptation`-only cut.

**(ii) It does not. The sub-noise rms penalty MOVES THE DECISION.** Scoring
the full `identify()` winner and margin at 4 vs 12 restarts:

| curve | @4 | @12 | |d(dAICc)| |
|---|---|---|---|
| PS392 (real) | branched 51.56 | branched 51.58 | 0.01 |
| PS206 (real) | branched 26.67 | branched 27.69 | **1.02** |
| PS105 (real) | reptation 7.21 | reptation 7.21 | 0.00 |
| planted 0 | reptation 25.89 | reptation 6.79 | **19.10** |
| planted 3 | reptation 61.67 | reptation 29.06 | **32.61** |
| planted 6 | **branched 17.26** | **star 1.74** | **15.52** |
| planted 7 | reptation 102.76 | reptation 118.12 | **15.36** |

**P1 FAILS: 1 flipped winner in 8** (planted curve 6, `star` -> `branched`).
**P3 FAILS: margins swing by up to 32.6 AICc units**, and even a real curve
(PS206) moves 1.02, just over the threshold.

This is the finding worth keeping. A ~1e-3-decade rms difference - well under
the forward model's own noise - propagates into **tens of AICc units** and can
change the reported class. The rms looks converged; the DECISION is not. Any
future check that scores restarts (or any other approximation) on fit quality
alone will therefore certify a change that silently moves classifications.
**Score the winner and the margin, never the rms.**

Note the direction of the flip: at 4 restarts `reptation`'s own planted curve
was won by `branched`. That is the standing BSW fault being made WORSE by a
cheaper search - exactly the "good fit of the wrong class" failure mode this
project's protocol exists to catch.

## Two findings that outlive the rejected change

1. **The "cheap" models are NOT easy searches.** `rouse_screened` needed all
   12 restarts on one curve, `zimm` 8, `sticky_reptation` 12, `branched` 12.
   The naive version of this idea - cut restarts bank-wide because `reptation`
   dominates runtime - would have quietly damaged the two weakest classes in
   the bank (zimm/rouse_screened, already 58% of all remaining error and weak
   only against each other). Their optimiser difficulty is presumably the same
   degeneracy as their classification difficulty. **Do not lower `N_RESTARTS`
   bank-wide on the intuition that the k=3 models are trivial.**
2. **The cost is `tube.py`, and only `tube.py`.** Three independent routes now
   agree: 89.5% (2026-09-18 profile), 94.2% (this session's per-candidate
   instrumentation), 96% (this cost table). No scheduling or budgeting change
   can touch it. Speeding up `identify()` REQUIRES making the Likhtman-McLeish
   forward model cheaper or calling it less, and TDD-DR was the attempt at the
   former and failed on accuracy (`docs/tdd_preregistration.md`).

## What is left for item (c)

The remaining levers are all inside `reptation` itself, and none is free:

- **Fewer forward calls per restart** - a cheaper optimiser, analytic
  gradients, or a coarser convergence tolerance. Untested.
- **A cheaper `tube.Gstar`** - already had its two brute-force loops replaced
  by closed forms (2026-09-17, 4x). `R_of_t`/`_prony_modes` is ~70% of what
  remains and is the Monte-Carlo constraint-release sampler, so making it
  cheaper and making it LESS noisy pull in opposite directions - and the noise
  is already above the margins the bank adjudicates (open item (b)).
- **Caching** - `identify()` refits from scratch every call; the test suite
  refits the same planted curves repeatedly. A fixture-level cache would cut
  suite time without touching the science at all. **This is now the ONLY
  remaining lever that cannot move a classification**, because it changes no
  arithmetic - it returns the identical result, just once instead of n times.
  Everything else on this list is an approximation, and the P1/P3 result above
  shows this pipeline converts sub-noise approximation error into tens of AICc
  units. Recommended next, and it is a TEST-harness change, not a product one.

## Consequence if adopted

`synth.py` does NOT import `n_restarts`, and the neural checkpoint is not
affected, so unlike the tube-model swap this does not stale the checkpoint or
any accuracy figure. It changes only how long `identify()` takes and - if the
criteria hold - nothing else.
