# Cross-PC workflow

User works from multiple PCs (home + office). No need to sync chat transcripts —
context travels via **git + `CLAUDE.md` + this folder**.

- **Sync rule:** pull before starting on a machine; commit + push before
  leaving it. Only committed work is visible on the other PC.
- Claude reconstructs "what changed on the other PC" from **git history**
  (`git log` / `git diff`), not from chat.
- **Untracked local files** are per-machine and invisible elsewhere. Here that
  means `.venv/` (recreated per machine via `uv sync`) and the gitignored
  `originals/` private archive — neither needs to travel.

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
