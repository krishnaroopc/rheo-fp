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

## Consequence if adopted

`synth.py` does NOT import `n_restarts`, and the neural checkpoint is not
affected, so unlike the tube-model swap this does not stale the checkpoint or
any accuracy figure. It changes only how long `identify()` takes and - if the
criteria hold - nothing else.
