# Builds and release gates

## Target matrix

| Target | Initial baseline | Architecture | Artifact | Status |
| --- | --- | --- | --- | --- |
| Windows | Windows 11 | x86-64 | portable directory / ZIP | unsigned preview; local package checks pass |
| macOS | macOS 14+ | arm64 | `.app` in ZIP, then signed/notarized distribution | native CI build/smoke passed; interactive acceptance pending |
| Linux | Ubuntu 24.04 LTS | x86-64 | portable directory in tar.gz | native CI build/smoke passed; interactive acceptance pending |

These are validation targets, not claims of support. Other OS versions/architectures are
unvalidated. Build on each native target; PyInstaller does not cross-compile the application.
Linux's glibc and system graphics dependencies prevent a universal-Linux-binary promise.

## Repeatable development build

Use pinned CPython 3.12.16 and uv 0.13.7. The lock fixes dependency artifacts, but builds are not
claimed byte-for-byte deterministic. Record the native build host and run tests first.

```powershell
uv sync --frozen --extra dev --python 3.12
.venv/Scripts/python.exe -m ruff check src tests scripts
.venv/Scripts/python.exe -m ruff format --check src tests scripts
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe scripts/build.py
.venv/Scripts/python.exe scripts/smoke_package.py dist/Brando/Brando.exe
```

Use `.venv/bin/python` and `dist/Brando/Brando` on Linux. macOS executable:
`dist/Brando.app/Contents/MacOS/Brando`. Build output includes runtime/engine resources,
synthetic example, original dependency notices, version inventory and file hashes. Keep the
entire directory/app together. No external Pandoc/TeX/Word executable is needed to convert.
On Windows install Microsoft Visual C++ x64 runtime if absent; standalone Microsoft runtime
DLLs are excluded from the archive. The optional Mesa software-OpenGL fallback is also excluded
because this Qt Widgets interface uses raster painting. Both palettes are smoke-tested after
these exclusions.

The smoke script relocates the bundle to a path with spaces and Unicode, checks offscreen Qt
startup, uses a restricted child PATH and clears Python/Conda environment variables.
This catches many accidental external-tool dependencies; it **does not replace a clean VM**
where development tools are absent. It invokes the packaged app's internal CLI using the
original synthetic example plus a generated PDF figure, then checks independent DOCX
text/math/table/comment/image expectations.
It also verifies that a worker error returns a diagnostic file within a bounded timeout.

On Windows the builder also isolates PATH to the project Python runtime and Windows system
directories. This prevents DLLs from unrelated development tools entering dependency analysis.
Engine resources are collected as data. PDFium uses the installed PyInstaller hooks for its
shared library and version data, with PDF rasterization exercised by the packaged smoke check.
Brando's selected crayon B artwork and desktop stylesheet are package data. Windows executable
resources use the same multi-resolution ICO as Qt. The macOS recipe uses its PNG input.
The RGBA PNG master shows the selected crayon B (concept 07) in mint on a rounded petrol tile,
with transparent outer corners. The ICO contains
16, 24, 32, 48, 64, 128 and 256 pixel variants. The same mark appears in the header and drop
target. Local design sheets and extraction prompts are excluded from source and builds.
The relocated UI check switches both color palettes and verifies their shared layout and icons.
PyInstaller uses a clean analysis and a workspace-local cache on every build.

## Before declaring a Windows release usable

1. Extract the ZIP on a fresh Windows 11 x86-64 VM with no Python/Git/Pandoc/TeX installation.
2. Run the GUI as an ordinary user from a path with spaces and Unicode. Use ZIP and folder
   import, ambiguous-root selection, reference styling and source comments off/on.
3. Cancel conversion and retry; verify clear errors for malformed ZIP/missing assets and
   preserve original files/earlier outputs.
4. Open representative DOCX files in Microsoft Word; check authors, affiliations, nested
   chapters, signed/scientific tables, editable equations, footnotes, bibliography, field
   updates, image rendering and comment anchors.
5. Check LibreOffice separately and document its version and any rendering differences.
6. Verify notices and matching dependency source archives accompany the release. Record
   signing, antivirus and download-origin checks separately; this preview remains unsigned.

## Other platforms and publication

macOS needs native GUI/clean-machine tests and assessment of Developer ID signing, hardened
runtime, notarization and Gatekeeper behavior before broad distribution. The unsigned ZIP
recipe is only a development artifact. Linux needs native GUI tests on the declared Ubuntu
baseline and explicit review of remaining shared-library dependencies.

The GitHub workflow uses only synthetic fixtures. It builds reviewable artifacts on native
runners, with no automatic release or tag/push operation. Native Windows/macOS/Linux tests, builds and relocated package smoke passed on
[the preview code](https://github.com/Giacomo98DaRe/Brando-From-LaTeX-to-Word/actions/runs/43067502485).
These headless checks do not establish interactive platform support. Versioned release publication requires explicit user request,
validated packages, SHA-256 files, corresponding source/notices, and documented limitations.
The presence of prepared release files does not authorize publication.

## Optional Word validation on Windows

`scripts/validate_word.ps1` uses an installed Word instance for development acceptance only.
Supply a JSON manifest with a `samples` array. Each sample has `name`, a `docx` path resolved
relative to the manifest, and an `expected_text` array. Choose a fresh output directory.

```powershell
powershell -NoProfile -File scripts/validate_word.ps1 -ManifestPath evaluation/word-manifest.json -OutputDirectory evaluation/word-new-run
```

The script records Word version, expected-text presence, native object counts, input hashes
and exported PDFs. It opens documents read-only, closes its own documents/instance and
returns failure for a missing expectation, a changed input hash or an opening/export error.
Keep corpus manifests, DOCX, PDFs and reports under ignored `evaluation/`. Inspect relevant
rendered pages separately and record the scope of that visual review.

## Developer CLI

```powershell
.venv/Scripts/python.exe -m brando.cli examples/article --destination outputs
.venv/Scripts/python.exe -m brando.cli project.zip --main main.tex --destination outputs --comments
```

Main-document discovery is heuristic. Use `--main` for nested roots or a main file whose
class declaration is in an included preamble. A reference DOCX controls Word styles and
page geometry, independently of source-template recognition. See `--help` for options.
