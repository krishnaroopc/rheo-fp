# Next actions (handoff across PCs)

Claude: read this at the start of work. It is the live "what to do next" list,
kept in git so it syncs between the user's home and office PCs. When the user
says something like "let's continue" / "do the next thing" / "pick up where we
left off", this is where to look. Update + commit this file as items complete.

Last updated: 2026-09-01 (Linux/home PC).

## 0. First, on any PC at session start
- Confirm the env exists: run `uv run pytest` (should be 102 passing, 4 skipped; use
  `-m "not slow"` to skip the end-to-end training test). If uv or
  the venv is missing, bootstrap per `.claude-notes/environment.md`
  (install uv, then `uv sync`). Python is pinned to 3.12 — do not change.
- Skim `.claude-notes/sessions.md` (newest entries) for what changed since.
- **CHECK FOR `originals/` AND ASK THE USER IF IT'S MISSING.** `originals/` is
  gitignored + per-machine, so it does NOT arrive via `git pull`. It holds the
  source PDFs (and my extracted `.txt`) + `pivo2006.xlsx` needed for the
  elastomer build's real-data validation. If this session is on a PC where
  `originals/` is absent or empty (e.g. first time on the office PC), and the
  active task touches those papers/data, **proactively ask the user to copy
  the `originals/` folder over** (USB/cloud) before attempting any digitizing
  or real-data validation. The forward-model code + planted-parameter tests
  can proceed without it; only the real-data steps are blocked.
  Quick check: `ls originals/` — expect the pivo, Martin EPDM, Tixier, and
  Darby 2022 (silicone) PDFs + supp + .txt.

## 1. ~~ACTIVE TASK~~ — elastomer / rubber + critical-gel module — **COMPLETE 2026-08-31**
Built, wired into `identify()`, and validated against real data (Darby 2022
cured silicones, Tixier 2004 critical gel, Likhtman-McLeish melt
counterexample), and the stack-level resolver is built too (§1c). 59 tests
pass. Files: `rheofp/models/network.py`,
`scripts/{prep_darby,prep_tixier,validate_network,validate_stack}.py`,
`data/{darby2022,tixier2004}.npz`, `tests/{test_network,test_stack}.py`.
**ALL THREE CLAUDE.md GOALS ARE NOW COMPLETE** (repo restructure, synthetic
generator, ML training pipeline). See §1e below and "What's genuinely open"
at the bottom of this file for what remains.

Full design + literature basis: `docs/elastomer_litreview.md` (read it first;
sections 0, 5, 6 are the operative ones). Summary of decisions already locked:
- Forward model = fractional Kelvin-Voigt (frequency-domain Chasset-Thirion):
  G'(w) = G_inf + c*w^m*cos(pi*m/2), G''(w) = c*w^m*sin(pi*m/2). 3 params.
- Critical gel is a SEPARATE fine class (user decision), same functional family
  with G_inf ~ 0, m ~ 0.5-0.75; label distinctly, don't merge.
- No affine/phantom split; report G_inf model-agnostically (like the XPP scope
  call). SAOS-only input; melt-vs-rubber ambiguity handled by abstention unless
  a temperature stack is present (`io/data.py` already carries T_K per sample).

### Real-data validation — DONE 2026-08-31
Both curves digitized by the user, converted by dedicated prep scripts,
outputs committed to `data/` so validation runs without `originals/`:
  (a) **Darby 2022 Fig. 1a** -> `originals/darby.ods` ->
      `scripts/prep_darby.py` (kPa->Pa there) -> `data/darby2022.npz`.
      pandas can't read .ods without `odfpy` (not in the locked env) — the
      script reads `originals/darby.xlsx`; regenerate with
      `libreoffice --headless --convert-to xlsx originals/darby.ods` on
      another PC. Martin 2008 was the old plan — dropped, no SAOS figure.
  (b) **Tixier 2004 Fig. 2/4** -> `originals/tixier.xlsx` (Pa already) ->
      `scripts/prep_tixier.py` -> `data/tixier2004.npz`. u = 0.762 recovered.

Non-blocking optional extras (never done — do only if asked):
  - Martin 2008 Table 1 single-point check (fitted G_inf vs Ge, tan d) per
    resol ratio — values transcribed in litreview section 3.
  - Villar 2001 Table 2 route-(a) self-consistency.
  - Darby Fig. S1 stiff ratios (SY 10:1 / 20:1) for a wider G_inf range.

### 1c. Stack-level abstention resolver — DONE 2026-08-31
Built in `fitting/identify.py`; `scripts/validate_stack.py`,
`tests/test_stack.py` (13 tests). Suite 46 -> 59 passing.
- `resolve_melt_vs_network(stack)` — two pieces of evidence, in priority
  order: (1) terminal relaxation observed at ANY temperature -> melt outright
  (a permanent network cannot flow at any T); (2) else how far the spectrum
  SHIFTS along omega across the stack. Verdict "melt"/"network"/"ambiguous".
- `shift_factor(ref, cur)` — horizontal log10 a_T by aligning **tan(delta)**
  curves, NOT the moduli. Key choice: tan(delta) is a modulus ratio so the
  vertical shift factor b_T cancels exactly — no simultaneous b_T fit, and no
  assumption about how the plateau scales with T. Coarse scan + parabolic
  refine (the objective is smooth 1-D; a gradient fit stalls on a flat
  tan(delta)).
- `identify_stack(stack)` — the architecture's native set-based input. Runs
  the single-curve pipeline on the COLDEST curve (hardest case: its window is
  likeliest to hide a melt's terminal relaxation), then lets the resolver
  lift the abstention or overturn a network call. It only ever removes
  unjustified confidence or adds justified confidence — never invents any.
- **SHIFT_DECADES_MIN = 0.5** — this is the "T-shift coverage" threshold the
  original spec asked for, now actually grounded: a melt with Ea ~ 60 kJ/mol
  over a 40 K spread shifts ~1.4 decades; a network shifts 0.00. 0.5 sits
  clear of both.
- Adversarial case proven: an entangled melt with a broad mode ladder and the
  terminal region below the window is confidently misclassified as
  `critical_gel` by a single curve (abstain=False!). The stack sees 1.89
  decades of shift and forces the abstention. That case is the reason this
  exists — see `test_stack_overturns_a_network_call_on_a_disguised_melt`.
- Honest limit, tested: with Ea = 0 a melt does not move, so the resolver
  calls it a network. It reports what is observable, not what is true.
- **Gap found later by the generator and fixed**: a critical gel's tan(delta)
  is frequency-INDEPENDENT by construction, so the alignment objective is FLAT
  — every shift fits equally well and the old code returned the grid's
  arbitrary minimum as if it were a measurement. Added
  `MIN_TAN_DELTA_STRUCTURE = 0.15`: `shift_factor` now returns NaN when
  tan(delta) has no structure, and the resolver reports "ambiguous — loss
  tangent is frequency-independent". Worth remembering: a flat objective is
  degeneracy, not a zero answer.

### 1d. Synthetic data generator — DONE 2026-08-31 (CLAUDE.md goal 2)
`rheofp/data/synth.py` + `scripts/generate_dataset.py` + `tests/test_synth.py`
(25 tests). Suite 59 -> 84 passing.
- Samples labelled stacks from ALL 9 classes (7 fine + wormlike_micelle and
  branched as model-only). Labels are PLANTED (from the generating model),
  never fitted.
- Parameter ranges are read from `solutions.MODELS` bounds where they exist,
  so the generated population and the fitters' search space cannot drift
  apart — there is a test asserting this.
- **Stacks are physically coherent, not independent draws**: a T-stack
  Arrhenius-shifts ONE parameter set (networks get Ea = 0 and instead scale
  moduli with absolute T, i.e. entropic elasticity). Independent per-curve
  draws would teach the classifier a correlation no real material has.
- Random window CROPPING (0-2.5 decades) is deliberate: it is what teaches
  abstention, by hiding the terminal region the way a real instrument does.
- ~2% log-normal noise, matching digitizing scatter on real figures.
- Output = canonical npz layout, so generated data loads with the same loader
  as the digitized literature data; carries label/regime/stack_id/n_curves.
- xlsx export exists but is a capped human backdoor only (200 samples), per
  CLAUDE.md. Never in an automated path, do not commit its output.
- Throughput ~1200 examples/s. Identifier round-trip on single cropped noisy
  curves ~82-85%; the confusions are Zimm<->Rouse (differ only in exponent),
  reptation->Zimm when the crop hides the plateau, and gel<->elastomer (nested
  models). Those are REAL ambiguity for the ML model to learn, not defects.

### Build steps (Claude, once asked / once xlsx exists)
Planted-parameter tests need NO data, so building can start before digitizing:
1. DONE (2026-08-31). `rheofp/models/network.py` — new module (the fractional
   springpot family has no mode ladder, so it did not belong in `maxwell.py`).
   `chasset_thirion_spectrum` (3-param) + `critical_gel_spectrum` (2-param bare
   springpot) + `fit_*` via `multi_restart_fit`. Critical gel is kept a genuine
   2-parameter model, not a 3-param fit with G_inf driven small — that is what
   lets AICc adjudicate the two classes on parameter count.
2. DONE (2026-08-31). `tests/test_network.py` +
   `scripts/validate_network.py` (plt.show only). Suite 27 -> 59 passing.
3. DONE (2026-08-31). Both classes wired into `fitting/identify.py` via
   `NETWORK_MODELS`, merged into a new `ALL_MODELS` bank. Pre-filter stays
   permissive: the ONLY hard discard for the network classes is
   `terminal_reached` (a permanent network cannot flow). Abstention decision —
   see "Abstention rule as built" below.
4. DONE (2026-08-31).
   - Melt counterexample: Likhtman-McLeish PS 6 at four low-freq truncations,
     reptation wins every time, network classes never steal it. DONE.
   - Darby 2022 real cured-elastomer: `data/darby2022.npz`, fit with
     `fit_chasset_thirion` -> G_inf recovered to +1%/+4%/+28% (SY/Solaris/EF)
     vs Darby Table 1 (620/120/27 kPa @ 0.01 rad/s); residual < 0.003 dec;
     m ~ 0.23-0.30; identify() -> cured_elastomer + abstain for all 3.
     In validate_network.py + tests (3 parametrized). DONE.
     Note EF is +28% off — the softest, ~55%-sol-fraction kit, digitized off
     the noisiest curve, and Table 1 has +/-30% error there. Acceptable; test
     tol is 35%.
   - Tixier 2004 real critical gel: `data/tixier2004.npz` (moduli in Pa
     already), `scripts/prep_tixier.py`. `fit_critical_gel` -> u = 0.762
     (Tixier Table II range 0.69-0.75), residual < 0.011 dec. identify() ->
     critical_gel, but ΔAICc only ~2.4 / weight 0.77 over cured_elastomer:
     the models are nested (gel = cured, G_inf->0), so when G_inf ~ 0 only
     the param count separates them and ΔAICc ~ 2 is the expected 1-param
     penalty. Correct call, thin margin. Possible future tiebreaker: use the
     frequency-flat-tan(delta) feature (currently computed, unused). Ask
     user first. DONE.
   - Optional anytime: Villar 2001 Table 2 route-(a); Martin 2008 Table 1/2.

### Abstention rule as built (2026-08-31) — revisit if you disagree
The threshold was specified as "decades of flatness / T-shift coverage". Built
deliberately WITHOUT a flatness threshold: from one curve, a melt's absent
terminal relaxation is missing evidence, not evidence of absence, so no number
of flat decades ever proves a network. `melt_rubber_ambiguous()` therefore
abstains whenever best == cured_elastomer AND not terminal_reached AND
n_temperatures < MIN_STACK_TEMPERATURES (= 2). Flat decades are still measured
and reported (`features["flat_decades_lo"]`) as confidence, not as a gate.
`identify(..., n_temperatures=N)` lifts the abstention. Critical gel never
abstains — it has no plateau to confuse with a melt.
Superseded 2026-08-31 for stacks: `identify_stack()` now runs the real per-T
check (see 1c above). `identify()` on a single curve still behaves exactly as
described here — n_temperatures is only a hint there.

## 2. Standing background facts (not blocking)
- XPP/pom-pom: LVE-validated but deliberately NOT a classifier class. Done.
- `docs/rheology_models.md` is a wishlist (elastomers is the first item being
  pulled off it). Other domains there (biofluids, cement, etc.) are future,
  not current scope.
- Commit/push policy: user commits at end of a working session ("when I'm done
  for the day"), not continuously. Ask/confirm before end-of-day sync.


### 1e. ML training pipeline — DONE 2026-09-01 (CLAUDE.md goal 3)
`rheofp/ml/{dataset,model,train,evaluate}.py`, `scripts/train_classifier.py`,
`tests/test_ml.py` (18 tests). Suite 84 -> 102 passing.
- **torch added to the locked env** (2.13.0+cu130). Re-locked properly; numpy
  stayed 2.5.1. See environment.md and the workflow.md preference note — the
  user explicitly wants deps added when needed, not avoided.
- `RheoNet` = conv curve-encoder -> masked attention pool -> two heads, exactly
  the frozen architecture. 246k params. Conv over log-frequency because the
  discriminating features are LOCAL SHAPE (terminal slope, plateau, wing) and
  the generator crops windows to random positions. Attention pool (not mean)
  because a stack's information often sits in ONE curve — the hottest, where
  terminal relaxation finally enters the window.
- Abstention is a **learned logit**, trained against whether the classifier
  actually got that example wrong (detached, so it does not steer the
  classifier). It learns to predict its own failures.
- Leakage guards, both tested: splits are **by stack** (temperature twins must
  never straddle train/test), and normalisation stats come from the **training
  split only**.
- Padding cannot influence output — tested by poisoning padded slots with 1e3
  and asserting identical logits.

**Results (16k examples, 55 epochs, seed 1, GTX 1660 Ti, ~12 min):**
  accuracy 0.932 vs AICc physics baseline 0.680 (+0.252)
  regime accuracy 0.999; abstain 20% -> 0.979, 30% -> 0.992
  stacks beat single curves (0.924 at N=1 -> 0.951 at N=2)
  cured_elastomer and critical_gel are PERFECT and never confused with a melt
  58% of ALL errors are Zimm<->Rouse, which differ only in mode-spacing
  exponent 1.8 vs 2.0 — measured log-slopes 1.05+/-0.70 vs 1.08+/-0.69, i.e.
  near-total overlap. That is physics, not a defect; `evaluate.py` now reports
  `merged_pair_accuracy` and `pair_confusions` so it cannot be misread.

**Two real bugs the tests caught — do not reintroduce:**
1. Head 2 was silently UNTRAINED: `param_targets` was always None so
   `head_params` got zero gradient. Now wired via masked padded targets (a
   2-param gel must not train the 2 unused slots). Verified: MAE 9.96 vs 19.0
   for predicting the mean. Guarded by
   `test_head_two_receives_gradient_from_the_parameter_loss`.
2. `_auc` returned 0.0 for a constant (useless) score instead of 0.5 — ties
   were not rank-averaged. Fixed and tested.

**Known instability:** `rouse_screened` per-class accuracy swings a lot by seed
(0.20 on seed 0, 0.71 on seed 1) — the model sometimes collapses the
degenerate pair onto one member. Check `merged_pair_accuracy` (stable ~0.96)
before concluding anything is broken.

## 3. What's genuinely open
- Train on / validate against REAL data. Everything above is synthetic; the
  model has never seen a measured spectrum. The 4 literature datasets in
  `data/` are the obvious first test.
- No temperature stack has ever been tested on real material — the stack
  resolver and the stack-aware model are both synthetic-only so far.
- Yield-dominated regime has no implemented physics at all (3rd taxonomy
  regime is empty).
- Optional: Zimm/Rouse tiebreaker; critical-gel AICc tiebreaker via the unused
  frequency-flat-tan(delta) feature; Villar/Martin tabulated checks.
