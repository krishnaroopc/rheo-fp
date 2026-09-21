# The eliminating-loop idea: measured verdict

**Read-only measurement, 2026-09-21. Nothing was changed.**
Script `scripts/check_plausible_runner_up.py`; raw output
`docs/elimination_loop_measurement_2026-09-21.txt`.

## The proposal (the user's, verbatim in substance)

> after you try 10 classes, it predicts class 3. but you then verify using the
> safety checks and realize 3 is impossible or wrong (maybe Class 2 and 7
> also). then you try again, but only on the remaining 7 classes, pick that
> winner, and run the verification, and so on until everything gives you green
> lights?

It is a better design than the penalty-weight approach it replaced: no
arbitrary weight to tune, just "eliminate the impossible and re-rank."

**Implementation note worth keeping:** this is **one pass down the ranking**,
not an iterative loop. Each candidate's AICc depends only on its own fit to
the data, not on which other candidates are present, so eliminating a class
and re-ranking simply promotes the next survivor — it never reshuffles the
order of the ones that remain. Same answer, ~10x less compute.

## Result: +2 curves net

Measured over the 21 real curves with an independently known truth (the
`data/*.npz` sets; Santangelo's L176/HM/HL/ML are LINEAR controls, so their
truth is `reptation`, not `star`).

| | count |
|---|---|
| currently WRONG | 7 |
| … which elimination **FIXES** | **4** |
| … still wrong after elimination | 3 |
| currently RIGHT | 14 |
| … which elimination **BREAKS** | **2** |
| **net** | **+2** |

### The 4 it fixes — all the same failure

| curve | truth | winner now | after elimination |
|---|---|---|---|
| Katzarova PS206 | reptation | branched | **reptation** |
| MM1998 PI4_Ma95k | star | branched | **star** |
| MM1998 PI4_Ma105k | star | branched | **star** |
| Santangelo S217 | star | branched | **star** |

Every one is `branched` absorbing another architecture, flagged by `n_e`
driven to its floor, with the TRUE class sitting immediately behind it. This
is the BSW over-flexibility fault, and elimination genuinely corrects it where
the flag fires.

### The 2 it breaks — and this is the cost

| curve | truth | winner now | after elimination |
|---|---|---|---|
| Pivokonsky E | branched | **branched** (correct) | zimm |
| Pivokonsky B | branched | **branched** (correct) | zimm |

Both real LDPE melts. `branched` is CORRECT there and is flagged anyway (the
documented `n_e = 0.90` ceiling defect), so elimination discards the right
answer — and the next plausible candidate is **`zimm`, an unentangled
dilute-solution model.** Not a near-miss: a physically absurd fallback.

**That is the decisive objection, and it is not about accounting.** A tool
that answers "unentangled polymer solution" for a branched polyethylene melt
is worse than one that answers "branched" with a warning attached, even though
the arithmetic says +2.

### The 3 it cannot help

`PS392` (the strongest single case of the BSW fault — `n_e` lands interior, no
flag), `S490` (interior, rms 0.0140), and `L176` (a linear control returned as
`star` from an interior vector). The checks are silent on all three, so no
amount of elimination reaches them.

## Verdict

**Do not ship the eliminating version.** Three reasons, in order of weight:

1. **It converts correct answers into absurd ones.** +2 net is not worth
   "branched LDPE → unentangled solution" on committed real data.
2. **It violates the project's own positive-observation rule.** A range
   violation is not an observation about the sample — it is the fitter
   failing, and that has two causes ("wrong class" and "right class, imperfect
   model"). Pivokonsky is the standing proof that the second cause is real.
   `rheo-fp` already removed two discards (`has_shoulder`, `wide_plateau`) for
   exactly this, and removing the first took a class from 18/30 to 29/30.
3. **It always terminates with an answer.** Handed material outside the bank
   (a comb), it eliminates down to whatever survives — and that survivor looks
   *more* trustworthy than today's wrong answer because it has green lights.
   That manufactures false confidence for the OOD case, already the tool's
   biggest blind spot.

**What IS worth keeping from the idea** — and it is most of it:

> Do not eliminate. **Re-rank and report the sequence.** "Best fit:
> `branched`, but its numbers are implausible. Best fit with plausible
> numbers: `reptation`."

That points all four catches at a specific named alternative instead of a
vague warning, costs nothing on Pivokonsky (which still reports `branched`
first), needs no ranking change and no retraining. The measurement above
already supplies the content for it — the `first-plausible` column IS that
second line.

**Not built.** `rheo-fp` is being paused; this is recorded for whoever picks
it up, and the same design question arises in `rheolyzer`, where a per-axis
output may dissolve it entirely (breadth and architecture stop competing for
one label).
