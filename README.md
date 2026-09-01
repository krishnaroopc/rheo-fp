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
  models/           forward physics: maxwell, tube, solutions, network, pompom
  fitting/          shared optimizer core + AICc-based regime identification
  data/             synthetic training-set generator
  ml/               dataset, two-head set model, training, evaluation
  io/               data loading/conversion (npz canonical format)
scripts/            validation, data prep, generation, training
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
python scripts/validate_pompom.py        # XPP pom-pom fit (LVE only - see module docstring)
python scripts/validate_network.py       # cured elastomer + critical gel, incl. real data
python scripts/validate_stack.py         # melt-vs-network resolution across a T stack
python scripts/prep_interpolate.py       # common-omega-grid interpolation utility
```

## Generating data and training the classifier

```
python scripts/generate_dataset.py -n 20000 -o data/train.npz
python scripts/train_classifier.py -n 16000 --epochs 55
```

`train_classifier.py` reports against the AICc physics identifier as a
baseline; on synthetic data the network scores ~0.93 against ~0.68 for the
baseline, with abstention lifting accuracy to ~0.98 at 20% coverage dropped.
Requires PyTorch (a locked dependency); uses CUDA when available, CPU
otherwise.

## Status

- `rheofp/models/maxwell.py`, `tube.py`, `solutions.py`: validated (forward
  physics reproduces published figures; inverse fits recover planted
  parameters).
- `rheofp/models/network.py`: validated, including against real measured data —
  cured elastomers (Darby et al. 2022, three commercial silicones) and a
  critical gel (Tixier et al. 2004, end-linked PDMS near the sol-gel
  threshold).
- `rheofp/fitting/identify.py`: AICc identifier over a 7-candidate bank, with
  single-curve abstention and a temperature-stack resolver for the
  melt-vs-network ambiguity.
- `rheofp/data/synth.py`: synthetic training-set generator (labelled stacks,
  planted parameters, physically coherent temperature stacks).
- `rheofp/models/pompom.py`: LVE validated against the real target — Pivokonsky
  et al. (2006) LDPE melts (data/pivo2006.npz). Nonlinear XPP flow prediction
  is out of scope (not digitized). Not a classifier output class either way —
  branched melts are classified via `branched_spectrum` in `maxwell.py`
  instead, since XPP is indistinguishable from generic Maxwell in LVE; see
  module docstring for exact scope.
- `rheofp/ml/`: two-head set model (masked attention pooling over a stack) with
  a learned abstention head. Trained and evaluated on synthetic data only —
  **it has not yet been trained on or validated against real measured
  spectra.** Do not read the synthetic accuracy as real-world performance.

## License

MIT — see `LICENSE`.
