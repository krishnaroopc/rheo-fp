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
  Wormlike micelles are model-only. Glassy regime was dropped.
- **Taxonomy (as actually built)**: **9 classes** — 7 fine
  (zimm, rouse_screened, reptation, sticky_rouse, sticky_reptation,
  cured_elastomer, critical_gel) + 2 model-only (wormlike_micelle, branched);
  **2 regimes** (terminal, solid). The Yield-dominated regime has no physics and
  therefore no training data. Five model-only classes from the design were never
  built. Do not quote the design numbers as if they were implemented.
- **"Model-only" is documentation, not behaviour.** Nothing in `identify.py` or
  `ml/evaluate.py` coerces `branched` / `wormlike_micelle` to a regime-level
  answer — both are scored as ordinary fine labels today. See §3.

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
class (model-only, regime = Terminal) is a **5-parameter Baumgärtel–
Schausberger–Winter spectrum**: `bsw_spectrum(w, G_N, tau_max, tau_c, n_e,
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
(*"missing evidence, not evidence of absence"*). Measured: 4 of 12 generated
vitrimer curves had BOTH vitrimer classes struck off before scoring, one landing
on `cured_elastomer` — a dynamic network reported as a permanent one, which is a
flagship molecular error under the scope above. Not yet changed; the decision
and the required measurement are in next-actions §1k.

## Goals — ALL THREE COMPLETE as of 2026-09-01
1. DONE. Restructured into the GitHub-ready `rheo-fp` package (rheofp/,
   scripts/, data/, docs/, tests/), README, locked env, .gitignore, LICENSE.
2. DONE. Synthetic data generator — `rheofp/data/synth.py` +
   `scripts/generate_dataset.py`. Binary npz out, tqdm bar; xlsx kept only as
   a capped human sanity-check backdoor.
3. DONE. ML training pipeline — `rheofp/ml/` + `scripts/train_classifier.py`.
   Two-head set model (conv encoder -> masked attention pool -> classify +
   regress) with a learned abstention head, on the frozen architecture.

**Current state:** 126 tests pass (2 skipped). On synthetic data the classifier scores
**0.917** (merged-pair 0.963, regime 0.999); **55% of all remaining error is
the physically degenerate Zimm<->Rouse pair**, while the equally-nested
cured_elastomer<->critical_gel pair now contributes zero. The **0.700 physics
baseline this used to be quoted against is superseded** — it was measured while
`wormlike_micelle` was generated but absent from `identify()`'s bank, making
~1/9 of the baseline's pool unanswerable; over the fixed 9-candidate bank a
standalone re-measurement gives ~0.82 (n=90), so the real margin is roughly
+0.10, not +0.217. The network's own number is unaffected — the ML pipeline
only touches `identify()` for the baseline. Re-measure the pair on the next
training run (next-actions §1h). Against real measured spectra it scores **6/6 literature
curves correct** (Darby 2022 cured silicones, Tixier 2004 critical gel,
Pivokonsky 2006 LDPE), up from 4/6 once the branched forward model was replaced
with BSW. Read that 6/6 carefully: six curves, three papers, all N=1, four of
them the same material family — it confirms the BSW fix worked, it is not
evidence of general real-world accuracy. **Abstention still cannot flag
out-of-distribution material**: it is trained against the model's own errors on
the synthetic distribution, so a low abstain_p is not evidence of a correct
answer on a material whose class is absent from training.

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
