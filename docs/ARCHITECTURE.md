# Architecture

- `project.py`: bounded byte capture from folders/ZIPs, enclosing-directory normalization,
  path checks, encoding fallback, source comments and heuristic main-root discovery.
- `engine_worker.py`: isolated tex2word pure-parser process. Python audit events restrict file
  reads to the captured project/work directory and installed runtime resource directories;
  subprocesses and sockets are disabled. This is not a general OS sandbox for arbitrary code.
- `adapters.py` applies small source-family mappings to temporary TeX copies and records their
  per-file counts. The initial Springer mappings cover bottom rules and equal-contribution
  notes while preserving literal examples. Source hashes describe the original captured bytes.
- `fidelity.py`: independent static include traversal, conservative title/author text checks
  and simple-tabular signed/decimal/scientific numeric-token checks. Skipped constructs are
  explicit; these observations do not establish full content equivalence.
- `core.py` coordinates options, capture, the cancellable worker, independent observations
  and atomic timestamped exports.
- `word.py` owns DOCX inspection, review formatting and native source-comment handling.
- `gui.py`: PySide6 Widgets controls, background tasks, local drag/drop and output opening.
  Import and conversion never block the UI thread. Word is opened only on user action.
- `widgets.py` provides the large project drop target, keyboard-operable switches and option
  information controls. Help wraps within a bounded tooltip, with a short hover delay and
  stable placement beside its control; click/Space opens it and Escape dismisses it.
  ZIP/folder selection and drop use the same capture entry point and display the selected name.
  The read-only details panel explains session messages and their saved export counterparts.
  The footer indicator and conversion button share the required-option readiness check.
  Status uses neutral, progress, green-ready and red-error colors with a readable text label.
  `appearance.py` applies light or dark colors to the same widget tree.
  The theme choice is local to the window session. Compact windows scroll the content while
  conversion actions remain available.
- `desktop.py` isolates Windows application identity and per-window native title-bar colors.
  The approved crayon B icon and stylesheet are packaged under `brando/resources`.
- `cli.py`: development/automation adapter to the same core.
- `__main__.py` dispatches GUI, CLI and isolated-worker modes. The frozen build uses this
  same entry point through a minimal wrapper.
- `scripts/build.py`: platform-local freezing, notice collection, portable archive and manifest.

The GUI caches the byte snapshot captured when an input is selected. Conversion uses those
bytes, even if original files change later; reselect the input to refresh. Reports identify
captured contents by hashes. No project script, Git operation, shell escape or build command
is executed from manuscript input. The bundled engine may parse local `.sty`/`.cls` source as
data; optional compilation is blocked. Development downloads are separate from conversion.

Source-template detection identifies the document class; overrides select the engine's class
semantics. Readable review output uses single-column Normal styling; a supplied reference
DOCX provides styles/theme/page geometry. Template recognition does not imply visual copying.

Cancellation stops import checkpoints or kills the isolated engine process. It is checked
again before publication. Postprocessing currently completes its bounded operation before
observing cancellation. No destination export folder is created until processing completes.
The complete export is staged inside the destination and published by a directory rename.
A failed report or document write cleans up the staging directory before returning the error.

`annotations.py` places percent source notes beside unique nearby source text in Word.
It uses static include traversal and normalized text from adjacent source lines, with separate
handling of headings and captions. Ambiguous text, unused files and unresolved source locations
use a final source-location appendix. Reports record each actual Word comment ID and anchor.
The opt-in collection covers every captured `.tex`/`.bib` file.
Supported inline `todo`, `comment` and `note` macros retain engine-provided manuscript anchors
when enabled. The checkbox also removes those annotations when disabled. Reports distinguish
matched body, appendix and engine-inline comment counts. Text matching is conservative and
requires review for macro-heavy sources. No parsing markers are inserted into the source.

Future work should extend fidelity observations and adapters based on observed regressions,
then tighten supported-template status. Optional generated-figure compilation needs a separate
explicit execution policy and portable tool distribution. Brando currently disables it.
