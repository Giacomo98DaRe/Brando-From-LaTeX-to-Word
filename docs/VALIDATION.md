# Validation record

Updated 2026-11-11. Development host is Windows x86-64, CPython 3.12.16.

## Completed evidence

- Full synthetic regression suite completed with 55 passing tests on the Windows host.
  It includes Qt offscreen scan, conversion, drop and ambiguous-root behavior, numerical
  tampering detection, nested-main paths, encoding adaptation and inline annotation opt-in.
  A simulated report-write failure also verifies cleanup without a partial export.
  Additional regressions cover Springer contribution notes/bottom rules, protected literal
  examples, adaptation reporting, source preservation and Unicode review-list fonts.
  Focus changes retain a manually selected main document; explicit reselection refreshes
  the captured project. GUI regressions cover comments on/off, adjacent option information,
  the underscore export directory and an unreadable optional comment preview.
  The maintained screenshot shows the current interface.
- Information controls were exercised with mouse hover, click and keyboard activation in both
  palettes. Help stays anchored while the pointer moves within the button; actual multiline
  rendering stays below 340 pixels wide. Eighteen rendered tips across both themes were
  measured. The Brando wordmark uses its capital B. Project selection uses ZIP/folder buttons
  or drop, with the chosen project name shown and no manual path input. The Source comments
  summary follows its switch, with native Word comment counts verified for both export states.
  The header names its appearance switch Dark mode.
  The footer status indicator follows idle, busy, ready and error transitions. Regressions in
  both modes verify actual green/red text colors and require a main document, destination and
  reference path when reference styling is selected before enabling conversion.
  The details panel is unavailable while empty and explains progress/warnings, the saved note
  and report filenames, and their distinction from Word comments. Compact error captures retain
  visible conversion actions.
- The light desktop has a large drop target and prominent source-comment switch.
  Dark mode changes colors in place. Keyboard theme activation preserves widget geometry,
  captured input and conversion choices, including during conversion. ZIP and folder drop
  events are delivered through Qt to the large target. Compact-window captures verify scrolling
  with conversion actions available. The approved crayon B icon is used by the window.
- The selected crayon B identity (concept 07) uses mint artwork on a rounded petrol tile
  in the header, drop target, window and Windows executable. Actual light/dark screenshots
  and icon renders at 16-256 pixels were inspected. All seven EXE icon payloads match the ICO
  exactly. All four production resources match their bundled copies. The full regression suite,
  Ruff checks and relocated package smoke passed after replacement.
- A hidden native Windows window verified `Brando.Desktop` application identity, a native icon
  handle and DWM title-bar color state for both palettes. The packaged UI check exercises the
  same theme switch and checks application/window icons before conversion tests.
- Five template families retain independently specified synthetic title, author, affiliation
  (where supplied), abstract, keywords and body expectations.
- Synthetic end-to-end checks exercise nested relative inputs, spaces/Unicode paths, original
  source hashes, signed/scientific table values, native equations, citation bibliography,
  footnotes, Word cross-reference fields, comment ranges, reference styles and prior exports.
- Import safeguards cover ZIP traversal, symbolic links, case collisions, size limits and
  independently compilable subfiles. Outside-project read attempts, cancellation and engine
  timeout are exercised. These are proportionate workflow checks, not an OS-sandbox proof.
- Shared engine comparison and real corpus folder/ZIP conversions completed; see
  [engine evaluation](ENGINE_EVALUATION.md). These tests do not certify complete content.
  The cleanup rerun passed all 40 expected-text checks across ten imports. Relocated package
  checks additionally verify rasterization of an original synthetic PDF figure to a PNG.
- Microsoft Word 16.0 build 16.0.14334 opened the synthetic example read-only and recognized
  two native equations, one table, one footnote and three comments. Checked author, included
  text and signed values were present. Word exported one PDF page. Visual inspection of its
  rasterized page found readable text, table values, scientific exponent, equation and footnote.
  This covers the synthetic example.

## Journal rendering follow-up

The optional Windows validation script opened all five current corpus DOCX files read-only
in Word 16.0 build 16.0.14334 and exported PDFs. All 20 selected text expectations passed,
and every DOCX retained its original hash after Word closed it.

| Sample | Word PDF pages | Word tables | Native equations | Inline images |
| --- | --- | --- | --- | --- |
| Elsevier elsarticle | 2 | 1 | 9 | 0 |
| Elsevier CAS | 7 | 1 | 4 | 2 |
| IEEEtran | 1 | 0 | 0 | 0 |
| Springer Nature | 11 | 5 | 44 | 0 |
| Scientific thesis | 35 | 10 | 14 | 1 |

The 56-page export was inspected through journal overview sheets and selected full-size
pages covering frontmatter, lists, tables, equations and the CAS photograph/caption. The
initial Springer export had 12 pages. After adapting equal-contribution notes and bottom
rules it has 11. The first table spans a page boundary and its data rows remain present.
Unicode bullets now render as bullets in the review layout. The Springer EPS figure still
requires separate preparation. CAS custom macros and extensive thesis constructs still
produce conversion notes. Complete page-by-page source equivalence and editing acceptance
remain outstanding.

## Packaging findings

The 2026-11-11 comment follow-up compares an explicitly supplied private manuscript locally.
The supplied Brando DOCX has zero comments. A separate same-project export with comments
enabled has 51 percent notes, previously all in an appendix. The original script's review
document has 34 comments and Track Changes enabled. These are distinct Word features.

Brando now places source notes beside uniquely matching nearby manuscript text. In a fresh
review export, 34 of the 51 notes match body paragraphs and 17 use the final Source annotations
section. Matching excludes unused source files and ambiguous repeated text. Regressions check
actual Word comment ranges for body text, headings and captions, plus explicit fallback cases.
Word 16.0 build 16.0.14334 recognized all 51 comments and two tables, and exported 12 PDF pages
with markup. Pages 1 and 3 were inspected for visible note balloons and paragraph anchors.
All original DOCX files and the new review export retained their recorded hashes.

The first Windows package conversion exposed an audit-hook interaction with PyInstaller lazy
imports. The hook now permits reads of the exact executable archive and workers persist
failures as diagnostic files. Packaged ZIP conversion subsequently passed with a restricted PATH.

The explicit packaged GUI startup check then exposed an incompatible ICU DLL that PyInstaller
collected from a host tool directory on PATH. Qt's files matched the installed wheel, but the
collected ICU exported version-suffixed symbols while Qt expected Windows ICU exports. The
builder now isolates its Windows PATH and performs a clean analysis with a workspace cache.
The corrected package passed relocated offscreen Qt startup, ZIP conversion with comments
off/on, independent number checks and a bounded worker-error diagnostic test. The child PATH
contained only Windows system tools. These checks used the existing development host.

The 2026-11-09 dependency check found pypdfium2 5.15.1 withdrawn for object cleanup during
interpreter exit. On 2026-11-11 the project updated the lock to 5.15.2, whose maintenance
release corrects shutdown and protects object trackers during traversal. The runtime license
inventory follows the new version. PDF rendering and packaged checks cover this correction.
[Upstream 5.15.2 release](https://github.com/pypdfium2-team/pypdfium2/releases/tag/5.15.2).

## Pending final checks

- Interactive packaged GUI acceptance on a clean Windows VM.
- Fresh Windows VM with no development tools installed.
- Full source equivalence and interactive editing acceptance for journal/complex documents.
- Separate LibreOffice compatibility check and version record.
- Native macOS and Ubuntu builds, GUI/clean-machine tests and distribution checks.
- Complete Qt bundled notices/corresponding-source provision before public binary distribution.

No platform is declared publicly supported. Build generation, DOCX structural integrity,
source-content observations, application portability and document rendering remain distinct.

## Public preview preparation

The fresh public-project evaluation completed 30 folder/ZIP conversions across ten documents.
All 177 selected text checks and 18 numeric-row checks pass. Minimum structure checks pass
in 27/30 runs: one thesis loses a conditional PDF figure in all three modes. A nested ICLR
bibliography path was fixed; complete absence of available project graphics is now warned.
See [the pinned source inventory and limits](PUBLIC_CORPUS.md). Fresh Word automation stalled,
so Word rendering acceptance for this new corpus is inconclusive. Earlier rendering evidence
above applies only to the earlier samples.

The README demo records actual Qt ZIP import, opt-in comments and conversion of the original
synthetic example, with three native comments independently verified. No private manuscript,
source archive, local history or development toolchain is included in the published source.
The public Windows preview uses system Microsoft runtime libraries; the optional Mesa
software-OpenGL fallback is excluded. Exact upstream Qt/PySide 6.10.1 source archives and
original notices accompany the preview release. Clean Windows-machine, LibreOffice and
interactive scaling checks remain separate acceptance tasks.

Native Linux/macOS CI exposed repeated source-note context within a single Word paragraph.
Comment placement now counts repeated occurrences inside each paragraph as ambiguous,
using Source annotations rather than attaching an arbitrary body comment. A direct Word
paragraph regression covers this case independently of engine paragraph splitting.

The [native CI run on preview code](https://github.com/Giacomo98DaRe/Brando-From-LaTeX-to-Word/actions/runs/43067502485)
passes all 55 synthetic tests, Ruff, native builds and relocated package smoke on Windows 2022,
macOS 15 arm64 and Ubuntu 24.04. The separately built Windows 11 preview also passes native
light/dark startup, seven matching executable icons, complete file-manifest verification and
10 restricted-PATH public-project conversions: 66 selected text and 12 numeric-row checks,
comments off/on, with the known Cyrraz figure loss correctly warned. Only the Windows preview
is distributed. These checks do not replace Word rendering or interactive clean-machine trials.
