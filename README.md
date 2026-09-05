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
baseline; on synthetic data the network scores ~0.92, with abstention lifting
accuracy to ~0.97 at 20% coverage dropped. The previously published ~0.70 for
the baseline was measured before `wormlike_micelle` had a candidate in the
identifier's bank, so ~1/9 of its test pool was unanswerable by construction;
a standalone re-measurement over the fixed 9-candidate bank puts it near ~0.82
(n=90). The paired figure will be regenerated on the next training run - see
`.claude-notes/next-actions.md` §1h.
Requires PyTorch (a locked dependency); uses CUDA when available, CPU
otherwise.

```
python scripts/eval_real_data.py          # trained checkpoint vs the literature sets
```

## Status

- `rheofp/models/maxwell.py`, `tube.py`, `solutions.py`: validated (forward
  physics reproduces published figures; inverse fits recover planted
  parameters).
- `rheofp/models/network.py`: validated, including against real measured data —
  cured elastomers (Darby et al. 2022, three commercial silicones) and a
  critical gel (Tixier et al. 2004, end-linked PDMS near the sol-gel
  threshold).
- `rheofp/fitting/identify.py`: AICc identifier over a 9-candidate bank - one
  per class the generator can produce - with single-curve abstention and a
  temperature-stack resolver for the melt-vs-network ambiguity.
- `rheofp/models/maxwell.py` `bsw_spectrum`: the branched / long-chain-branched
  melt class (Baumgärtel–Schausberger–Winter spectrum, 5 parameters). Validated
  against real LDPE — Pivokonsky et al. (2006) melts E and B, fit to under 0.07
  decades, where the earlier 3-parameter double-reptation form could not get
  below ~0.28.
- `rheofp/data/synth.py`: synthetic training-set generator (labelled stacks,
  planted parameters, physically coherent temperature stacks).
- `rheofp/models/pompom.py`: LVE validated against the real target — Pivokonsky
  et al. (2006) LDPE melts (data/pivo2006.npz). Nonlinear XPP flow prediction
  is out of scope (not digitized). Not a classifier output class either way —
  branched melts are classified via the BSW spectrum (`bsw_spectrum` /
  `model_branched` in `maxwell.py`), since XPP is indistinguishable from generic
  Maxwell in LVE; see module docstring for exact scope.
- `rheofp/ml/`: two-head set model (masked attention pooling over a stack) with
  a learned abstention head. **Trained on synthetic data only**, then evaluated
  against the digitized literature sets: currently 6/6 correct. That is six
  curves from three papers, all single-temperature, four of them the same
  material family — do not read either the synthetic accuracy or the 6/6 as
  general real-world performance. Abstention is trained against the model's own
  synthetic errors and does not fire on out-of-distribution material.

## License

MIT — see `LICENSE`.
