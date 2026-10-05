# STEM Shorts Pipeline

Read docs/HANDOVER.md fully before starting. It holds all decisions, current
file contents, gotchas, and the plan for Phases 4 to 9. Current phase: 4 (prompts).

Rules:
- The files on disk are the source of truth; if they differ from the handover,
  show the diff and ask before overwriting.
- Give targeted edits, not whole-file rewrites, unless asked.
- All commands run in the Ubuntu (WSL2) terminal in ~/shorts-pipeline.
- After rebuilding containers, wait for /health before testing.
- Never print or commit secrets (.env).