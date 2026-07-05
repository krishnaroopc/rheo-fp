# rheo-fp

An open-source ML classifier for linear rheology. Ingests small-amplitude
oscillatory shear (SAOS) data — G′(ω), G″(ω) — and outputs (1) material type
identification and (2) fitted constitutive model parameters.

## Architecture

- **Input**: set-based stacks of spectra (multiple curves across temperature
  or concentration). A single curve is the degenerate N=1 case.
- **Output**: two heads — material-type classification (with abstention when
  the input lacks discriminating information) and a best-fit constitutive
  model, always emitted.
- **Taxonomy**: 3 regimes (Terminal/liquid-like, Solid/gel-like,
  Yield-dominated); 8 fine classes; 6 model-only classes.

See `CLAUDE.md` for the full architecture rationale and validation history.

## Layout

```
rheofp/            importable package
  models/           forward physics: maxwell, tube, solutions, pompom
  fitting/          shared optimizer core + AICc-based regime identification
  io/               data loading/conversion (npz canonical format)
scripts/            validation scripts (plot + assert against known-good results)
data/               converted spectral datasets (.npz, open format)
docs/               reference bibliography, model-taxonomy notes
tests/              pytest regression tests
```

No `.ipynb` or `.xlsx` files are distributed in this repository, and none of
`rheofp/`, `scripts/`, or `tests/` read from anywhere outside the repo -
everything needed to run tests, validation scripts, or build on this work
lives here. Original working notebooks and source spreadsheets stay
local-only in a gitignored `originals/` folder purely as a private archive;
it was only ever needed for the one-time xlsx -> npz conversion into `data/`,
which is already done and committed. You do not need to carry `originals/`
to another machine to work on this repo.

## Setup

The environment is locked for reproducibility across machines (Python pinned to
3.12, exact dependency versions + hashes in `uv.lock`). Recommended:

```
# install uv once:  winget install --id=astral-sh.uv -e
uv sync
```

`uv sync` installs Python 3.12 (managed by uv) and all locked dependencies into
a local `.venv/`, and installs this package editable. Run things with `uv run`,
e.g. `uv run pytest`.

pip fallback (also fully pinned — from the same lock):

```
pip install -r requirements.txt
```

See `.claude-notes/environment.md` for details and how to change dependencies.

## Running the validation scripts

Each forward-model module has a corresponding script that reproduces its
planted-parameter recovery / literature-figure checks and plots the result:

```
python scripts/validate_maxwell.py       # Maxwell/Prony family, WLM, sticky-Maxwell stack
python scripts/validate_tube.py          # Likhtman-McLeish tube model + branched/LCB
python scripts/validate_solutions.py     # Zimm/Rouse/reptation regime identifier
python scripts/validate_pompom.py        # XPP pom-pom fit (NOT YET VALIDATED - see module docstring)
python scripts/prep_interpolate.py       # common-omega-grid interpolation utility
```

## Status

- `rheofp/models/maxwell.py`, `tube.py`, `solutions.py`: validated (forward
  physics reproduces published figures; inverse fits recover planted
  parameters).
- `rheofp/models/pompom.py`: LVE validated against the real target — Pivokonsky
  et al. (2006) LDPE melts (data/pivo2006.npz). Nonlinear XPP flow prediction
  is out of scope (not digitized). Not a classifier output class either way —
  branched melts are classified via `branched_spectrum` in `maxwell.py`
  instead, since XPP is indistinguishable from generic Maxwell in LVE; see
  module docstring for exact scope.
- ML training pipeline: not yet started.

## License

MIT — see `LICENSE`.
