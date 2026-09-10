# rheo-fp — Project Context

Read `.claude-notes/` for evolving facts, decisions, and preferences —
including `.claude-notes/sessions.md`, a dated journal of past working sessions.
**Append a short entry to that journal at the end of each working session** so
context carries across PCs.

**When the user says "continue" / "pick up where we left off" / "do the next
thing" (esp. on a different PC), read `.claude-notes/next-actions.md` first** —
it's the live cross-PC to-do list with the current active task and decisions
already made.

## Cross-PC workflow (important)
User works from multiple PCs (home + office). Git is the sync layer:
- **Pull before starting**, commit + push before leaving a machine. Only
  committed work is visible on the other PC.
- Reconstruct "what changed on the other PC" from `git log` / `git diff`.

**On a machine where `git` or `uv` is "not recognized", or `.venv/` is
missing, you are on a fresh/formatted PC — go straight to the
">>> BOOTSTRAP A FRESHLY-FORMATTED WINDOWS PC <<<" section at the top of
`.claude-notes/environment.md`.** It lists exactly what to install (git, uv,
VS Code — NOT Python, uv manages that), the clone URL, and which
"broken"-looking things are expected. The **laptop was wiped and reinstalled
with Windows 11 on 2026-09-09**, so it needs that path on its next session.

## Environment — reproducible, DO NOT loosen
The env is locked for **identical versions across PCs** (user requirement — no
dependency issues, computer-agnostic):
- Managed by **uv**; **Python pinned to 3.12**; exact deps+hashes in `uv.lock`.
- Fresh PC: install uv, then `uv sync`. Run things with `uv run …`
  (e.g. `uv run pytest`).
- `.venv/` is per-machine (gitignored) — recreate it, never commit it.
- Full details, including how to change dependencies, in
  `.claude-notes/environment.md`.

## What this is
An open-source ML classifier for linear rheology. Ingests small-amplitude
oscillatory shear (SAOS) data — G′(ω), G″(ω) — and outputs (1) material type
identification and (2) fitted constitutive model parameters. Python / NumPy /
SciPy / PyTorch, shipped as the installable `rheofp` package (the original
Jupyter notebooks are archived local-only in `originals/` and are no longer the
working form — see Goals below, all three are complete).

## SCOPE — what "material type" means here (user, 2026-09-04)
**This classifies MOLECULAR / microstructural architecture, not macroscopic
material category.** The target distinctions are the ones a person cannot make
by looking at the sample: linear melt vs long-chain-branched melt; entangled vs
unentangled; permanently crosslinked elastomer vs dynamically crosslinked
vitrimer; cured network vs critical gel; good vs theta solvent (Zimm vs Rouse).
A foam, a paste, a yield-stress emulsion is obvious on sight and is NOT the
problem this tool is for.

Consequences, which are easy to get wrong:
- **Do not spend effort detecting macroscopically obvious out-of-scope
  material.** Time was spent on exactly that on 2026-09-04 before the scope was
  clarified; see next-actions §1j for the (negative) result so it is not
  repeated.
- The out-of-distribution material that DOES matter is molecularly distinct but
  macroscopically ordinary: **polymer blends, block copolymers, semicrystalline
  melts, star polymers, filled/nanocomposite melts.** None are in the taxonomy.
- The **temperature stack is not one open item among several — it is the
  load-bearing capability**, because it is the ONLY thing that separates a
  dynamic network (vitrimer) from a permanent one (cured elastomer). See §3.
- An explanation of WHY a class was chosen is not a nicety here. With a foam a
  user can referee the answer by looking at the jar; with elastomer-vs-vitrimer
  they cannot, so the reported evidence has to do the refereeing.

## Classifier architecture (FROZEN — do not redesign)
- **Input**: set-based stacks of spectra (multiple curves across temperature
  or concentration). Single-curve input is the degenerate N=1 case via masked
  attention pooling. Stacks enable classification from trends across T or c.
- **Output**: two heads. Head 1 emits material type, with abstention when the
  input lacks discriminating information. Head 2 always emits a best-fit model.
- **Taxonomy (design)**: 3 regimes (Terminal/liquid-like, Solid/gel-like,
  Yield-dominated); 8 fine classes (4 identifiable from single curves, 4
  requiring stacks); 6 model-only classes (regime-level labels only).
  Glassy regime was dropped.
- **Taxonomy (as actually built)**: **10 generated fine classes** (zimm,
  rouse_screened, reptation, sticky_rouse, sticky_reptation, cured_elastomer,
  critical_gel, wormlike_micelle, branched, star); **2 regimes** (terminal,
  solid). The Yield-dominated regime has no physics and therefore no training
  data. Five model-only classes from the design were never built. Do not quote
  the design numbers as if they were implemented.
  **`identify()`'s bank holds TEN**, matching the generator exactly — `star`
  was added to the bank and then to `synth.py` on 2026-09-09, so both sides and
  `ml.dataset.CLASSES` now carry the same ten. The bank-coverage invariant
  below is enforced by a test in both directions.
- **The model-only tier no longer exists (retired 2026-09-07, user decision).**
  `wormlike_micelle` and `branched` were the only two, they were never actually
  coerced to regime level by any code, and both now stand as ordinary fine
  labels — the classifier says "your sample is branched". Evidence: BSW fits
  real LDPE to ~0.06 decades with errors landing on physically adjacent classes
  (zimm/rouse, not reptation); wormlike_micelle measured 40/40 self-correct and
  drew no wrong answers from any other class (n=40/class, 2026-09-07).
  Linear-vs-branched is a standard LVE diagnostic, so reporting it is within
  what SAOS supports. `MODEL_ONLY_CLASSES` is deleted from both `synth.py` and
  `identify.py`; `ALL_CLASSES == FINE_CLASSES`.

## Completed & validated work (forward physics, three batches)
Each model was validated by reproducing published figures and recovering
planted parameters before being trusted.

**Batch 1 — Maxwell/Prony family**: single-mode Maxwell; multi-mode Prony;
sticky-Maxwell with Arrhenius temperature-tying (one shared forward serves
both associating networks and vitrimers via different parameter binding);
practical wormlike micelle.

**Batch 2 — tube models**: Likhtman–McLeish (2002) implemented verbatim —
μ(t) reptation+CLF, R(t) Rubinstein–Colby constraint release via Sturm
sequence, eq. 19, Prony-based Fourier transform. Vectorized Sturm sequence +
cached Prony modes gave ~10–22× speedup; never recompute modes per frequency
point. Also hierarchical double-reptation branched/LCB spectrum
(`branched_spectrum`; superseded for classification by the BSW spectrum —
see the branched-class note below).
Critical constraint: linear melt curves must stay inside the valid frequency
window or G″ exceeds G_e unphysically.

**Batch 3 — polymer solutions**: two-layer architecture — spectral shape
layer (Zimm/Rouse/reptation) plus concentration-scaling layer with exponents
verified against Colby (2010) and Dobrynin–Colby–Rubinstein (1995).
Polyelectrolyte c-stack discriminator confirmed: relaxation time decreases
with c in the unentangled regime, is c-independent when entangled.
No single model spans dilute→entangled; fitting is regime-aware against a
candidate model bank.

**Solution identifier** (`solution_identifier.ipynb`): regime-aware pipeline —
permissive signature-feature pre-filter → multi-restart L-BFGS-B fitting in
log space → AICc ranking with Akaike weights → none-of-the-above floor via
FLOOR_CHI2. Lesson learned: aggressive pre-filter pruning caused
misclassification; keep the pre-filter permissive and let AICc resolve.

**Pom-pom** (`rheofp/models/pompom.py`): LVE-validated against the real target,
Pivokonsky, Zatloukal & Filip (2006, J. Non-Newt. Fluid Mech. 135, 58), two
LDPE melts at 200 °C (data/pivo2006.npz; originals/ has the source xlsx +
paper PDF, local-only). fit_maxwell recovers both melts' G'/G'' to < 0.02
decades. Nonlinear XPP parameters (q_i, λb/λs, α_i) are transcribed from the
paper's Tables 2/3 and assembled by build_xpp_table(), but were fit by the
paper against nonlinear flow data (extensional/shear viscosity, normal stress
coefficients) not digitized here — true nonlinear-XPP prediction remains
unvalidated. See `rheofp/models/pompom.py` docstring for exact scope.

**Scope decision (2026-07-04): XPP is not a classifier output class.** Product
only ever ingests SAOS/LVE data (frozen input scope above); in that regime
XPP is indistinguishable from a generic multimode Maxwell fit, and its
nonlinear parameters are underdetermined by LVE data alone. `pompom.py` is not
wired into `fitting/identify.py`'s model bank and stays as a validated
reference/tool, not part of the SAOS-only pipeline.

**Branched / LCB melt class — BSW forward model (2026-09-03).** The branched
class (fine class since 2026-09-07, regime = Terminal) is a **5-parameter
Baumgärtel–Schausberger–Winter spectrum**: `bsw_spectrum(w, G_N, tau_max, tau_c, n_e,
n_g)` in `maxwell.py` — two power-law wedges (broad terminal wedge tau^n_e, a
high-frequency wedge tau^-n_g below crossover tau_c), discretized onto a mode
ladder. It replaced the old 3-param `branched_spectrum` (hierarchical
double-reptation), which physically **could not represent real LDPE**
(≥0.28 decades RMS on Pivokonsky 2006 E and B, whatever sigma). BSW fits both
to ~0.06–0.07 decades and its intrinsically broad spectrum cannot fake a
sharp reptation terminal, so AICc still separates it from the linear-melt
class. Now IN `identify()`'s bank as `"branched"` (`BRANCHED_MODELS` in
`maxwell.py`); `branched_spectrum`/`fit_branched` are retained for the
tube-model context + tests. G_N is a window-limited amplitude scale, not a
measured plateau modulus. Refs: Baumgärtel & Winter (1990, 1992).

**Star-polymer melts — Milner-McLeish (2026-09-09). A FINE CLASS, in
`identify()`'s bank (10 candidates).** `rheofp/models/star.py`
implements Milner & McLeish (1997, Macromolecules 30, 2159): arm
retraction against the eq-24 effective potential with the Colby-Rubinstein
dilution exponent alpha = 4/3, the eq-13 early-Rouse branch, the eq-29
first-passage time with prefactor (**with the 1/2 erratum from MM1998's
Appendix applied — see the star.py docstring**), joined by the eq-22 crossover,
the eq-26 modulus integral through the shared `maxwell_spectrum` sum, **and a
separate arm-Rouse high-frequency term (`_arm_rouse_modes`, default on) for the
region above the G″ minimum that MM's eq 26 does not cover**.
Three parameters `(G_N, Z, tau_e)`, k=3, in `STAR_MODELS`. Validated against
the paper's own analytic statements (eq 24 -> eq 8 at alpha=1 to 3.6e-15; the
Figure 2 potential ratio 0.257 vs ~0.26; the quoted log(tau(1)/tau_0) = 13.8;
eq-22 handoff at s = 0.183 where the text wants ~0.2) and planted-parameter
recovery is exact, with Z holding to 0.4% under 2% noise.
**`Z` is entanglements per ARM, and the number of arms is not a parameter at
all** — LVE depends only on arm length, which is the theory's own prediction
and reproduces Pearson-Helfand's observed arm-number independence of
viscosity. The class can say "star", never "how many arms".
**Two limits, both tested:** Z is not recoverable from a terminal-only sweep
(low Z with the plateau cropped drifts ~20% under noise), and **past Z ~ 40 the
model predicts TWO G'' maxima** as the Rouse and activated relaxations
separate — numerically converged, so any feature or pre-filter assuming a
single loss peak will misread a high-Z star.
**Wired into `ALL_MODELS` after the pre-registered cannibalisation check**
(n=30 planted cropped noisy curves/class, identical seeds both banks): real
data held **6/6**, eight of nine existing classes were identical, and
`branched` lost nothing. The reason it earns a place: the 9-model bank had
`branched` (BSW) absorbing **25/30 star melts** silently and confidently —
the "good fit of the WRONG class" failure already documented for vitrimers,
now confirmed for a second architecture. Cost, recorded honestly: `zimm`
23/30 → 21/30, both curves **exact ties** (identical rms to four decimals at
identical k=3, ΔAICc 0.07 and 0.00, with `rouse_screened` tied alongside) —
`star` has joined the known Zimm↔Rouse degenerate cluster, not displaced
anything. Refs 1 and 2 (Pearson-Helfand 1984; Ball-McLeish 1989) are in
`originals/` and were needed to fix the eq-29 prefactor — see next-actions
for the three transcription traps.
**Gap CLOSED same day (2026-09-09, step 3b):** `synth.py` now generates `star`
too, so the bank can no longer emit a class the NEURAL head has never seen —
the mirror image of the wormlike_micelle bug never shipped. Design note worth
keeping: **`tau_e` is DERIVED, not drawn.** A star's spectrum spans ~23-24
decades while a sweep window is ~3-5, so the TERMINAL time is placed relative
to the window and `tau_e` back-computed via `_star_terminal_decades(Z)`. The
first offset range was sign-inverted and gave `terminal_reached` = 0% over 60
planted curves — which would have taught the classifier that stars never flow,
a spurious discriminator of exactly the shape of the fixed-density bug. Range
is now (-3, 1), measured at 51% terminal_reached (n=120); **re-measure that
fraction if the range is ever touched.**
**Real-data validation (step 4) — COMPLETE 2026-09-09.** Two datasets prep'd
and committed: `data/mm1998.npz` (7 monodisperse four-arm PI stars, Z known
from Ma/Me; Milner-McLeish 1998) and `data/santangelo1999.npz` (2 six-arm PIB
stars + a LINEAR control). `identify()` returns `star` for **5/7** MM1998
stars.

**The split is governed by TERMINAL FLOW, not by Z** — this is the class's
real operating envelope and it was measured, not assumed. Where flow is
observed the class is **5/5**; where it is not it is **1/5**, and all four
real-data failures across both datasets sit on the wrong side of that line:
the two MM1998 misses (Z 19 and 21 → `branched`, ΔAICc 57 and 103 — genuine
losses with star's rms 20-55% worse, NOT zimm-style ties), Santangelo's S490,
and Santangelo's **linear control returned as `star`**. A non-terminal window
makes the class fail in both directions. The cause is truncation, not narrow
windows — MM1998's windows cover 104-211% of the model's own predicted
spectrum width; it is the low-frequency asymptote that is missing (Ma105k's
terminal slopes are 1.40/0.70 against 2.0/1.0). In the good band the wins are
decisive: ΔAICc 93-225 at rms 0.024-0.041, except the Z = 2.2 arm which wins
by only ΔAICc 4.8 with its rms tied to `branched` — won on parsimony, because
below Z ≈ 4 there is no star-specific shape left.
**This must NOT become a pre-filter discard** (`if not terminal_reached: drop
star`) — that is the `has_shoulder` missing-evidence fallacy again, and it
would delete the class exactly where a real star is hardest to see. It belongs
in `report.py`; whether to add a star-specific caveat there is the one open
item, see next-actions.

**`Z` is NOT a reportable output** — biased +17-84%. Report "star", never
"Z = ...". **The cause is NOT `Z_BOUNDS`' floor of 4**, and an earlier version
of this file said it was: refitting at floors 4/3/2/1 leaves the two
weakly-entangled arms at Z = 9.12 and 6.66, far above the floor and unmoved by
it. Below Z ≈ 4 the cost is simply FLAT in Z (Ueff(1) ≈ 1-2 k_BT; the
activated time sits under ~1 decade above the arm's own Rouse time), so Z is
unidentifiable there whatever the bound — which is what the floor was
asserting. Leave it at 4. `star` is deliberately NOT in `AMBIGUOUS_PAIRS` —
see next-actions.

**Two bugs in `rheofp/models/star.py` found and fixed by that validation
(2026-09-09).** (1) The eq-29 prefactor was **2× too large** — the AUTHORS'
OWN erratum, printed in MM1998's Appendix under eq 10 ("eq 29 of ref 1 with an
additional factor of 1/2, mistakenly omitted"); the module was transcribed from
the 1997 paper. (2) **The arm's own Rouse modes were missing** — MM scope eq 26
to end at the G″ minimum, a real window goes past it, so the fitter inflated Z
to cover the gap. Added `_arm_rouse_modes` reusing the validated Likhtman-
McLeish eq-19 form from `tube.py` (`arm_rouse=False` recovers the paper's bare
result). Effect: median |Z error| 44% → 30%, fitted G_N 440-490 → 366-436 kPa
(PI's true ~400). **Consequence: G′ now rises ABOVE G_N at high frequency —
G_N is the plateau LEVEL, not the curve maximum.** Cannibalisation check passed
(matched before/after: overall 0.845 → 0.855, star self-recovery 18/20 → 20/20,
other 8 classes byte-identical).

**Bank-coverage invariant (2026-09-04).** `identify()`'s bank must hold a
candidate for EVERY class `rheofp/data/synth.py` can generate — now enforced by
`test_every_generated_class_has_a_candidate_in_the_identifier_bank`. It was
violated: `wormlike_micelle` was generated, and emitted by the neural head, but
had no registry entry, so the AICc identifier could not return it at any cost.
Two lessons. (1) It silently corrupted the physics baseline, which filtered its
pool by the *neural* class list — a no-op — and was therefore charged for
questions it could not answer. (2) **A missing class does not surface as low
confidence.** Handed a micelle, the 8-model bank answered `branched` at Akaike
weight 1.000 with a 0.05-decade residual, far under `FLOOR_CHI2`; the
none-of-the-above floor cannot catch a class that isn't in the bank, because
the most flexible candidate present simply absorbs it. Now registered as
`WLM_MODELS` in `maxwell.py` (k=4, `beta` linear, not log10). Adding it cost no
accuracy on the other eight classes and left real data at 6/6.

**Pre-filter principle (2026-09-04) — a hard discard is only sound when it
rests on a POSITIVE observation.** `terminal_reached` removing the network
classes is sound: flow was *observed*, and a permanent network cannot flow at
any temperature. `if not has_shoulder: allowed -= {sticky_rouse,
sticky_reptation}` is NOT sound: an absent second G″ peak is equally consistent
with "no exchangeable bonds" and "bond exchange outside my window", which is the
same missing-evidence fallacy the project already rejected for melt-vs-rubber
(*"missing evidence, not evidence of absence"*).

**FIXED 2026-09-07 — the `has_shoulder` discard is REMOVED.** Both sticker
classes are now always on the ballot and AICc adjudicates them; the shoulder
survives as a reported *feature*, never as a discard. Pre-registered
before/after on planted cropped noisy curves (n=30/class, identical seeds):
`sticky_rouse` **18/30 → 29/30**, `sticky_reptation` **26/30 → 28/30**, overall
**0.837 → 0.885**, and **every other class byte-identical** — the two k=4
models cannibalised nothing. Real data stayed **6/6**. The flagship error is
gone: vitrimer reported as a permanent network went **0/120**. Cost: two more
candidates fit per call, so `identify()` is ~1.9 s/curve (suite ~4.5 min).
The two remaining discards are both sound-by-observation (`terminal_reached`
removing the network classes; `wide_plateau` gating reptation).

## Goals — ALL THREE COMPLETE as of 2026-09-01
1. DONE. Restructured into the GitHub-ready `rheo-fp` package (rheofp/,
   scripts/, data/, docs/, tests/), README, locked env, .gitignore, LICENSE.
2. DONE. Synthetic data generator — `rheofp/data/synth.py` +
   `scripts/generate_dataset.py`. Binary npz out, tqdm bar; xlsx kept only as
   a capped human sanity-check backdoor.
3. DONE. ML training pipeline — `rheofp/ml/` + `scripts/train_classifier.py`.
   Two-head set model (conv encoder -> masked attention pool -> classify +
   regress) with a learned abstention head, on the frozen architecture.

**Current state (2026-09-09, retrained) — these are 10-CLASS numbers.**
**194 tests pass, 2 skipped** — the full non-slow suite re-run on the laptop
after the two `star.py` fixes and the step-4 real-data tests (12:15 on an
i7-10750H; it was 185 before those 9 tests were added), so the suite is green
against the current code, not just against the retrain snapshot. Retrained on
the ten-class distribution after `star` was added (16k examples, 55 epochs,
seed 1, office PC).

On synthetic data the classifier scores **0.923** (merged-pair **0.968**,
regime **0.999**) against an AICc physics baseline of **0.907** measured on the
**same test split** — margin **+0.016**. That baseline pairing was the
outstanding item from §1h and is now closed: the ~0.82 (n=90) standalone figure
is superseded, and `skipped` was 0, confirming the bank covers all ten
generated classes. **Do not read +0.016 as the network barely working** — the
baseline rose from ~0.82 to 0.907 because the bank was fixed (wormlike_micelle,
then star), so the network is being compared against a much stronger physics
side than the old +0.217 and +0.10 margins were. Note also the two are not
strictly comparable: the baseline sees ONE curve, the network sees the stack.

**58% of all remaining error is still the physically degenerate Zimm<->Rouse
pair** (107 errors), while cured_elastomer<->critical_gel again contributes
**zero** — cured_elastomer is perfect (1.000) and critical_gel 0.992. Per class,
the rest sit at 0.91-1.00; zimm (0.724) and rouse_screened (0.737) are the only
weak entries and they are weak only against each other.

**`star` classified at 0.996 (239/240) — the strongest non-trivial class in the
bank, with its single error going to `wormlike_micelle`, not zimm/rouse and not
branched.** Both hypotheses the retrain was set up to distinguish are therefore
REJECTED: the network does not confuse stars with the linear-melt pair (so the
AICc side's three-way tie does not reproduce here), and it does not confuse them
with `branched` (so the two brains do NOT disagree about what absorbs stars).
**`star` stays out of `AMBIGUOUS_PAIRS`** — the evidence that tempted it was
AICc-side ties, and the network shows no such degeneracy. Note the asymmetry
worth remembering: 2 zimm curves still leak *to* star, but no star leaks to
zimm, so the overlap is one-directional and small.

Abstention is well-calibrated: dropping the least-confident 10% lifts accuracy
to 0.957, 20% to 0.982, 30% to 0.996. Stacks still beat single curves (0.898 at
N=1 -> ~0.94 at N>=2).

Against real single-curve spectra the retrained checkpoint scores **6/6
literature curves correct** (Darby 2022 cured silicones, Tixier 2004 critical
gel, Pivokonsky 2006 LDPE), raw == resampled so the density invariance holds.
The AICc side's own 6/6 was re-confirmed with the 10-model bank on 2026-09-09.
Read that 6/6 carefully: six curves, three papers, all N=1, four of them the
same material family — it confirms the BSW fix worked, it is not evidence of
general real-world accuracy. **`star` now HAS real-data validation** (step 4
complete, 2026-09-09): 5/7 on Milner-McLeish 1998's own seven-star set, and
5/5 restricted to curves that reach terminal flow — but read the envelope in
the star paragraph above, and note that the 6/6 benchmark figure does not
include any star curve.

**Both real temperature stacks tested so far (Edera 2024, Ricarte 2023 —
vitrimers) confirm the STACK MECHANISM but fail the FINE CLASS.**
`resolve_melt_vs_network` correctly refuses a permanent-network call on real
dynamic-network data in both cases (Edera: 2.50 dec shift; Ricarte: residuals
0.001-0.02, Arrhenius R^2=0.99). But every curve in both datasets is identified
as `branched`, not a sticker class — diagnosed as a genuine forward-model limit
(`scripts/diagnose_sticky_models.py`): the sticky models are a few discrete
Maxwell modes about one sticker time and cannot reproduce a real vitrimer's
power-law G'' wing (rising monotonically as omega falls), which BSW's broad
spectrum fits well. **User decision: keep the sticky models as-is; report the
ambiguity instead of replacing the forward models** —
`branched_vitrimer_contradiction()` in `rheofp/report.py` names this
specific, measured contradiction whenever a `branched` winner shows the
vitrimer power-law signature (calibrated: 0 false positives across 31 mixed
synthetic `branched` winners and both real Pivokonsky LDPE curves).

**Abstention still cannot flag out-of-distribution material**: it is trained
against the model's own errors on the synthetic distribution, so a low
abstain_p is not evidence of a correct answer on a material whose class is
absent from training. The explanation layer (`rheofp/report.py`,
`scripts/explain.py`) exists precisely because that detector problem has no
general solution: it reports the winner's absolute fit quality, ranks
alternatives by delta AICc (not the misleading Akaike weight), and prints an
UNCONDITIONAL "don't think it's X? this may be why" section on every result —
including confident, correct ones — because most of this classifier's errors
are GOOD fits of the WRONG class, which no confidence score flags.

**Uploads are density-agnostic by construction**: any point count and any
frequency range are resampled onto a fixed internal log-omega grid in
`rheofp/ml/dataset.py` (`resample_log_grid`), so raw and resampled inputs give
identical predictions. Do not reintroduce a fixed-density assumption.
See `.claude-notes/next-actions.md` §1f and §3.

## Data format conventions
xlsx: column 0 = ω; paired columns named `<sample> G' (Pa)` / `<sample> G'' (Pa)`;
one sheet per figure/dataset; an `omega_hz` flag controls Hz vs rad/s.

## Working style — follow strictly
- Validation-first, in this order: forward physics validated → inverse
  recovery validated → physical discriminators validated → notebook
  assembled → end-to-end execution.
- Work proceeds in explicit, user-directed steps. Do NOT write unsolicited
  code, do not add speculative features, do not ask batteries of questions —
  execute what is asked.
- Keep implementations lean. Config-driven: all hardcoded values isolated in
  config blocks at the top.
- Notebooks use `plt.show()` only — never `savefig`, never save outputs into
  the notebook file.
- Deliver code snippets as plain pasteable text unless a file is requested.

## Key references
Likhtman & McLeish (2002); McLeish & Larson (1998); Baumgärtel–Schausberger–
Winter (1990) / Baumgärtel–Winter (1992); Leibler–Rubinstein–Colby
(1991); Rubinstein–Semenov (1998, 2001); Stukalin et al. (2013); Colby (2010);
Dobrynin–Colby–Rubinstein (1995); Pivokonsky et al. (2006).
