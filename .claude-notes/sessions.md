# Session journal

Dated summaries of Claude Code working sessions — for **context across PCs**,
not for resuming conversations. Newest first. Claude: append a short entry at
the end of each working session (what was discussed, decided, and changed).

---

## 2026-09-03 — Windows PC bootstrapped; BSW replaces the branched forward model; real data 4/6 -> 6/6

**First session on this Windows home PC since the uv migration.** It had no uv
and no `.venv` (it predates that change). Installed uv 0.12.8 via winget —
matches the Linux PC's version — then `uv sync`. Baseline confirmed 112 passing
before touching anything. Two notes for next time on this machine:
- winget says "restart your shell"; uv is not on PATH in the session that
  installed it. Full path:
  `C:\Users\krish\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_*\uv.exe`.
- **torch resolves to 2.13.0+cpu here, not +cu130.** This is EXPECTED and
  correct per environment.md: the lock's CUDA extras are marked
  `sys_platform == 'linux'`, so Windows takes PyPI's CPU wheel. This box does
  have an NVIDIA RTX A1000, but training runs on CPU (~9 s/epoch at 16k, vs
  ~11 s/epoch on the Linux GTX 1660 Ti — barely different at this model size).
  Do not "fix" this by adding a per-PC torch variant; it would break the
  single-lock guarantee.
- `originals/` is ABSENT on this PC (only an unrelated `rheo_fingerprinting`
  folder). Nothing needed it this session — every derived `data/*.npz` is
  committed, which is exactly the point of that design.

**The work: closed the §1f blocker.** User picked option (a) — give the branched
class a broader forward model — and specified a two-exponent BSW spectrum with
5 parameters. Full detail in next-actions.md §1g; the short version:
- Prototyped `bsw_spectrum` and measured it against Pivokonsky BEFORE writing
  anything into the repo. Old model 0.316/0.280 decades RMS on E/B; BSW
  0.068/0.059. Also checked up front that it does not steal planted reptation
  curves (reptation AICc -4522 vs BSW -758) — that was the real risk with a
  more flexible model, and it is why the class is safe to add.
- Wired into `identify()`'s bank (now 8 candidates), the synth generator, and
  the ML pipeline (`N_PARAMS` 4 -> 5, model imports it instead of hardcoding).
- **Real data 4/6 -> 6/6.** Both LDPE melts now `branched` at p=0.92/0.96.
  Synthetic 0.917 vs a 0.700 baseline (the BASELINE rose too, 0.627 -> 0.700,
  because identify() can finally score branched). branched per-class 0.935.
- Suite 112 -> 121.

**Two things I got wrong along the way, both worth remembering:**
1. I wrote a smoke test asserting a larger terminal-wedge exponent `n_e`
   flattens tan(delta). It does not — `n_e` reshapes the spectrum
   non-monotonically. Replaced with a claim that IS robustly true (BSW keeps
   tan(delta) > 0.5 over more decades than a single Maxwell mode). Lesson: do
   not assert a monotonic relationship in a test without checking it first.
2. Two stack tests failed after the change because the "disguised melt" fixture
   now correctly classifies as `branched` instead of a network class. That is
   the fix WORKING one level upstream, not a regression — but the overturn
   logic still needs a genuine test case, so I built a new fixture that really
   does still read as cured_elastomer from one curve. Reframed rather than
   deleted.

**Also this session:** generated a private HTML project report to
`C:\Users\krish\OneDrive - UCB-O365\CUB\ML\rheo_fingerprinting\originals\rheo-fp-report.html`
(local file, not published anywhere).

**Process note the user pushed on:** asked how long each step took, and I could
only give the times commands print themselves — I have no timer on my own edits
and correctly declined to invent numbers. Same for "what time did I send X":
the transcript carries no per-message timestamps. Keep saying "unknown" rather
than guessing; there is precedent for a bad time estimate in the 2026-09-01
entry.

---

## 2026-09-02 — First real-data evaluation; density-invariance bug found + fixed

Ran the trained classifier against the digitized literature data for the first
time (the "main open item" from 2026-09-01). Two findings, both real.

**1. The model scored 0/6 on real curves — confidently wrong (abstain_p ~ 0).**
Sanity-checked the harness first (18/20 on synthetic through the identical code
path), so it was the model, not the plumbing. Cause: the generator emitted every
curve at exactly 60 points, so the model keyed on sampling density. Real data is
11-90 points. Hand-resampling to 60 fixed 4/6 on the spot, which is what pinned
the diagnosis. Fixed structurally rather than by patching the training
distribution alone: `resample_log_grid()` in `rheofp/ml/dataset.py` now puts
every curve on a fixed 60-point log-omega grid over its own window, so ANY
uploaded point count and frequency range works; the generator additionally
varies density (`N_OMEGA_RANGE = (10, 100)`, redrawn per curve within a stack).
User's framing: "the external user can upload any number of data points across
any freq range. the framework should adjust accordingly."
After retraining: **4/6, and raw == resampled** — the invariance holds. Darby
(3 cured silicones) and Tixier (critical gel) now correct from raw points.
Synthetic accuracy 0.917 vs 0.627 baseline (0.857 before the branched widening
below). Not comparable to the old 0.932, which was measured at a uniform 60
points. Suite 102 -> 112.

**2. Pivokonsky LDPE still fails — and it is a forward-model limit, not tuning.**
Fitting `branched_spectrum` to that data drives sigma against any ceiling given
(12, then 30) and still bottoms out at ~0.19-0.28 decades RMS; a 10-mode
Maxwell fits the same curves at ~0.02. Synthetic branched sat at median
tan(delta) ~0.32 vs the real ~0.95-0.99. Widened `BRANCHED_SIGMA` to
(1.0, 10.0) (-> ~0.47). That helped the SYNTHETIC class a lot (274/277, overall
0.857 -> 0.917) and did nothing for the real melts. Recorded in
next-actions.md §1f: the 3-parameter hierarchical double-reptation form cannot
represent real LDPE — either give the branched class a broader forward model or
keep it model-only behind abstention.

Unwelcome side effect, worth remembering: pre-widening the model was
appropriately unsure on Pivokonsky (abstain_p ~0.29); post-widening it is
confidently wrong (~0.01, p(rouse_screened) ~0.99). Abstention is trained
against the model's own errors on the synthetic distribution, so it cannot flag
a material whose true class is not in that distribution. Low abstain_p is not
evidence of a correct answer on out-of-distribution material.

New: `scripts/eval_real_data.py` (reports raw AND resampled, so a regression in
the invariance shows up immediately).

---

## 2026-09-01 — ML training pipeline; all three CLAUDE.md goals complete

- **Scope correction from the user, important.** I had treated the locked env
  as a reason to avoid adding `torch` and asked permission. User clarified:
  "computer-agnostic" means *the same across machines*, NOT *keep deps
  minimal* — **install whatever is needed**, just re-lock so every PC and any
  third-party GitHub user gets the identical thing. Recorded in workflow.md
  under Preferences. Do not repeat that hesitation.
- **torch 2.13.0+cu130 added** via `uv add torch`, `requirements.txt`
  regenerated. numpy stayed 2.5.1 — no resolver collateral. CUDA works on this
  PC's GTX 1660 Ti. Also registered a `slow` pytest marker.
- **Built `rheofp/ml/`** — dataset, model, train, evaluate — plus
  `scripts/train_classifier.py` and `tests/test_ml.py`. **Suite 84 -> 102.**
  `RheoNet` (246k params) is the frozen architecture made real: conv
  curve-encoder -> masked attention pool -> two heads. Conv because the
  discriminating features are local shape in log-frequency and windows are
  randomly cropped; attention rather than mean because a stack's information
  often sits in one curve (the hottest).
- **Abstention is a learned logit**, trained against whether the classifier
  actually erred (detached). It predicts its own failures rather than applying
  a threshold after the fact.
- **Results** (16k examples, 55 epochs, ~12 min): accuracy **0.932 vs 0.680**
  for the AICc physics baseline (+0.252). Regime 0.999. Abstaining on the
  least-confident 20% -> 0.979, 30% -> 0.992. Stacks beat single curves.
  cured_elastomer and critical_gel perfect, never confused with a melt.
- **The dominant error is physics, not a defect**: 58% of all errors are
  Zimm<->Rouse, which differ only in mode-spacing exponent (1.8 vs 2.0);
  measured log-slope distributions overlap almost entirely (1.05+/-0.70 vs
  1.08+/-0.69). Added `merged_pair_accuracy` + `pair_confusions` to
  evaluate.py so this is reported honestly instead of looking like failure.
  Caveat: `rouse_screened` per-class accuracy is seed-unstable (0.20 vs 0.71);
  the merged-pair number (~0.96) is the stable one.
- **Two real bugs caught by the tests, both now guarded:**
  1. Head 2 was silently UNTRAINED — `param_targets` was always None, so
     `head_params` received zero gradient. Wired through with masked padded
     targets; verified MAE 9.96 vs 19.0 for predict-the-mean.
  2. `_auc` gave 0.0 instead of 0.5 for a constant score (ties not
     rank-averaged).
- Gitignored `checkpoints/` and `data/synthetic_train*.npz` — both are
  reproducible from scripts, so nothing generated travels via git.
- Process note: a training run was left in the background overnight and I
  misreported its elapsed time as ~10 min when it was 9h21m (idle, not
  computing). Actual compute is ~12 min. Piping through `tail` also hides all
  progress until exit — don't do that for long runs.
- **All three CLAUDE.md goals are now complete.** What's genuinely open: the
  model has never seen REAL data (everything is synthetic), no real
  temperature stack has been tested, and the yield-dominated regime still has
  no physics. See next-actions.md §3.
- One portability fix: `ndarray.ptp()` is gone in NumPy 2 — used `np.ptp()`.
- `originals/` is present on this PC (all 6 PDFs + pivo2006.xlsx).
- NOT committed — left in the working tree for the user's end-of-day sync.

---

## 2026-08-31 — Linux PC set up; elastomer + critical-gel module BUILT

- **New machine** (Linux/CachyOS, first session here). Cloned the repo to
  `~/Documents/local_drive/coding/rheo-fp`. Installed uv 0.12.8 via the
  standalone installer to `~/.local/bin` (NOT pacman — no sudo needed);
  `uv sync` built `.venv` with Python 3.12.14 + the locked deps. Baseline
  confirmed 27/27 before touching anything. Note: system Python here is 3.14,
  so always go through `uv run` — and `~/.local/bin` must be on PATH.
- **Built the elastomer/critical-gel module** (next-actions §1 steps 1-3, and
  the melt-counterexample half of step 4). Suite **27 -> 42 passing**.
  - `rheofp/models/network.py` (new module — the fractional springpot family
    has no mode ladder, so it did not belong in `maxwell.py`):
    `chasset_thirion_spectrum(w, G_inf, c, m)` and `critical_gel_spectrum(w,
    c, u)`, plus log-space fits on `multi_restart_fit`, plus
    `tan_delta_spread` as the gel discriminating statistic.
  - **Design call**: critical gel is a genuine **2-parameter** model (bare
    springpot), not the 3-param element with G_inf driven small. Both fit the
    same data equally well, so parameter count via AICc is what actually
    separates the two classes. A test asserts the 3-param fit drives
    G_inf < 1e-3 * springpot on true gel data.
  - `fitting/identify.py`: banks merged into `ALL_MODELS = MODELS |
    NETWORK_MODELS`. Pre-filter kept permissive per the original lesson — the
    ONLY hard discard added is `terminal_reached` removing both network
    classes (a permanent network cannot flow).
  - `identify()` gained `n_temperatures` and returns `abstain` /
    `abstain_reason`. Head 2 still always emits a model, per the frozen
    two-head architecture.
- **Abstention threshold — decided, please review.** Spec said "decades of
  flatness / T-shift coverage"; built with **no flatness threshold**, because
  from a single curve a melt's absent terminal relaxation is missing evidence,
  not evidence of absence — no number of flat decades ever proves a network.
  Abstains whenever best == cured_elastomer AND not terminal_reached AND
  n_temperatures < 2. Flat decades are measured and reported as confidence,
  not as a gate. Recorded in next-actions.md under "Abstention rule as built".
- **Melt counterexample passed**: Likhtman-McLeish (2002) PS 6 truncated at
  wmin = 1e-5/1e-2/1e-1/1e0 — reptation wins on AICc every time, so the
  network classes never steal real melt data. Useful finding: the ambiguity
  does NOT materialize against a real melt, because reptation's plateau +
  Rouse wing outfits a flat springpot. Also noticed `terminal_reached` is
  False even on PS 6's full window (its low-w slope is 1.02, under the 1.4
  threshold) — pre-existing detector behavior, left alone rather than tuned.
- **Validation scope, do not overstate**: both new classes are
  planted-parameter validated ONLY. Real-material validation still needs the
  user to digitize figures to xlsx. `scripts/validate_network.py` prints that
  reminder on every run.
- **Data-source correction (later same session).** Re-read Martin 2008
  (EPDM): it has NO crosslinked-network G'(w)/G''(w) figure — Fig. 2 is the
  *un-crosslinked* polymer, Fig. 6 is time-domain G(t), and only tabulated
  low-freq Ge/tan d (Table 1) + swelling-based nu (Table 2) describe the
  cured networks. So Martin cannot be the route-(b) cured-elastomer SAOS
  source. User supplied **Darby et al. 2022, J. Appl. Polym. Sci. 139,
  e52412** (Sylgard 184 / Solaris / Ecoflex 00-30) — main PDF + supp now in
  `originals/` (+ darby2022-main.txt / darby2022-supp.txt). It HAS native
  cured-PDMS frequency sweeps (Fig. 1a, Fig. S1), 0.01-100 rad/s, LVE. That
  is now the route-(b) source; Martin drops to a Table 1 single-point Ge
  check; Villar stays route (a). `docs/elastomer_litreview.md` section 3 / 3b
  / 6 and next-actions.md updated. Caveats on Darby: data-not-shared (must
  digitize), noisy G'' (expect G_inf pinned, c/m loose), filled systems,
  single T. Digitizing targets are now Darby Fig. 1a (+ optional stiff
  Fig. S1 ratios) and Tixier Fig. 2/4.
- **Darby Fig. 1a digitized + validated (still same session).** User
  digitized it into `originals/darby.ods` (moduli in kPa). New
  `scripts/prep_darby.py` converts kPa->Pa and writes `data/darby2022.npz`
  (committed) — 3 samples SY184_10-1 / Solaris_1-1 / EF0030_1-1, 16 pts,
  0.1-100 rad/s. `fit_chasset_thirion`: G_inf vs Darby Table 1 (0.01 rad/s)
  to +1% (SY, 629 vs 620 kPa), +4% (Solaris, 124 vs 120), +28% (EF, 19.4 vs
  27 — softest, ~55% sol fraction, noisiest curve, Table 1 itself +/-30%
  there); log-residual < 0.003 dec; m ~ 0.23-0.30. `identify()` -> all 3
  cured_elastomer with big AICc margins, abstains (single curve). Wired into
  `scripts/validate_network.py` (now 4-panel) + `tests/test_network.py` (3
  parametrized real-data tests). **Suite 42 -> 45 passing.** Cured-elastomer
  class is now REAL-DATA validated; only Tixier critical-gel check remains.
- pandas needs `odfpy` for .ods, deliberately NOT added to the locked env
  (one-off prep). Used `libreoffice --headless --convert-to xlsx` ->
  `originals/darby.xlsx`, which `prep_darby.py` reads. Both gitignored.
- Extracted the two Darby PDF figures with `pdfimages` to scratchpad to read
  Fig. 1a / Fig. S1 (pdftotext gave only text). Nothing new installed.
- **Tixier Fig. 2/4 digitized + validated (same session) — module now
  COMPLETE.** User digitized into `originals/tixier.xlsx` (moduli in Pa
  already, so no conversion). New `scripts/prep_tixier.py` -> committed
  `data/tixier2004.npz` (1 curve, 11 pts, 1-100 rad/s). Both G'/G''
  power-law slopes ~0.755; tan(delta) ~ 2.55 flat (spread 0.06 dec).
  `fit_critical_gel` -> u = 0.762 (Tixier Table II 0.69-0.75; = system III),
  c = 6.85 Pa, residual < 0.011 dec. `identify()` -> critical_gel, but
  ΔAICc only ~2.4 / weight 0.77 over cured_elastomer — the two are nested
  (gel = cured with G_inf->0), so when G_inf truly ~0 only param count
  separates them and ΔAICc ~2 is exactly the 1-param penalty. Correct call,
  thin margin; noted a possible future tiebreaker (the unused
  frequency-flat-tan(delta) feature) — ask user before adding.
  Wired into validate_network.py (now 5-panel) + tests (1 more). **Suite
  45 -> 46 passing.** The elastomer / critical-gel module is done: forward
  model, discriminators, abstention, and real-data validation for both
  classes + the melt counterexample.
- **Stack-level abstention resolver BUILT (same session).** `identify.py` gains
  `resolve_melt_vs_network(stack)`, `shift_factor(ref, cur)` and
  `identify_stack(stack)`; `scripts/validate_stack.py` + `tests/test_stack.py`
  (13 tests). **Suite 46 -> 59 passing.**
  - Evidence 1: terminal relaxation at ANY temperature -> melt outright.
  - Evidence 2: horizontal shift of the spectrum across the stack.
    SHIFT_DECADES_MIN = 0.5 — this finally grounds the "T-shift coverage"
    threshold the original spec asked for (melt @ Ea 60 kJ/mol over 40 K
    shifts ~1.4 dec; network shifts 0.00).
  - **Design choice worth keeping**: alignment is done on **tan(delta)**, not
    the moduli. tan(delta) is a modulus ratio so the vertical shift factor b_T
    cancels exactly — only the horizontal shift needs fitting, and nothing has
    to be assumed about how the plateau scales with T. Verified by a test that
    a pure 3x vertical rescaling reports zero shift.
  - Coarse scan + parabolic refine rather than a gradient fit: the objective is
    a smooth 1-D curve and L-BFGS-B stalls on a flat tan(delta).
  - `identify_stack` runs the single-curve pipeline on the COLDEST curve (its
    window is likeliest to hide a melt's terminal relaxation) then applies the
    resolver. It only removes unjustified confidence or adds justified
    confidence.
  - **The payoff case**: an entangled melt (broad mode ladder, terminal below
    window) is confidently called `critical_gel` by a single curve with
    abstain=False. The stack measures 1.89 decades of shift and forces the
    abstention. This is why the feature exists.
  - Honest limit, tested: Ea = 0 -> the melt does not move -> resolver says
    "network". It reports what is observable, not what is true.
- **Synthetic data generator BUILT (same session).** `rheofp/data/synth.py`,
  `scripts/generate_dataset.py`, `tests/test_synth.py` (25 tests). **Suite
  59 -> 84 passing.** Labelled stacks from all 9 classes; labels planted not
  fitted; parameter ranges read from the fitters' own bounds (tested, so the
  population and search space cannot drift); stacks share ONE parameter set
  with an Arrhenius shift (networks: Ea = 0, moduli scale with absolute T);
  random window cropping is what teaches abstention; ~2% log-normal noise;
  canonical npz out; tqdm bar; ~1200 ex/s; xlsx is a capped human backdoor.
  Round-trip through `identify()` ~82-85% on single cropped noisy curves —
  the residual confusions (Zimm<->Rouse, gel<->elastomer) are real physical
  ambiguity, which is exactly what the ML model needs to learn.
- **Generator surfaced a real bug in the stack resolver, now fixed.** A
  critical gel's tan(delta) is frequency-independent by construction, so the
  tan(delta) alignment objective is FLAT — every shift fits equally well, and
  `shift_factor` was returning the scan grid's arbitrary minimum as though it
  were a measurement (2.23 decades of pure noise). Added
  `MIN_TAN_DELTA_STRUCTURE = 0.15`; `shift_factor` now returns NaN and
  `resolve_melt_vs_network` reports "ambiguous — loss tangent is
  frequency-independent". Lesson: a flat objective is degeneracy, not a zero
  answer. Covered by tests in both test_synth.py and test_stack.py.
- Next project work: the ML training pipeline (CLAUDE.md goal 3).

---

## 2026-07-04 (later still) — Elastomer/rubber module: literature review + scope decisions

- Clarified `docs/rheology_models.md` is a **wishlist**, not current scope: added
  an Implemented/Wishlist status column. Vitrimers + polyelectrolytes already
  covered; elastomers/gels/biofluids/shape-memory/etc. are future ambition.
- Worked through what a **basic elastomer/rubber module** needs. Key physics
  ambiguity established: a permanently crosslinked elastomer and a very-high-Mw
  entangled melt can look identical in a single SAOS curve; distinguishing them
  needs a **temperature stack** (melt's terminal relaxation is T-dependent and
  eventually enters the window; a true network's plateau doesn't). Ties into the
  frozen architecture's existing abstention design. `io/data.py` already carries
  optional `T_K` per sample, so the plumbing exists. User confirmed: users will
  enter T for their data.
- Ran a literature review (web + 6 PDFs the user dropped into `originals/`,
  gitignored). Full writeup: **`docs/elastomer_litreview.md`**. Outcomes:
  - **Forward model settled**: fractional Kelvin-Voigt = frequency-domain
    Chasset-Thirion: G' = G_inf + c*omega^m*cos(pi m/2),
    G'' = c*omega^m*sin(pi m/2). 3 params, fits with existing optimizer.
    Grounded in Curro-Pincus (1983), Bonfanti springpot algebra.
  - **Data wrinkle**: the model-network papers (Villar/Valles 2001) are
    time-domain G(t), not SAOS. Villar -> route (a) param-reconstruction only
    (self-consistency, NOT independent validation — do not overstate, do not
    digitize). EPDM (Martin 2008) is the real cured-elastomer SAOS source
    (native G'/G'' + crosslink density via swelling). Tixier (2004, J. Rheol.
    48, 39) is native-SAOS but CRITICAL-GEL/near-threshold, not cured plateau;
    it anchors the gel boundary and shows u ~ 0.69-0.75 (NOT universal 0.5).
  - Melt-vs-rubber abstention counterexample: reuse existing Likhtman-McLeish
    melt npz, frequency-truncated (planted-truth).
- **DECISION (user): critical gel is a SEPARATE fine class**, not the
  G_inf->0 limit of the elastomer model. Taxonomy gains two new Solid/gel-like
  fine classes: cured elastomer + critical gel (same fractional family, scored
  and labeled distinctly). Recorded in `elastomer_litreview.md` sections 5-6.
- **Nothing built yet** — stopped at end of lit-review. Next: user digitizes
  EPDM + Tixier figures to xlsx; then build `chasset_thirion_spectrum` +
  discriminators + abstention. See `docs/elastomer_litreview.md` section 6.
- Also this session: installed `poppler-utils` (PDF text extraction) and
  `uv`-nothing-new; saved autonomy + roadmap + env facts to Claude's
  cross-conversation memory.

---

## 2026-07-04 (later) — Validated XPP pom-pom against real Pivokonsky (2006) data

- User supplied the real target data in `originals/` (gitignored, local-only):
  `1-s2.0-S0377025706000085-main.pdf` (Pivokonsky, Zatloukal & Filip 2006) and
  `pivo2006.xlsx`. Found `data/pivo2006.npz` was **already converted** from
  this same xlsx (committed in the original restructure commit `54539be`) —
  samples `E`=LDPE Escorene LD165BW1, `B`=LDPE Bralen RB0323, matching the
  paper's Fig. 2 (90 and 85 points respectively).
- Installed `poppler-utils` (winget) to extract the paper's text — got the
  full 10-mode Maxwell + XPP nonlinear parameter tables (Tables 2 and 3) for
  both melts directly from the PDF (`pdftotext -layout`).
- Rewrote `scripts/validate_pompom.py` to fit real data instead of the
  substitute Verbeeten (2001) set: `fit_maxwell` (10 modes) recovers both
  melts' measured G'/G'' to **< 0.02 decades** mean log10 error (well under a
  0.10 tolerance). Added `tests/test_pompom.py` (4 tests, all passing —
  27/27 total now).
- **Important validation-scope nuance**: only the LVE regime is validated.
  The paper's nonlinear XPP parameters (`q_i`, `λb/λs`, `α_i` in Tables 2/3)
  were fit against nonlinear flow data (extensional/shear viscosity, normal
  stress coefficients — Figs. 3-9) not digitized here. `build_xpp_table()`
  correctly assembles those published values onto the fitted linear modes,
  but true nonlinear-XPP flow prediction remains **unvalidated**. Don't
  overstate this as "fully validated" — see `rheofp/models/pompom.py`
  docstring for the precise scope.
- Updated `rheofp/models/pompom.py` docstring, `README.md` status, `CLAUDE.md`,
  and `docs/references.md` to reflect LVE-validated status (removed
  "NOT YET VALIDATED").
- **Scope decision, confirmed with user**: product only ever ingests SAOS/LVE
  data, and XPP is indistinguishable from generic multimode Maxwell in that
  regime (nonlinear q_i/α_i/λb/λs are underdetermined by LVE alone). So XPP is
  **not a classifier output class** — branched melts route through
  `branched_spectrum` (hierarchical double-reptation, already in
  `maxwell.py`) instead. `pompom.py` stays validated but out of
  `fitting/identify.py`'s model bank; recorded in its docstring + CLAUDE.md +
  README so this isn't re-litigated when ML training starts.
- Committed at end of day 2026-07-04 (env setup + pompom validation + docs all
  in one end-of-day sync).

---

## 2026-07-04 — Set up second PC + reproducible env + cross-PC brain

- Cloned `rheo-fp` to this (home) PC at `C:\Users\krish\rheo-fp`.
- User required **identical Python + dependency versions across PCs** — repo
  must be computer-agnostic, no dependency issues. The repo was NOT reproducible:
  `requirements.txt` was unpinned, and PCs differed (office 3.12, home had 3.14).
- Decided (with user): standardize on **Python 3.12** + **uv lockfile**.
- Installed uv (0.11.26) and Python 3.12.13 via uv on this PC.
- Added `pyproject.toml` (pins `requires-python = "==3.12.*"`, deps, hatchling
  build of `rheofp`, `dev` group = pytest). Generated `uv.lock`. Ran `uv sync` →
  `.venv` with locked versions; `rheofp` installed editable. **23/23 tests pass.**
- Regenerated `requirements.txt` as a pinned+hashed `uv export` (pip fallback).
- Fixed `.vscode/settings.json`: was a hardcoded office `Python312` path →
  now relative `${workspaceFolder}/.venv/Scripts/python.exe`.
- Set up cross-PC brain like the website: `CLAUDE.md` cross-PC section +
  `.claude-notes/` (README, workflow, environment, this journal).
- Note: `gh` CLI installed on this PC but not yet authenticated
  (`gh auth login` still pending — only needed for PR/issue work).

---

