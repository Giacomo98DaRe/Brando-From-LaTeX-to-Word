# Brando project instructions

Brando is an independent, local desktop Overleaf/LaTeX project to editable DOCX converter.
Communicate with Giacomo in concise Italian. Keep code, documentation and reports in English.

## Resume and working memory

- When present, read `history/STATUS.md` before continuing substantial work. Consult `history/DECISIONS.md`
  for settled choices and `history/WORKLOG.md` for evidence and unsuccessful approaches.
- Update these files after a meaningful implementation/validation milestone or before handing
  off an unfinished task. Record what actually ran, failures, remaining gaps and the next step.
- Keep durable instructions here short; put changing implementation status in `history/`.
- `history/` is local working memory and must stay ignored by Git. On a fresh clone without
  history, use the maintained README and docs; do not require missing local memory files.
- Maintain `history/COMMIT_PLAN.md` for the current change cycle: ordered commit groups,
  purpose, paths, required verification and progress. When both the working tree and staging
  area are clean (`git status --porcelain` is empty, including relevant untracked files),
  overwrite the plan to start a fresh cycle covering only subsequent changes. Update the
  active plan as scope evolves; do not overwrite an unfinished plan while changes remain.
  Ignored local history/tool/output files do not prevent a clean Git baseline.
- If resuming the initial implementation, read the two original handoff Markdown documents
  in `overleaf_word_handoff/` when available. The handoff and corpus are local evaluation
  inputs, excluded from Git and public builds; do not modify their upstream source files.

## Scope and authorization

- Keep NAIARA and all scientific Python/Conda environments unchanged. Use the project `.venv`.
- Handle local Git commits yourself as part of the normal project workflow, gradually and
  according to an ordered plan. Group coherent, reviewable changes into focused commits;
  verify each group and use clear messages. Do not make one blanket commit of unrelated work.
  Respect any explicit temporary instruction to postpone commits; record its current status
  and the proposed commit sequence in local history. The user need not execute Git commands.
- Pushes, remote repository creation and release publication still require an explicit user
  request. Local development, testing and reviewable packaging are authorized.
- All document processing stays on the user's computer. No accounts, uploads, telemetry or
  conversion services. Do not run project-provided scripts or unrestricted TeX compilation.
- Preserve input files and earlier exports. Keep imported resource access within the captured
  project, apart from installed engine/runtime resources. Maintain bounded ZIP ingestion,
  cancellation and subprocess timeouts.

## Implementation conventions

- Python 3.12+, shared portable conversion core and PySide6 Widgets UI; isolate OS integration.
- Keep source-template recognition separate from Word styling. All template families are
  experimental until supported by explicit content and packaged-app evidence.
- Source comments are opt-in, distinct from Overleaf Review-panel discussions. Report actual
  comment coverage and anchor locations. Never imply that Word edits synchronize to LaTeX.
- Generated DOCX must not require Word, Git, Python or a separately installed engine for users
  of the packaged app. Optional tools must not silently run or alter system configuration.
- Write original synthetic public fixtures. Keep corpus downloads, personal paths, outputs,
  development environments and proprietary manuscripts out of the publishable source tree.
- Keep `.gitignore` organized into clearly commented categories. Put disposable/local research
  material in ignored directories immediately. Only allowlist reviewed synthetic document
  fixtures under `examples/` or `tests/fixtures/`; do not force-add private or upstream inputs.
- Record dependency versions, licenses and distribution obligations before bundling them.
- Prefer direct, readable functions and descriptive names. Remove proven-unused code and
  explain non-obvious constraints in comments. Preserve independent validation checks.
- Format maintained Python with the pinned development-only Ruff configuration. Keep
  third-party sources, license texts and local research inputs outside formatting changes.

## Verification and commands

- Run `.venv/Scripts/python.exe -m pytest` on Windows (`.venv/bin/python -m pytest` elsewhere).
- Check Python quality with `.venv/Scripts/python.exe -m ruff check src tests scripts` and
  `.venv/Scripts/python.exe -m ruff format --check src tests scripts` before committing Python.
- Local engine benchmark: `.venv/Scripts/python.exe scripts/benchmark.py`; needs the ignored
  handoff bundle and evaluation-only Pandoc installation. It must never enter remote CI.
- GUI: `.venv/Scripts/pythonw.exe -m brando`; CLI help:
  `.venv/Scripts/python.exe -m brando.cli --help`. Build entry: `scripts/build.py`.
- Successful exit codes and valid XML do not establish fidelity. Check independently expected
  source text, authors, chapters, numerical signs/decimals/exponents, citations and assets.
- Distinguish missing fixture dependencies from regressions. Distinguish structural checks,
  Word rendering, LibreOffice rendering and clean-machine packaging validation.
- Do not claim platform support from an untested build or from tests on a different OS.
- Keep Windows build dependency discovery isolated from unrelated host PATH entries. The
  builder's clean analysis and workspace cache prevent accidental native DLL contamination.
