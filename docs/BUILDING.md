# Development

## Set up and run

Use CPython 3.12.16 and uv 0.13.7 in a dedicated project environment.

```powershell
uv sync --frozen --extra dev --python 3.12.16 --managed-python
.venv/Scripts/pythonw.exe -m brando
```

Run the required checks before committing Python changes.

```powershell
.venv/Scripts/python.exe -m ruff check src tests scripts
.venv/Scripts/python.exe -m ruff format --check src tests scripts
.venv/Scripts/python.exe -m pytest
```

Apply formatting with `ruff format src tests scripts`. On macOS/Linux use `.venv/bin/python`.
Runtime dependencies and development tools are pinned in `uv.lock`.

## Command line

```powershell
.venv/Scripts/python.exe -m brando.cli examples/article --destination outputs
.venv/Scripts/python.exe -m brando.cli project.zip --main main.tex --destination outputs --comments
```

Use `--main` for an ambiguous or nested document root. See `--help` for the remaining options.
User-facing option behavior is covered in the [user guide](USAGE.md).

## Build and verify a package

Build on the target operating system.

```powershell
.venv/Scripts/python.exe scripts/build.py
.venv/Scripts/python.exe scripts/smoke_package.py dist/Brando/Brando.exe
```

| Target | Baseline and architecture | Packaged executable | Evidence |
| --- | --- | --- | --- |
| Windows | Windows 11 x86-64 | `dist/Brando/Brando.exe` | Local native UI, conversion checks and Windows CI |
| macOS | macOS 14+ arm64 and x86-64 | `dist/Brando.app/Contents/MacOS/Brando` | macOS 15 native CI for each architecture |
| Linux | Ubuntu 24.04 x86-64 | `dist/Brando/Brando` | Ubuntu 24.04 native CI |

CI runs synthetic tests, Ruff, a native build and relocated package checks on four native
targets. Interactive macOS/Linux acceptance is pending. Build results and rendering evidence
are recorded in [validation](VALIDATION.md).

The builder collects runtime resources, original dependency notices, a synthetic example,
version metadata and file hashes. Windows dependency discovery uses an isolated PATH and
workspace cache. The Windows package uses the system Microsoft Visual C++ runtime and omits
the optional Mesa OpenGL fallback. Linux system-library copies are removed and their Ubuntu
package names are recorded in `linux-system-dependencies.txt`. Corresponding library sources and replacement instructions
are maintained in [third-party notices](../THIRD_PARTY_NOTICES.md).

The package check relocates the app to a path with spaces and Unicode, restricts tool discovery
and checks both palettes, ZIP conversion, comments, equations, numeric values, a PDF figure
and bounded worker failures. Interactive acceptance also covers cancellation, retries,
reference styling and ordinary-user startup on another machine.

## Validate Word output

Use an installed Microsoft Word for the optional read-only rendering check. Supply a JSON
manifest with a `samples` array containing `name`, `docx` and `expected_text` fields.
Paths are resolved relative to the manifest. Choose a fresh output directory.

```powershell
powershell -NoProfile -File scripts/validate_word.ps1 -ManifestPath evaluation/word-manifest.json -OutputDirectory evaluation/word-new-run
```

The script records Word version, text checks, native object counts, input hashes and exported
PDFs. Inspect the relevant rendered pages and record the scope of review. Keep downloaded
projects and generated evidence under ignored `evaluation/`.

## Publish a release

- Run the native CI build and relocated package checks for every published target.
- Record desktop trials separately, including the documented prerequisites and OS versions.
- Review representative DOCX in Word for text, signed values, authors, equations, tables,
  figures, citations and comment placement. Record any remaining supported-case limits.
- Record the results and the owner's release decision, then choose a version/tag.
- Publish matching binaries, checksums, notices and corresponding dependency sources.
  Record the executable's signing status accurately.

Publication follows the repository owner's authorization. The CI workflow produces test
artifacts automatically. Release publication is performed explicitly.

## Technical references

- [Architecture](ARCHITECTURE.md) describes the conversion core, UI and resource boundaries.
- [Public-project evaluation](PUBLIC_CORPUS.md) records pinned inputs and observed limits.
- [Engine comparison](ENGINE_EVALUATION.md) records the initial converter selection.

To replay the original local benchmark, provide the ignored handoff bundle, install the
optional `evaluation` dependencies and run `scripts/benchmark.py` or `scripts/evaluate_app.py`.
Remote CI uses the original synthetic fixtures in this repository.
