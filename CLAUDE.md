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
identification and (2) fitted constitutive model parameters. Built in Jupyter
notebooks (Python / NumPy / SciPy / Matplotlib). Currently a collection of
validated notebooks; the immediate task is converting this into a professional
GitHub repository named "rheo-fp".

## Classifier architecture (FROZEN — do not redesign)
- **Input**: set-based stacks of spectra (multiple curves across temperature
  or concentration). Single-curve input is the degenerate N=1 case via masked
  attention pooling. Stacks enable classification from trends across T or c.
- **Output**: two heads. Head 1 emits material type, with abstention when the
  input lacks discriminating information. Head 2 always emits a best-fit model.
- **Taxonomy**: 3 regimes (Terminal/liquid-like, Solid/gel-like,
  Yield-dominated); 8 fine classes (4 identifiable from single curves, 4
  requiring stacks); 6 model-only classes (regime-level labels only).
  Wormlike micelles are model-only. Glassy regime was dropped.

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
point. Also hierarchical double-reptation branched/LCB spectrum.
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
nonlinear parameters are underdetermined by LVE data alone. Branched melts
are represented for classification via `branched_spectrum` (hierarchical
double-reptation, already in `maxwell.py`) instead. `pompom.py` is not wired
into `fitting/identify.py`'s model bank and stays as a validated
reference/tool, not part of the SAOS-only pipeline.

## Goals — ALL THREE COMPLETE as of 2026-09-01
1. DONE. Restructured into the GitHub-ready `rheo-fp` package (rheofp/,
   scripts/, data/, docs/, tests/), README, locked env, .gitignore, LICENSE.
2. DONE. Synthetic data generator — `rheofp/data/synth.py` +
   `scripts/generate_dataset.py`. Binary npz out, tqdm bar; xlsx kept only as
   a capped human sanity-check backdoor.
3. DONE. ML training pipeline — `rheofp/ml/` + `scripts/train_classifier.py`.
   Two-head set model (conv encoder -> masked attention pool -> classify +
   regress) with a learned abstention head, on the frozen architecture.

**Current state:** 102 tests pass. On synthetic data the classifier scores
~0.93 vs ~0.68 for the AICc physics baseline. **It has never been trained on
or evaluated against real measured spectra** — that is the main open item.
See `.claude-notes/next-actions.md` §3 for what is genuinely open.

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
Likhtman & McLeish (2002); McLeish & Larson (1998); Leibler–Rubinstein–Colby
(1991); Rubinstein–Semenov (1998, 2001); Stukalin et al. (2013); Colby (2010);
Dobrynin–Colby–Rubinstein (1995); Pivokonsky et al. (2006).
