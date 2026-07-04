# rheo-fp — Project Context

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

**Pom-pom notebook** (`mcleish_larson1998_pompom_fit.ipynb`): multimode
generalized Maxwell spectrum; verification target is Pivokonsky, Zatloukal &
Filip (2006, J. Non-Newt. Fluid Mech. 135, 58), two LDPE melts at 200 °C
(spectrum tables still needed).

## Immediate goals (the current task)
1. Restructure into a GitHub-ready repo "rheo-fp": sensible folder layout
   (e.g. notebooks/, src or rheofp/ package, data/, docs/), README.md,
   requirements.txt (single env file — repo is cloned per machine and the
   environment recreated from it; no Codespaces), .gitignore (strip notebook
   outputs), LICENSE.
2. Synthetic data generator: binary output (.npz or Parquet) with a
   tqdm-style progress bar. xlsx retained only as a human-facing
   sanity-check backdoor.
3. Then: ML training pipeline on the frozen architecture.

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
