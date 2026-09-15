# .claude-notes

Repo-tracked memory for Claude Code, committed to git so it **syncs across
PCs** (unlike Claude's default memory under `~/.claude/`, which stays on one
machine).

Claude: treat files here as durable project memory. Read them at the start of
work on this repo, and append new durable facts/decisions/preferences here
(then commit) instead of relying on per-machine memory. Keep one topic per
file where practical; keep entries short and dated (absolute dates).

## Index

- [next-actions.md](next-actions.md) — **live "what to do next" list; read this
  first when the user says "continue" / "pick up where we left off".**
- [sessions.md](sessions.md) — dated journal of Claude working sessions.
- [questions.md](questions.md) — **explanation sessions: what the user has asked
  about the NN, the answers, the level to pitch at, and the findings those
  questions turned up.** Read before answering "how does X work" about the
  classifier; append after any such session (they leave no commit, so the
  journal never records them).
- [environment.md](environment.md) — reproducible Python env (uv + Python 3.12).
- [workflow.md](workflow.md) — cross-PC working agreement.
