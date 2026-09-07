# Archived scripts

Superseded code kept for provenance, not run by anything and not covered by
tests. Nothing in `rheofp/` imports from here.

- **`prep_interpolate.py`** — common-omega-grid interpolation, migrated from
  the notebook-era `interpolate_rheology.ipynb`. Superseded by
  `resample_log_grid()` in `rheofp/ml/dataset.py`, which is the live path every
  upload goes through and which handles arbitrary point counts and windows.
  Its own docstring already noted its raw input sheet no longer exists.
