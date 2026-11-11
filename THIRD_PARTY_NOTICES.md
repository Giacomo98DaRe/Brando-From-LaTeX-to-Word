# Third-party notices

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
| pypdfium2 / PDFium | 5.15.2 | Apache-2.0 / BSD-3-Clause and PDFium dependency notices |
| latex2mathml | 3.81.1 | MIT; wheel and source archive omit a license file, supplemented from upstream |
| typing_extensions | 4.16.0 | PSF-2.0 |
| Microsoft Visual C++ runtime on Windows | System prerequisite | Install from Microsoft if absent; loose runtime DLLs are excluded from the ZIP |

PyInstaller 6.17.0 is a build tool with a GPL exception for generated bundles. Pandoc 3.9
and pypandoc_binary 1.17 are local evaluation tools only, excluded from the application.
Ruff 0.17.4 is an MIT-licensed development formatter/linter, excluded from the application.
No third-party CSL style or sample manuscript is bundled; engine-provided styles retain
the engine's original notices. The example project is original synthetic material.

## Qt / LGPL distribution

Brando uses unmodified Qt 6.10.1 Core, Gui, Network, Widgets and Svg through PySide6 Essentials
and Shiboken6 6.10.1 under the LGPLv3 option. `resources/licenses/` contains the LGPLv3/GPLv3
texts and original upstream attribution/license notices for these modules, including their
optional bundled dependencies. A conservative notice inventory does not imply every optional
component is linked. The Windows app does not ship the optional Mesa `opengl32sw.dll`.

The preview release provides the complete upstream `qtbase`, `qtsvg` and `pyside-setup`
6.10.1 source archives alongside the application, with hashes and upstream URLs in
[`resources/licenses/QT_SOURCES.json`](resources/licenses/QT_SOURCES.json).
Download them from the [same release](https://github.com/Giacomo98DaRe/Brando-From-LaTeX-to-Word/releases/tag/v0.1.0-preview.1).
These are source downloads for rebuilding the LGPL libraries; users do not need them to run Brando.
Brando's matching source and build instructions are in this repository and the tagged release.
No Qt/PySide library source modifications are made by Brando.

The directory bundle keeps shared libraries separate and replaceable. Brando imposes no
restriction on reverse engineering for debugging modified LGPL libraries. To replace them,
work in a copy of the extracted app: replace the matching files under `_internal/PySide6/`
and `_internal/shiboken6/` with compatible shared libraries/bindings for the same Python ABI,
architecture and Qt version, retaining their licenses. Alternatively build Brando from source
with your rebuilt PySide6 environment using `scripts/build.py`. No signature or online check
prevents replacement. Test the modified app before using its exports.

## Windows runtime

The public Windows ZIP excludes standalone Microsoft `MSVCP140*.dll` and `VCRUNTIME140*.dll`.
Install the [official x64 Visual C++ runtime](https://aka.ms/vc14/vc_redist.x64.exe) if it is
not already present. Brando does not run that installer or alter the system automatically.
The original Python license includes the conditions for Microsoft code embedded in the
Python binaries; keep that notice when redistributing the app. This is separate from the
licenses for Brando and its open-source dependencies.

The package includes original dependency notices under `third-party-notices/` and a version
inventory. Keep these with any redistributed copy. The preview is unsigned; packaging checks
are not a certification of document fidelity or clean-machine compatibility.

Primary references:

- [tex2word pinned license](https://github.com/yfyang86/tex2word/blob/6c467479946643480f8e90b1078066b59d10d5b4/LICENSE)
- [Qt for Python 6.10 notices](https://doc.qt.io/qtforpython-6.10/licenses.html)
- [Qt licensing](https://doc.qt.io/qt-6/licensing.html)
- [PyInstaller 6.17 license exception](https://pyinstaller.org/en/v6.17.0/license.html)
- [pypdfium2 licensing](https://pypdfium2.readthedocs.io/en/stable/readme.html#licensing)

Retrieved supplemental text URLs and hashes are recorded in `resources/licenses/SOURCES.json`.
