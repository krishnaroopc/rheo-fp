# Cross-PC workflow

User works from multiple PCs (home + office). No need to sync chat transcripts —
context travels via **git + `CLAUDE.md` + this folder**.

- **Sync rule:** pull before starting on a machine; commit + push before
  leaving it. Only committed work is visible on the other PC.
- **Session-start protocol (Claude, do this FIRST, before any new work):**
  `git pull` in this repo (the "website repo" mentioned historically is a
  SEPARATE project — ignore it here), fetch + prune
  to catch stray branches, then reconstruct what changed on the other PC from
  the new commits, read the updated `.claude-notes/` (esp. `next-actions.md`),
  and run the session-start checks in `next-actions.md` §0. Only after this
  sync is confirmed should new work begin. (User instruction, 2026-07-09.)
- Claude reconstructs "what changed on the other PC" from **git history**
  (`git log` / `git diff`), not from chat.
- **Untracked local files** are per-machine and invisible elsewhere. Here that
  means `.venv/` (recreated per machine via `uv sync`), the gitignored
  `originals/` private archive, and generated artefacts — `checkpoints/` and
  `data/synthetic_train*.npz`. None of them need to travel: the venv comes
  from `uv sync`, and the checkpoint/dataset are reproducible from
  `scripts/train_classifier.py` and `scripts/generate_dataset.py`.
  `originals/` only matters if you re-digitize a figure; every derived
  `data/*.npz` is committed.

## Environment reproducibility (the whole point of the uv setup)
- Env is **not** "install whatever pip gives you." It is locked: Python is
  pinned to 3.12 and every package to an exact version+hash in `uv.lock`.
- On a fresh PC: install uv, then `uv sync`. That recreates a byte-identical
  environment — same Python, same wheels — with zero dependency drift.
- See [environment.md](environment.md) for the exact commands and rationale.

## Preferences
- User does **not** need the same chat across PCs — shared *context* is enough.
- User requires **identical Python + dependency versions across PCs**; the repo
  must be computer-agnostic with no dependency issues. Do not loosen the pins.
- **What "computer-agnostic" actually means (clarified by user 2026-09-01):**
  *the same everywhere*, NOT *keep the dependency list minimal*. **Install
  whatever the work needs** — just add it to `pyproject.toml`, re-lock, and
  commit the lock so every machine gets the identical thing. Do not treat the
  lockfile as a reason to avoid a dependency, and do not stop to ask permission
  for an ordinary one; that was a misreading. Third-party users downloading
  from GitHub are likewise expected to have or install compatible software.
  "Do not loosen the pins" means do not un-pin versions — not do not add
  packages.
