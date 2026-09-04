# Cross-PC workflow

User works across **three machines**: two Windows PCs (home + office) and a
Linux box (CachyOS). No need to sync chat transcripts — context travels via
**git + `CLAUDE.md` + this folder**.

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

### Per-machine gotchas (found the hard way, don't re-debug these)
- **Windows, right after `winget install astral-sh.uv`:** the installer says
  "restart your shell" and means it — `uv` is NOT on PATH in the session that
  installed it. Either open a new terminal, or call it by full path:
  `C:\Users\krish\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_*\uv.exe`.
- **Windows gets `torch==2.13.0+cpu`, Linux gets `+cu130`. This is correct.**
  The lock marks the CUDA extras `sys_platform == 'linux'`, so Windows resolves
  PyPI's CPU wheel from the SAME lockfile. A Windows box with an NVIDIA card
  (the home PC has an RTX A1000) will still report
  `torch.cuda.is_available() == False`. Do NOT "fix" this with a per-PC torch
  variant — one lock for every machine is the whole guarantee. At this model
  size it barely matters: ~9 s/epoch CPU vs ~11 s/epoch on the Linux GTX 1660 Ti.
- **Full test suite is ~3 minutes** since `identify()` gained the 5-param BSW
  candidate (8 models × multi-restart fits). Use `-m "not slow"` (~2 min) to
  skip the end-to-end training test. Not a hang.

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
