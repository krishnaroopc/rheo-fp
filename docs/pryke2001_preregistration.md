# Pre-registration: what `star` should do on Pryke 2001

**Written 2026-09-11, BEFORE any Pryke curve has been digitized or fitted.**
Committed ahead of the data deliberately. This project has three times written
a plausible claim into its notes ahead of the measurement and been wrong
(`Z_BOUNDS`' floor, the "zimm-style ties" reading of the MM1998 misses, and the
n=200 agreement verdict), and once fixed it by pre-registering
(`9b51840`, the third agreement seed, which then landed in the ambiguous band
and was reported as such). This is that habit applied to the next dataset.

**Do not edit the predictions below after seeing results.** Record outcomes in
a separate "OUTCOME" section underneath, and let the diff show what was wrong.

---

## The dataset

`originals/ma010350l.pdf` — Pryke, Blackwell, McLeish & Young,
*Macromolecules* **35**, 467-472 (2002), doi:10.1021/ma010350l.
Four symmetric **three-arm 1,2-polybutadiene** star melts, plus their
hydrogenated poly(1-butene) analogues. Master curves at **333 K**, Figures 2
(parent) and 3 (hydrogenated), roughly 1e-3 to 1e6 s^-1.

Z is known independently from the paper's own tables, not fitted:

| sample | arm M_w | Z = M_a/M_e (parent, M_e=3550) | Z (hydrogenated, M_e=6100) |
|---|---|---|---|
| A | 11 300 | **3.2** | 1.9 |
| B | 24 100 | **6.8** | 4.0 |
| C | 38 900 | **11.0** | 6.4 |
| D | 78 600 | **22.1** | 12.9 |

Table 2 also gives G_0 = 0.765 MPa and tau_e = 1.02e-5 s for the parent
(0.510 MPa / 2.04e-5 s hydrogenated). The hydrogenated M_e was FITTED by the
authors, not taken from literature, and they flag it as well below Fetters'
9536 — so treat hydrogenated Z as the less trustworthy column.

## Scope of this prediction

Predictions are made for the **parent 1,2-polybutadiene set (Figure 2)** only.
The hydrogenated set is a secondary target; if it gets digitized, these
predictions do NOT transfer to it unchanged, because its M_e is fitted and its
Z values sit lower.

## What is being tested

Whether `star` survives a change of chemistry. Every existing star validation
is polyisoprene (MM1998) or polyisobutylene (Santangelo). Polybutadiene is
independent, and the class has never seen it.

---

## PREDICTIONS

### P1 — the primary claim

**`identify()` returns `star` for samples C (Z 11.0) and D (Z 22.1).**

Reasoning: these sit squarely inside the band where the class has worked on
real data. MM1998 was 5/5 on curves that reach terminal flow, with decisive
margins (dAICc 93-225 at rms 0.024-0.041), and its successful arms span
Z = 2.2-9.4. C and D are comparable or better entangled, and the paper's own
Figure 2 shows both with a well-developed plateau and a visible terminal
upturn.

**Confidence: high for D, moderate for C.** See P4 for the condition that
would legitimately excuse a miss.

### P2 — the low-Z samples are NOT expected to work

**Samples A (Z 3.2) and B (Z 6.8) may return anything, and A in particular is
expected to fail or to win only on parsimony.**

This is not hedging after the fact — it is the class's documented envelope.
Below Z ~ 4 the fitting cost is FLAT in Z (Ueff(1) is 1-2 k_BT and the
activated time sits under a decade above the arm's own Rouse time), so there is
no star-specific shape left to measure. On MM1998 the Z = 2.2 arm won by only
dAICc 4.8 with its rms tied to `branched`.

**Independent corroboration that this is real and not a defect of my
implementation:** the paper reaches the same boundary from the other side. Its
Conclusions say the low-M_a samples "show the largest deviation from the data
curves... This may be due to the marginal degree of entanglement, with
s = 3.2". Two different routes, one boundary.

So: **A failing is NOT a regression and must not be reported as one.** B is
genuinely uncertain.

### P3 — `Z` will be recovered badly, and must not be reported

**Fitted Z will be biased high, likely by tens of percent, on every sample.**

On MM1998 it ran +17-84%. Nothing about this dataset changes the cause. `Z` is
already a non-reportable output and this prediction does not make it reportable
— it exists so that a bad Z is not mistaken for a new problem.

**Corollary:** do NOT tune anything to make Z come out better on this dataset.
That would be fitting the bound to the test set.

### P4 — `terminal_reached` is the predictor, not Z

**Any sample whose digitized window does not reach terminal flow may fail in
EITHER direction, and the score should be reported split on
`terminal_reached`, exactly as MM1998's was.**

This is the measured operating envelope: 5/5 where flow is observed, 1/5 where
it is not, and all four real-data failures across MM1998 + Santangelo sit on
the non-terminal side, including a LINEAR control returned as `star`.

**This matters more than usual here because the master curves are
time-temperature superposed over ~9 decades.** How much of the terminal zone
survives depends entirely on where the digitizing stops. Check
`features["terminal_reached"]` and the low-frequency slopes BEFORE scoring a
curve as a miss — a truncated trace is a digitizing artefact, not a class
failure.

### P5 — the likely wrong answer, if there is one, is `branched`

**Misses are expected to go to `branched` (BSW), not to zimm/rouse.**

That is what absorbed 25/30 planted stars before the class existed, and it is
what took both MM1998 misses (dAICc 57 and 103). A miss landing somewhere else
— `reptation`, a sticker class — would be genuinely surprising and worth
investigating rather than shrugging at.

### P6 — the two brains

**The neural head is expected to agree with `identify()` on C and D.**

Weak prediction, stated because it is cheap and falsifiable. Note the standing
caveat: the network scored `star` at 0.996 on synthetic data but the pooled
synthetic measurements show `star -> branched` disagreements running with the
PHYSICS side right, so agreement here is corroboration and not proof.

---

## What would count as a genuine problem

Ranked, so a bad result is not over- or under-read:

1. **`star` loses on C or D at a decisive margin (dAICc > 20) WITH terminal
   flow observed.** That would mean the class does not transfer across
   chemistry, which is the whole question this dataset was chosen to answer.
2. **A miss lands somewhere other than `branched`** (see P5).
3. **Fitted G_N comes out far from the paper's own G_0 = 0.765 MPa** on a
   well-entangled sample. G_N is the plateau LEVEL, not the curve maximum
   (G' rises above it at high frequency since the arm-Rouse term was added),
   so compare against the plateau, not the peak.

## What would NOT count as a problem

- A (Z 3.2) failing — predicted in P2, and corroborated by the paper itself.
- Z recovered badly — predicted in P3.
- Any curve failing where `terminal_reached` is False — predicted in P4;
  report it split, do not score it as a flat miss.

---

## OUTCOME

**Run 2026-09-11 (office PC), after digitizing Figure 2's two well-entangled
panels.** Nothing above this line was edited. Data: `data/pryke2002.npz` via
`scripts/prep_pryke2002.py`; two samples, `PBD3_Ma38k` (Z 10.96) and
`PBD3_Ma78k` (Z 22.14). `identify(n_restarts=12)`.

### Result table

| sample | Z_true | winner | dAICc over 2nd | rms (star) | rms (branched) | fitted G_N | fitted Z | fitted tau_e |
|---|---|---|---|---|---|---|---|---|
| PBD3_Ma38k | 10.96 | **star** | 170.0 (branched) | 0.0361 | 0.0720 | **0.776 MPa** | 13.57 (+24%) | 2.78e-5 s |
| PBD3_Ma78k | 22.14 | **star** | 86.8 (branched) | 0.0882 | 0.1244 | **0.731 MPa** | 31.51 (+42%) | 3.66e-5 s |

Paper's own values: G_0 = 0.765 MPa, tau_e = 1.02e-5 s.

### Scoring against the predictions

**P1 — HELD, on both samples.** `star` wins C (Z 11.0) and D (Z 22.1) at
dAICc 170 and 87, with rms 50% and 29% better than `branched`. These are
decisive wins of the MM1998 mid-band kind, not the Z = 2.2 parsimony tie.
**The class transfers to a third chemistry** (PBD, after PI and PIB), which is
the question this dataset was chosen to answer.

**P2 — NOT TESTED.** Samples A and B were not digitized (recommended scope was
Figure 2's two well-entangled panels only). No claim either way.

**P3 — HELD exactly.** Z biased **+24%** and **+42%**, inside the +17-84%
band measured on MM1998. Nothing was tuned. `Z` remains non-reportable.

**P4 — THE PREDICTION'S PREMISE FAILED, AND THIS IS THE MAIN FINDING.**
`terminal_reached` is **False for BOTH samples**, and `star` was nonetheless
**correct on both**. That directly contradicts the 1/5 hit rate on the
non-terminal side that P4 was built from (MM1998 + Santangelo, n=10).

The feature is not tracking what its name suggests here. `PBD3_Ma38k` has
low-frequency slopes **1.87 / 0.85** against the 2.0 / 1.0 melt limit, and
G''/G' = **33** at its lowest raw point — that curve unambiguously flows, and
`terminal_reached` still reads False. `PBD3_Ma78k` is the genuinely marginal
one: slopes 0.35 / 0.17, with the G''/G' crossover falling exactly ON its
lowest digitized point (ratio 1.17, confirmed against Figure 2 by the user —
the published window stops there; this is not a truncated trace).

So the honest statement is: **`terminal_reached` False did not predict failure
on this dataset, and the 5/5-vs-1/5 split does not generalise as stated.**
Two readings remain open and this run cannot separate them:
  (a) the feature is stricter than "flow observed" — plausibly it wants
      sustained 2/1 asymptotes over a run of points, and these are TTS master
      curves interpolated onto a 60-point grid across ~8 decades; or
  (b) the real envelope is narrower than the feature and these two curves sit
      inside it for another reason.
**Do not "fix" the feature on the strength of n=2.** What is now established
is that the envelope claim in CLAUDE.md and next-actions is overstated and
must be requalified, not that the feature is wrong.

Note this cuts AGAINST the class's own caveat: `challenge()` emits the star
window caveat whenever the winner is `star` and `terminal_reached` is False,
so it fires on both of these — on two curves where the call is right and
G_N lands within 4% of the paper's. The caveat is still correctly grounded
(it says the evidence is thin, not that the answer is wrong), but its hit
rate on real stars is now 2 false alarms out of 2 here.

**P5 — HELD.** `branched` is the runner-up on both samples, as predicted. No
miss occurred, so the prediction is only weakly exercised, but the ordering is
exactly what P5 said it would be.

**P6 — FAILED, on both samples, and sharply.** The neural head says
`branched` (p = 0.983) on Ma38k and `cured_elastomer` (p = 0.986) on Ma78k.
Both are **confident** with **abstain_p ~ 0.00**, and `agreement()` classes
both as the sharp **`disagree`** kind, not `disagree_ranked`.

Read carefully, because the pooled synthetic statistics say a disagreement
roughly halves BOTH sides' reliability (0.945 -> 0.438 physics, 0.937 ->
0.426 neural) and that which brain degrades more is NOT stable. Here the
physics side carries external corroboration the network does not: it recovered
the paper's own G_0 to within 1.4% / 4.4% from a free fit. So on this dataset
the physics side is the right member of the pair — but that is an
after-the-fact reading supported by outside knowledge, which is precisely how
the shortlist is meant to be used, and it must NOT be generalised into
"trust physics on a split".

`cured_elastomer` at p = 0.986 on a melt that visibly flows is worth keeping
as a specimen: the network's confidence is trained only against its own errors
on the synthetic distribution, so it has no way to flag a real curve whose
shape sits off that distribution.

### Against the "genuine problem" list

1. **`star` loses on C or D at dAICc > 20 with flow observed** — did not
   happen; `star` won both decisively.
2. **A miss landing somewhere other than `branched`** — no miss.
3. **Fitted G_N far from the paper's G_0 = 0.765 MPa** — did not happen, and
   this is the run's strongest positive result: **0.776 MPa (+1.4%)** and
   **0.731 MPa (-4.4%)**, from three free parameters that never saw that
   number. Independent corroboration of the modulus scale on a new chemistry.

**One item outside the pre-registered list, recorded because it is a real
mismatch:** fitted `tau_e` is **2.78e-5 / 3.66e-5 s** against the paper's
**1.02e-5 s** — factors of **2.7 and 3.6**. `star.py`'s docstring says a fit
landing "within a factor of two on the time scale is behaving exactly as
published" (the paper's own section-V residual factors are ~1.6 in modulus and
~2 in time), so this sits just outside that band while the modulus sits well
inside it. Not predicted, not a failure of any stated criterion, and n=2.
Flagged for the next star dataset rather than acted on.

### Net

The primary claim held and the modulus corroboration is better than expected.
The prediction that failed is P4's premise, which was the project's own
confidence about where this class works — the envelope is looser than
"terminal_reached True", at least on TTS master curves. That requalification is
the result worth carrying forward; the 2/2 hit rate is n=2 and should not be
quoted as an accuracy.
