# Third-party notices and distribution status

Brando's original code and synthetic examples use the MIT license in `LICENSE`. This does
not replace any dependency license. No code or CSL file was copied from the legacy exporter.

## Runtime inventory

Versions below were inspected in the Windows development environment. `uv.lock` records
resolved artifacts and hashes. A build exports exact installed versions and license metadata
to `third-party-notices/versions.json`, and copies available original notices without editing.

| Component | Inspected version | License / notice |
| --- | --- | --- |
| CPython | 3.12.16 | PSF license and bundled dependency notices |
| tex2word | 1.2.0 | MIT, copyright 2026 Yifan Yang |
| PySide6 Essentials / Shiboken6 | 6.10.1 | LGPL-3.0-only option; Qt's own third-party terms also apply |
| python-docx | 1.2.0 | MIT |
| pylatexenc | 2.10 | MIT |
| lxml | 6.1.3 | BSD-3-Clause and bundled libxml2/libxslt notices |
| Pillow | 13.0.0 | MIT-CMU and bundled image-library notices |
| pypdfium2 / PDFium | 5.15.1 | Apache-2.0 / BSD-3-Clause and PDFium dependency notices |
| latex2mathml | 3.81.1 | MIT; wheel and source archive omit a license file, supplemented from upstream |
| typing_extensions | 4.16.0 | PSF-2.0 |
| Microsoft Visual C++ runtime on Windows | 14.44.35211.0 | Microsoft redistributable terms require final distribution review |

PyInstaller 6.17.0 is a build tool with a GPL exception for generated bundles. Pandoc 3.9
and pypandoc_binary 1.17 are local evaluation tools only, excluded from the application.
Ruff 0.17.4 is an MIT-licensed development formatter/linter, excluded from the application.
No third-party CSL style or sample manuscript is bundled; engine-provided styles retain
the engine's original notices. The example project is original synthetic material.

## Qt / LGPL distribution approach

The desktop uses Qt Core, Gui and Widgets via unmodified PySide6. The directory bundle keeps
shared libraries separate and replaceable. Brando imposes no restriction on reverse
engineering for debugging modified LGPL libraries. Replacement instructions and source
provision must accompany a public distribution. Keep the matching version/ABI when replacing
libraries; do so in a copy of the portable directory.

Supplemental LGPLv3 and GPLv3 texts are included under `resources/licenses/`. They supplement
the wheel's incomplete license-text payload; they do not convert Qt to an MIT dependency.
Before public binary distribution, complete a module-by-module Qt bundled-dependency notice
audit and supply the applicable corresponding source/source offer for the exact Qt, PySide6
and Shiboken build. Source URLs alone are not treated here as completed compliance.

**The current bundle is a local development artifact, not cleared for public distribution.**
The prepared automation builds reviewable artifacts; it does not publish a release or certify
license compliance, signing, notarization, platform support or document fidelity.

Primary references:

- [tex2word pinned license](https://github.com/yfyang86/tex2word/blob/6c467479946643480f8e90b1078066b59d10d5b4/LICENSE)
- [Qt for Python 6.10 notices](https://doc.qt.io/qtforpython-6.10/licenses.html)
- [Qt licensing](https://doc.qt.io/qt-6/licensing.html)
- [PyInstaller 6.17 license exception](https://pyinstaller.org/en/v6.17.0/license.html)
- [pypdfium2 licensing](https://pypdfium2.readthedocs.io/en/stable/readme.html#licensing)

Retrieved supplemental text URLs and hashes are recorded in `resources/licenses/SOURCES.json`.
