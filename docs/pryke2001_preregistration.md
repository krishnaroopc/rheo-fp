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

*(empty — to be filled in after the data exists and the fits are run. Do not
edit anything above this line.)*
