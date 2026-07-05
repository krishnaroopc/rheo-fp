# Session journal

Dated summaries of Claude Code working sessions — for **context across PCs**,
not for resuming conversations. Newest first. Claude: append a short entry at
the end of each working session (what was discussed, decided, and changed).

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
