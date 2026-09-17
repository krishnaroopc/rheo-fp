# Pre-registration: a noise-aware tie rule for model selection

**Written 2026-09-17, BEFORE the rule is implemented or run.** The diagnostic
measurements below were made first and are reported honestly, including the one
that contradicts the motivating hypothesis. No tie rule exists in the code yet.

**Do not edit the predictions after seeing results.** Record outcomes in an
OUTCOME section underneath and let the diff show what was wrong.

---

## What prompted this

Katzarova 2018's three monodisperse linear polystyrenes are textbook entangled
linear melts. With the Likhtman-McLeish tube model in the bank and the
`wide_plateau` discard removed, `identify()` returns `branched` on all three,
with `reptation` second every time:

| sample | Z | reptation rms | branched rms | gap | dAICc |
|---|---|---|---|---|---|
| PS392 | 29.5 | 0.0314 | 0.0250 | 0.0064 | 50.7 |
| PS206 | 15.5 | 0.0300 | 0.0261 | 0.0039 | 28.9 |
| PS105 | 7.9 | 0.0222 | 0.0207 | 0.0015 | 12.1 |

`branched` is BSW, k=5; `reptation` is k=3. The AICc arithmetic was verified by
hand and reproduces from the residuals alone - `k=5` is correctly registered and
correctly paid for. **Nothing is broken.** This is AICc doing exactly what it is
specified to do.

## The measurement that killed the original hypothesis

The motivating claim was "branched wins inside the digitization noise, so the
difference is not evidence." That is **FALSE as a general statement**, and it
must not be quoted.

Digitization scatter, measured as the residual of each curve about a local
quadratic in log-log (G' and G'' are smooth by construction, so point-to-point
wiggle is reading error):

| curve | scatter (decades) |
|---|---|
| PS392 | 0.0022 |
| PS206 | 0.0019 |
| PS105 | 0.0089 |
| HM / HL / ML | 0.0060 / 0.0062 / 0.0118 |
| Pivokonsky E / B | 0.0009 / 0.0018 |

So the gaps above sit at **2.9x / 2.1x / 0.17x** the per-curve scatter. Only
PS105 is genuinely inside the noise. On PS392 and PS206, `branched` fits better
by an amount that is real and resolvable.

A free 12-mode Prony floor was also computed and is **NOT used**: it moves
non-monotonically with mode count (PS105: 0.047 at 12 modes, 0.139 at 16),
which is NNLS conditioning rather than a noise measurement. Recorded so it is
not mistaken for a validated number later.

## What this means, stated plainly

The honest reading is NOT "the tie rule will fix the classification." It is:

**BSW genuinely fits a real linear melt better than the correct tube model
does, by a margin larger than the measurement error, on 2 of 3 curves.**

CLAUDE.md currently asserts BSW's "intrinsically broad spectrum cannot fake a
sharp reptation terminal, so AICc still separates it from the linear-melt
class." These three curves **falsify that claim** and it must be corrected
whatever the outcome here.

A tie rule is therefore being tested as a *partial* measure, on its own merits,
not as a fix for the 0/3.

## The rule to be implemented

Within `identify()`'s ranking, treat two candidates as tied when their rms
residuals differ by less than the curve's own estimated digitization scatter,
and break such ties by parsimony (lower k), then by rank order.

- The scatter estimate is computed per curve by the local-polynomial method
  above, not by a global constant.
- The rule applies ONLY to the top of the ranking; it never promotes a model
  that is not already within scatter of the leader.
- `identify()`'s return contract is unchanged; a tie-break is recorded in the
  result so `report.py` can say a tie was broken and why.

## Predictions, pre-registered

**P1 (primary).** The rule changes the winner on **PS105 only** (gap 0.17x
scatter). PS392 and PS206 stay `branched`. Final Katzarova monodisperse score
becomes **1/3, not 3/3**. *If this lands 3/3, the rule is too aggressive and
must be rejected, not celebrated.*

**P2 (must not break).** The 6/6 real-data benchmark stays 6/6. In particular
both Pivokonsky LDPE curves stay `branched` - they are real branched material
with scatter 0.0009/0.0018, so nothing should tie there.

**P3 (must not break).** MM1998 stars stay 5/7 and Pryke 2002 stays 2/2. Any
loss here means the rule is cannibalising a validated capability, and it is
rejected.

**P4 (cannibalisation).** On planted synthetic curves, n=30/class, identical
seeds before and after: no class loses more than 1 curve, and overall accuracy
does not fall. Measured BY HOW MUCH, not just whether the winner changed - the
flaw that made the comb check misread in the first place.

**P5.** The rule fires rarely. On synthetic data it changes the winner on
**under 5%** of curves. A rule that fires often is a rule that has replaced
AICc, which is not what is being authorised.

## Rejection criteria, fixed in advance

The rule is REJECTED and reverted if any of: P2 fails; P3 fails; P4 fails;
P5 exceeds 10%; or P1 lands 3/3 (which would indicate the threshold is
absorbing real signal rather than noise).

## What this does not address

Even on full success this leaves `branched` out-fitting correct physics on
PS392 and PS206 by a resolvable margin. That is a separate, deeper problem -
either BSW is too flexible for the bank, or the tube model is still missing
something real on well-entangled melts. It is NOT addressed here and must not
be reported as addressed.
