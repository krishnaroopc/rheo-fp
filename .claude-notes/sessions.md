# Session journal

Dated summaries of Claude Code working sessions — for **context across PCs**,
not for resuming conversations. Newest first. Claude: append a short entry at
the end of each working session (what was discussed, decided, and changed).

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
