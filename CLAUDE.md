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
User works from multiple PCs (home + office + laptop). Git is the sync layer:
- **Pull before starting**, commit + push before leaving a machine. Only
  committed work is visible on the other PC.
- Reconstruct "what changed on the other PC" from `git log` / `git diff`.
- **What does NOT travel, and must be rebuilt per machine:** `.venv/`
  (recreate with `uv sync`), `checkpoints/` (retrain — see next-actions),
  and `originals/` (a OneDrive junction; optional, nothing is blocked by its
  absence because every derived `data/*.npz` is committed).
- **On a fresh Windows PC, run `gh auth setup-git` after `gh auth login`.**
  Otherwise git uses Git Credential Manager, which blocks on an invisible GUI
  prompt and makes `git push` **hang forever with no error message**. Hit on
  the laptop 2026-09-09; details in `.claude-notes/environment.md`.

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
**>>> IT IS NOW THE SHIPPED `reptation` CLASS (2026-09-17). <<<** For most of
the project's life `tube.py` was validated but NEVER WIRED IN: the bank's
`reptation` entry was a hand-rolled fast approximation, and it was broken on
real monodisperse linear melts (rms 0.115/0.083/0.044 on Katzarova 2018, with
Z recovered ~2x LOW). `model_reptation_lm` in `solutions.py` is now a thin
adapter onto `tube.Gstar` - same (Ge, tau_d, Z) vector, same k=3, so AICc stays
comparable - and it recovers **Z = 28.9/16.0/9.6 against true 29.5/15.5/7.9**.
The old `model_reptation` is retained in the file but no longer shipped.
Never caught earlier because **the 6/6 real-data benchmark contains no
monodisperse linear melt** - the same blind spot that let the comb check pass
with no star curve in its real-data set. Two consequences: `identify()` got
much slower (was ~2 s), and because `synth.py` imports the same registry the
GENERATOR swapped too, so **the neural checkpoint is stale and every accuracy
figure in this file predates it**.
**Cost UPDATE 2026-09-17: `identify()` is ~88 s/curve, not the ~160 s first
measured** - `tube.py`'s two brute-force inner loops were replaced by closed
forms (a Gamma-function early term and a polygamma tail on eq 19's 3rd sum).
Both are strictly MORE accurate than what they replaced; the second fixed a
real convergence bug worth 3.9e-3 decades of G". Real-data results are
unchanged except that **PS105 returns `reptation`** (dAICc 7.2 over branched,
was branched by 12.1) - **but that flip is an artifact of `LM_RNG_SEED = 0`
and was WITHDRAWN on 2026-09-18; the BSW fault is 3/3, not 2/3.** See the
seed-sensitivity block below.
Details and the measured numbers are in `.claude-notes/next-actions.md`.

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
to ~0.06–0.07 decades.
**>>> CORRECTION 2026-09-17: this paragraph used to claim BSW's "intrinsically
broad spectrum cannot fake a sharp reptation terminal, so AICc still separates
it from the linear-melt class." THAT IS FALSE, and it had never been tested
against a real monodisperse linear melt. <<<** On Katzarova 2018's three
monodisperse polystyrenes, `branched` beats the VERBATIM Likhtman-McLeish tube
model on ALL THREE - rms 0.0250/0.0261/0.0207 against 0.0314/0.0300/0.0222, at
dAICc 50.7/28.9/12.1 - and on the two longer chains that margin is **2.9x and
2.1x the curves' own digitization scatter**, i.e. real resolvable structure and
not noise.
**>>> The 2026-09-17 requalification to "2/3" is WITHDRAWN (2026-09-18).
It is 3/3 again. <<<** After `tube.py`'s convergence fix the shortest chain
**PS105 returned `reptation`** - rms 0.0205 vs branched's 0.0207, dAICc 7.2
the other way - and that was read as the fault shrinking to 2/3. **It is not
physics: it is the tube model's RNG draw.** `tube.R_of_t` estimates constraint
release by SAMPLING `LM_NCHAINS = 20` chains at a fixed `LM_RNG_SEED = 0`.
Re-running PS105 at seeds 0-4 gives **`reptation` on seed 0 ONLY**, and
`branched` on 1/2/3/4 (dAICc +29.9/+1.7/+15.4/+58.1). reptation's rms swings
**0.02045-0.02685** across those draws while `branched` is identical to five
decimals on every one (BSW does no sampling). So the ~2e-4 rms margin that
decided PS105 is **an order of magnitude below the forward model's own
sampling noise** (~1.3e-2 decades at nchains=20, measured against an
nchains=480 reference). PS392 and PS206 are STABLE - `branched` on 5/5 seeds
at dAICc +51.6..+68.9 and +27.7..+44.8 - so **the BSW fault itself is
untouched and is back to ALL THREE.** Script
`scripts/check_tube_seed_sensitivity.py`; output
`docs/tube_seed_sensitivity_2026-09-18.txt`.
**General rule this establishes: any `reptation` margin smaller than ~1e-2
decades of rms is a property of the seed, not of the material.** The AICc
arithmetic was verified by hand and k=5 is correctly paid
for; BSW simply fits a real linear melt better than the correct physics does.
This is the project's ACTIVE OPEN FAULT - see `.claude-notes/next-actions.md`,
top section. Note the precedent it sits against: `comb` was VETOED for exactly
this failure mode (fitting a linear control better than real combs).
Now IN `identify()`'s bank as `"branched"` (`BRANCHED_MODELS` in
`maxwell.py`); `branched_spectrum`/`fit_branched` are retained for the
tube-model context + tests. G_N is a window-limited amplitude scale, not a
measured plateau modulus. Refs: Baumgärtel & Winter (1990, 1992).

**des Cloizeaux TDD-DR — BUILT AND VALIDATED, DELIBERATELY NOT IN THE BANK
(2026-09-18).** `rheofp/models/tdd.py` implements van Ruymbeke & Keunings
(2002, Macromolecules 35, 2689) Table 1 eq 4 + eqs 1/5, with Table 2 eq 8 Rouse
added by the paper's own linear mixing rule. Three parameters
`(G_N, tau_rep, Z)`, k=3, 26 tests, **fully deterministic — it samples
nothing.** It was built to replace `tube.py` as the shipped `reptation`,
because `identify()` spends **94.2%** of its runtime in that one candidate
(4940 forward calls x 10.67 ms of 56.0 s; every other candidate is ~0.03
ms/call). Pre-registered in `docs/tdd_preregistration.md`, committed before any
fit; head-to-head in `scripts/check_tdd_vs_tube.py`.
**REJECTED on its own criteria.** P1 PASS; P2 PASS decisively (planted Z exact
noiseless, max 2.1% error under 2% noise — better than `tube.py`'s +22%); but
**P3 FAILED 2/3** (rms 0.0471/0.0383 against tube's 0.0315/0.0298 on
Katzarova's two longer monodisperse PS; bar was +0.005 dec) and **P4 returned
the pre-registered vetoing outcome (c)** — the BSW margin gets ~3x WORSE
(dAICc +147.7/+87.6 against tube's +51.6/+27.7). Not a fitting artifact:
10/30/60 restarts agree to four decimals.
**Method note worth carrying forward: score through `identify()`'s own
`fit_model`, never a local multi-restart reimplementation.** The first run of
this comparison used one and made EVERY model look worse (reptation
0.0446/0.0422, branched 0.0353/0.0369), failing to reproduce the project's
recorded figures. The verdict was unchanged, but only the `fit_model` numbers
are quotable — and those reproduce the record exactly.
**>>> THE NEAR-MISS, and why it was refused. <<<** The binding constraint is
`M*/Me` fixed at the paper's PS value of 8.7. Freeing it (k=4) gives rms
0.0316/0.0335/0.0285 and **beats BSW 3/3** at dAICc −28.7/−25.6/−8.9 — exactly
the result this project has chased since 2026-09-17. It was NOT taken:
`M*/Me` **pins to its upper bound at 60** (a parameter at its bound is not
identified by the data, it is absorbing misfit) and **Z error blows out from
+4.6%/+6.5% to +50.2%/+60.4%**. That is winning by flexibility while destroying
the one physical quantity the class exists to report — the `comb` veto exactly,
and the same shape as the BSW fault itself. Pinned by
`test_tdd_is_deliberately_not_in_the_identifier_bank`.
**Two bugs caught by validation that every shape test passed.** (1) The obvious
finite-difference Prony ladder (`g_i` = drop of G across each interval)
conserves mass but MISPLACES it and does not converge — refining N=96→1536
moved G′ by 0.09 decades and kept drifting. Against a referee of direct
oscillatory quadrature of the exact definition `G'(w) = w ∫ G(t) sin(wt) dt` it
was **0.12–0.30 decades wrong**; NNLS matches to <1e-4. Geometric-midpoint
placement did not help. **That referee is reusable — use it for any G(t)→G\*(w)
route**, and it is now a permanent test. Same aliasing hazard that forced
`comb.py` onto ML1999. (2) The bare TDD kernel has **no Rouse rise and no G″
minimum** (G″ decays as w^−0.23 where `tube.py` turns up); van Ruymbeke add
Rouse separately and say so (p.2692). Same gap `star.py` had.
**Honest cost correction: the speedup is ~8x, not the ~210x a first probe
suggested** — that probe used the ladder that turned out to be wrong.
**Chaudhuri & Lele (2020, J. Rheol. 64, 1) is NOT a speed paper**: its TDD-DR
is for POLYDISPERSE/bimodal blends (eq 7 = a double integral over two MWDs plus
a 5-parameter GEX inversion), which is more work, not less. It is the recipe
for a future BLEND class, which is what `tdd.py` is retained for.

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

**The split is governed by TERMINAL FLOW, not by Z** — measured, not assumed,
BUT **requalified by Pryke 2002 on 2026-09-11; read the correction at the end
of this paragraph before quoting the numbers.** Where flow is
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
in `report.py`; the star-specific caveat was built there 2026-09-09.

**>>> CORRECTION 2026-09-11 (Pryke 2002): the 5/5-vs-1/5 split is NOT the
envelope it was read as. <<<** On a third chemistry (1,2-polybutadiene)
`terminal_reached` read **False on BOTH** samples and `star` was **right on
both**, decisively (ΔAICc 170 and 87). The cause is a hard threshold —
`terminal_reached = (slope_Gp_lo > 1.4) and (slope_Gpp_lo > 0.7)` — and
Ma38k measures **1.39 / 0.625**, missing the G′ cut by **0.01** while plainly
flowing (raw terminal slopes 1.87/0.85, G″/G′ = 33 at the lowest point).
So **do not quote "5/5 where flow is observed, 1/5 where it is not" as the
class's operating envelope**: it is a threshold artefact at least as much as a
physical boundary. Nothing was changed (n=2, and the feature gates a sound
positive-observation discard); pinned by
`test_terminal_reached_is_a_sharp_threshold_that_a_flowing_melt_can_miss`.
Knock-on: `challenge()`'s star window caveat fired on both — **2 false alarms
out of 2** — on correct calls whose G_N landed within 4% of the paper's.

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

**Comb / H-polymer melts — BUILT AND VALIDATED, DELIBERATELY NOT IN THE BANK
(2026-09-14).** `rheofp/models/comb.py` implements McLeish et al. (1999,
Macromolecules 32, 6734) section 2.1 + Appendix A: arms retract first against
an effective potential carrying a `(1-phi_b)` factor (cross-bar material acts
as a permanent network throughout, eq 4), the relaxed arms then act as solvent,
and the cross-bar reptates in a tube diluted to `s_b*phi_b` effective
entanglements with all friction at the branch points. Five parameters
`(G_0, s_a, s_b, phi_b, tau_e)`, k=5, `COMB_MODELS`. 33 tests.

**Use ML1999, NOT McLeish & Larson 1998.** ML1998's eq 8 is a SQUARED bracket,
not a Prony series, so it needs a numerical Fourier transform — which aliases
unfixably (the same machinery reproduces an analytic Maxwell mode to 4 decimals
on a narrow grid and fails by 114x on the 16-decade grid this model needs, not
converging with added points). ML1999 eqs 22-24 give a SUM of two weighted
integrals: a mode ladder through the validated `maxwell_spectrum`, like
`star.py`'s eq 26.

**Why it is NOT on the ballot.** The pre-registered cannibalisation check
passed on its own terms (synthetic: every class unchanged but
`sticky_reptation` 29→27; benchmark 6/6). That reading was WRONG, and the
script had two flaws now fixed: it scored only WHETHER the winner changed, never
BY HOW MUCH, and its real-data set contains **no star curve**. Measured against
MM1998's seven real four-arm polyisoprene stars, wiring `comb` in took `star`
from **5/7 to 4/7** (PI4_Ma47k → `comb`) and collapsed the surviving decisive
margins from ΔAICc **194-225 to 7.6-27.4**. Cause is physical, not a bug: a comb
with a short cross-bar is very nearly a star, and k=5 beats k=3. `star` has real
validation across three chemistries; `comb` has none yet, so this trades a
confirmed capability for an unconfirmed one.
**Consequence today: an uploaded comb is confidently MISIDENTIFIED** — measured
over 30 planted combs with the class absent: `branched` 12, `critical_gel` 10,
`star` 6, `sticky_reptation` 2. Always wrong, never uncertain. Pinned by
`test_a_planted_comb_is_misidentified_while_the_class_is_unwired`.
**>>> SETTLED 2026-09-16 BY REAL COMB DATA: `comb` STAYS OUT. <<<**
Kapnistos et al. (2005) Figs 1a + 2a digitized (`data/kapnistos2005.npz`, 9
curves including a linear-backbone control), predictions pre-registered in
`docs/kapnistos2005_preregistration.md` and committed BEFORE any fit
(`058d4f7`; outcome `bfa5a43`). **All three criteria failed: P1 real combs →
`comb` 0/6; P2 the LINEAR control c6bb-PS → `comb` at weight 1.000, ΔAICc
161.8, rms 0.247→0.126; P3 MM1998 `star` 4/7 with worst surviving margin 4.2
against a floor of 50.** The decisive fact is P2 — **the comb model fits a
straight chain better than it fits any real comb in the same figure**, which is
flexibility rather than physics. P1 failed in the direction NOT predicted: the
pre-registered worry was that `comb` would win the combs for the wrong reason,
and instead it won none of them.
**Two corrections this produced.** (1) The synthetic comb-absent figures quoted
above (`branched` 12, `critical_gel` 10, `star` 6 of 30) **do not describe real
data**: measured on 9 real combs it is **`star` 6/9, `branched` 3/9,
`critical_gel` 0/9**. (2) **The confusion is METHOD-DEPENDENT** — the AICc side
confuses comb↔`star`, the NETWORK confuses comb↔`critical_gel` (8/9), a **9/9
disagreement with zero overlap**, and the two-brain shortlist contained the
truth **0/9 times**. So the pooled either-right constants (97.5% / 86.4%) **must
not be quoted for a material whose class is absent from the bank** — that
regime now has a real-data counter-example. The network was confident on every
one (`abstain_p` 0.000-0.003, p to 0.994), the sharpest demonstration yet of the
OOD blind spot; `critical_gel` is not a silly answer, since the paper itself
(p.7854) records combs showing a critical-gel-like power law.
**A candidate rule was measured and REJECTED**: the two-step tan-δ signature
holds on only 2 of 6 real combs while the linear backbone shows one minimum —
not a discriminator at n=9. Do not build on it without more chemistries.
**What an uploaded comb does today**: 6/9 wrong but flagged by the
none-of-the-above floor (the first real-data case of that floor catching a
missing class rather than being fooled), **2/9 wrong at good fit quality with no
warning** (c652-PS at rms 0.030 → `branched`), 1/9 a tie. Never right.
Reopening would need a reparameterised `comb` that cannot outfit a linear chain
(the c6bb-PS control is the cheap test), or real comb data from a second source
(ML1999 Fig 6, `originals/mcleish1999_h_polymers.pdf`, figure-only so it needs digitizing).
Do not lower `test_star.py`'s `runner_up["delta"] > 50` assertion — it is
correctly reporting a regression, not miscalibrated, confirmed twice now.

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
**The `wide_plateau` discard on reptation was REMOVED 2026-09-16** for the same
reason: `plateau_width` reads 2.29/0.84/0.16 decades at Z = 29.5/15.5/7.9 on
Katzarova's three linear melts - a monotone function of entanglement count, so
a >= 1.0-decade threshold was a cutoff on MOLECULAR WEIGHT wearing a shape
test's clothes, and it deleted the TRUE class from the ballot for the two
shorter chains. It was never pinned by a test; it is now (the removal is).
**TWO hard discards remain** (this said "exactly ONE" until 2026-09-17, which
was simply wrong - the second had been there all along, pinned by no test):
1. `terminal_reached` removes the network classes - flow was SEEN, and a
   permanent network cannot flow at any temperature.
2. `confident_entangled` removes `zimm` and `rouse_screened` - a plateau
   >= 1 decade wide, with spectrum continuing above it AND terminal flow
   below it, was SEEN, and an unentangled chain has no plateau at all.
Both are sound by the project's own standard (a hard discard needs a POSITIVE
observation). Both are now pinned by tests, and a third test asserts that
every feature a discard rule names is actually exported into `feats` - the
gap that made #2 unexplainable to users until 2026-09-17.

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
**334 tests collected** (counted 2026-09-21, = 306 + the 20 of the new
`tests/test_plausibility.py` + 8 others added since). The figure has been
266, then 280, then 306, and has drifted every time; **recount rather than
trusting it.** The
previous figure here was 213, measured 2026-09-09 in 13:34 on the office PC
(RTX A1000; the laptop is slower); the 33 tests of `tests/test_comb.py` were
added 2026-09-14 and the rest is arithmetic — 194 after the step-4 tests, + 2
for the star window caveat, + 17 (3 in `test_report.py`, 14 in the new
`test_neural_report.py`) = 213, + 33 comb + a few from the widened vitrimer
safeguard. Retrained on the ten-class distribution after `star` was added
(16k examples, 55 epochs, seed 1, office PC).
**The `comb` class is NOT in the bank** — see the comb paragraph below; the
checkpoint and all accuracy figures here remain 10-class and current.

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
**Extended to a THIRD CHEMISTRY 2026-09-11 (Pryke 2002, 1,2-polybutadiene):
2/2, ΔAICc 170 and 87 over `branched`** (`data/pryke2002.npz`; predictions
pre-registered in `docs/pryke2001_preregistration.md` before the curves were
digitized, outcomes recorded under its OUTCOME section). The strongest result
there is independent: a free 3-parameter fit recovered the paper's own stated
G_0 = 0.765 MPa to **+1.4% / −4.4%** — a number the fit never saw. Z stayed
biased **+24% / +42%**, inside the known band, and remains non-reportable.
**Both curves were sharp two-brain DISAGREEMENTS** (network said `branched`
p=0.983 and `cured_elastomer` p=0.986, both confident at abstain_p ≈ 0);
physics was the right member, but that was knowable only from the recovered
G_0, so it must not be generalised into trusting physics on a split. Fitted
`tau_e` came in 2.7–3.6× the paper's, just outside the factor-of-2 band
`star.py` cites while the modulus sat well inside — flagged, not acted on, n=2.

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

**Are the winner's fitted NUMBERS usable? (`rheofp/plausibility.py`,
2026-09-21, Plan A step 1.)** Nothing used to ask this: the two-brain check
compares LABELS and `FLOOR_CHI2` checks fit QUALITY, but a parameter stopped
by its bound can sit inside a good fit while reporting the wall's position
instead of the sample's. `at_bound_warning()` flags it for the winning class
on every call, report-only (`identify()` untouched; dependency runs
`plausibility -> report`). This automates what had twice been caught by a
human reading one number, and both times it changed a verdict: `tdd`'s
`M*/Me` pinned at 60, and `comb`'s `s_b` pinned on 8/9 real combs.
**Calibrated both ways** (`docs/at_bound_calibration_2026-09-21.md`): fires on
8/9 real Kapnistos combs, quiet on 4/6 of the real benchmark. Three bounds are
marked SOFT because they are physics rather than numerical walls (`star`'s Z
floor of 4, `critical_gel`'s `u`, `cured_elastomer`'s `m`) and report without
the distrust language.
**Read its limit honestly: it catches bad FITS, not bad WINS.** The one
Kapnistos curve with NOTHING pinned is `c6bb-PS`, the linear control that
`comb` wrongly wins — `comb` reaches that answer from a comfortably interior
vector via its star limit, so no bound is involved. This is not an
out-of-distribution or wrong-class detector, and must not be described as one.
**It immediately found a real defect**: on BOTH Pivokonsky LDPE melts —
correct `branched` calls at rms 0.062/0.056 — BSW's terminal-wedge exponent
`n_e` sits ON its 0.90 ceiling, and widening the ceiling shows it chases every
limit given, rms improving monotonically out to **n_e = 2.0** against
`bsw_spectrum`'s own stated ~0.2-0.7. The shipped bound is the only thing
keeping that parameter inside BSW's physics on real data — a **third**
independent form of the BSW over-flexibility fault. Nothing was changed:
that is a pre-registered, cannibalisation-checked change, and note the
direction — a larger `n_e` makes BSW MORE flexible, the opposite of what the
fault needs. See next-actions for the open item, including the correction that
`synth.py`'s quoted `n_e ~ 0.55-0.68` describes a WORSE local optimum that
`fit_bsw` finds, not the model's best fit.

**The two brains' AGREEMENT is the confidence signal neither one can give
alone (`rheofp/neural_report.py`, 2026-09-09).** The AICc bank and the network
share no machinery — closed-form model fitting ranked by penalised likelihood
versus a conv encoder over a resampled grid — so a divergence is not subject to
either side's known overconfidence failure (the network's abstention is trained
only on its own synthetic errors; AICc's weight hits 1.000 even when the true
class is absent from the bank). Four outcomes are reported, not two: `agree`,
`agree_degenerate` (a split across a known-inseparable pair, which must NOT be
alarmed like a real one), `disagree_ranked`, `disagree`.

**Measured twice. Quote the n=600 run; the n=200 one is superseded but kept.**
On MM1998's seven-star set the signal separates the AICc hits from the AICc
misses *perfectly*: agree on all 5 AICc gets right, disagree on both it gets
wrong (Ma95k/Ma105k, true stars called `branched` at ΔAICc 56.5 and 102.6,
where AICc is decisive and the abstention head reads 0.00, so neither
self-confidence flags them). It also flags Santangelo's linear control returned
as `star` at weight 1.000. That is n=7.

**Synthetic: measured THREE times** (`scripts/measure_agreement.py`, seeds 7 /
11 / 23, 1400 curves, all three outputs committed under `docs/`). The
constants in `neural_report.py` are **pooled** over all three and a test
recomputes them from the files.

| | agree (n=1231) | disagree (n=169) |
|---|---|---|
| physics | 0.945 ± 0.007 | **0.438 ± 0.038** |
| neural | 0.937 | **0.426** |
| either right | 0.975 | **0.864** |

**A disagreement roughly HALVES both methods** (ratio 0.46). As a *gate*,
agreement beats simply trusting the network's own probability by **+0.006 /
+0.019 / +0.012** across the three runs → **pooled +0.014 at 2.0 SE**. No
single run reaches significance; only the pooled agree arm does. The sign
never flipped, so the effect is **consistent and small**. **Say "comparable,
probably a shade better; not a reason to prefer it" — never "established".**
The seed-23 run was judged against a decision rule committed *before* the
numbers existed (`9b51840`) and landed AMBIGUOUS; that rule was not
renegotiated afterwards, and must not be.

Three things the repeat runs corrected: **which brain degrades more on a
disagreement is NOT stable** (network worse at seed 11, fitter worse at seed
23), so never advise trusting one side over the other on a split;
`agree_degenerate` **swings** (physics 0.364 / 0.576 / 0.575) on ~5-7% of
curves, so only its `either right` is quotable; and `star → branched` appears
10× (seed 11) and 3× (seed 23) **with the PHYSICS side right**, the opposite
direction from MM1998 — **the real-data n=7 pattern does not generalise.**

**The most robust result was NOT the one being measured — the PAIR beats
either member, and it is the claim that held up best across re-measurement.**
Pooled: one of the two labels is correct **97.5%** (agree) and **86.4%**
(disagree) — against just **0.438 / 0.426** for the two methods individually on
those same disagreement cases. So even where neither brain is individually
reliable, the pair is usually the right *shortlist*. It varies ~9 points
between seeds on the small disagree arm, so quote it as "about 85-90%", not to
the decimal. A **sharp** disagreement is the pair's BETTER case — pooled
either-right **0.93** (n=112) against **0.75** for the milder
`disagree_ranked` kind (n=51), consistent across all three runs: when the two
diverge completely they usually diverge onto the right answer and a wrong one,
whereas reordering the same short list more often means both are looking at the
wrong part of it.

`report.py`'s renderer therefore prints `YOUR SHORTLIST: A or B` on any
disagreement and frames it as a two-item list to settle with outside knowledge
— never a winner with a dissent attached, and **never averaged into one
verdict, which would destroy exactly this**. `pair_note()` in
`neural_report.py`; the quoted constants are pinned against the committed
measurement file by a test, so user-facing numbers cannot drift from the run
they came from.

This is REPORTING ONLY: `identify()`'s contract is untouched, and `report.py`
still imports no torch (the dependency runs `neural_report` → `report`, never
back).

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
