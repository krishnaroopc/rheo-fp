# Next actions (handoff across PCs)

Claude: read this at the start of work. It is the live "what to do next" list,
kept in git so it syncs between the user's home and office PCs. When the user
says something like "let's continue" / "do the next thing" / "pick up where we
left off", this is where to look. Update + commit this file as items complete.

Last updated: 2026-07-04 (end of day, home PC).

## 0. First, on any PC at session start
- Confirm the env exists: run `uv run pytest` (should be 27 passing). If uv or
  the venv is missing, bootstrap per `.claude-notes/environment.md`
  (install uv, then `uv sync`). Python is pinned to 3.12 — do not change.
- Skim `.claude-notes/sessions.md` (newest entries) for what changed since.

## 1. ACTIVE TASK — build the elastomer / rubber + critical-gel module
Full design + literature basis: `docs/elastomer_litreview.md` (read it first;
sections 0, 5, 6 are the operative ones). Summary of decisions already locked:
- Forward model = fractional Kelvin-Voigt (frequency-domain Chasset-Thirion):
  G'(w) = G_inf + c*w^m*cos(pi*m/2), G''(w) = c*w^m*sin(pi*m/2). 3 params.
- Critical gel is a SEPARATE fine class (user decision), same functional family
  with G_inf ~ 0, m ~ 0.5-0.75; label distinctly, don't merge.
- No affine/phantom split; report G_inf model-agnostically (like the XPP scope
  call). SAOS-only input; melt-vs-rubber ambiguity handled by abstention unless
  a temperature stack is present (`io/data.py` already carries T_K per sample).

### Blocking sub-step the USER must do (needs the gitignored PDFs)
Digitize two figures into xlsx (same convention as `originals/pivo2006.xlsx`:
col 0 = omega rad/s, paired `<sample> G'`/`<sample> G''` cols), then convert to
.npz via `rheofp/io/data.py`:
  (a) EPDM frequency sweep — `originals/1-s2.0-S0032386108001419-main.pdf`
      (Martin 2008) -> cured-elastomer real-data check.
  (b) Tixier Fig 2 or 4 — `originals/39_1_online.pdf` (Tixier 2004)
      -> critical-gel real-data check.
NOTE: `originals/` is gitignored and per-machine. To do the build/validation on
the office PC, copy the `originals/` PDFs over (they are NOT in git). The
digitizing itself is a human step (WebPlotDigitizer).

### Build steps (Claude, once asked / once xlsx exists)
Planted-parameter tests need NO data, so building can start before digitizing:
1. Add `chasset_thirion_spectrum` forward + fit (new `rheofp/models/network.py`,
   or into `maxwell.py` — decide at build time). Log-space fit via the existing
   `rheofp/fitting/optimize.py` `multi_restart_fit`.
2. Planted-parameter recovery tests (`tests/test_network.py`) + a
   `scripts/validate_network.py` (plt.show only, no savefig — house style).
3. Wire two new Solid/gel-like fine-class discriminators (cured elastomer,
   critical gel) + the abstention rule into `rheofp/fitting/identify.py`.
   Abstention threshold (decades of flatness / T-shift coverage) is a design
   decision — surface it to the user, grounded via the melt counterexample.
4. Real-data validation: digitized EPDM + Tixier xlsx->npz; Villar (2001) via
   parameter-reconstruction ONLY (self-consistency, not independent — see
   litreview 3a caveat); melt counterexample = existing Likhtman-McLeish npz
   with a truncated frequency window.

## 2. Standing background facts (not blocking)
- XPP/pom-pom: LVE-validated but deliberately NOT a classifier class. Done.
- `docs/rheology_models.md` is a wishlist (elastomers is the first item being
  pulled off it). Other domains there (biofluids, cement, etc.) are future,
  not current scope.
- Commit/push policy: user commits at end of a working session ("when I'm done
  for the day"), not continuously. Ask/confirm before end-of-day sync.
