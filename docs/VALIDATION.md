# Validation

Evidence collected on 2026-11-11 and 2026-11-12.

## Automated checks

| Check | Result and scope |
| --- | --- |
| Synthetic regression suite | 55 passing tests on Windows, macOS and Linux CI |
| Python quality | Pinned Ruff check and format checks pass |
| Native build and relocated package checks | Pass on Windows 2022, macOS 15 arm64/Intel and Ubuntu 24.04 |
| Linux graphical platform | Packaged XCB startup and both palettes pass under Xvfb |
| Local Windows UI | Native light/dark startup, title-bar behavior and compact-window captures checked |
| Package integrity | File manifests, original notices, executable architecture and archive checksums checked for release packages |
| Additional Windows PCs | Owner reports successful trials on 2026-11-12; OS versions and detailed trial logs were not supplied |

Packages use CPython 3.12.16. Native build results are available in
[GitHub Actions](https://github.com/Giacomo98DaRe/Brando-From-LaTeX-to-Word/actions).
The repository owner authorized the public v0.1.0 release after the Windows trials,
with macOS/Linux desktop trials to follow publication.

The suite covers bounded ZIP ingestion, path traversal, links/collisions, source preservation,
nested inputs and bibliographies, encoding adaptation, cancellation/timeouts, atomic export,
signed/scientific table values, native math, citations, references and comment opt-in.
Qt checks cover import, option state, tooltip wrapping, readiness colors and shared theme layout.
Repeated comment context within one Word paragraph is treated as ambiguous.

Relocated package checks clear Python/Conda variables and restrict PATH. They verify a synthetic
PDF figure through actual raster pixels, comments off/on and bounded worker-error diagnostics.

## Public projects

The source inventory and individual findings are recorded in the
[public-project evaluation](PUBLIC_CORPUS.md).

| Run | Observations |
| --- | --- |
| 30 folder/ZIP conversions across ten documents | 177 selected text and 18 numeric-row checks pass |
| Minimum structure checks | 27/30 pass, with the same conditional thesis figure absent in three runs |
| Source comments | 1,602 native comments across enabled exports, zero in disabled exports |
| Ten Windows executable conversions across five projects | 66 selected text and 12 numeric-row checks pass, actual comments off/on verified |

Nested ICLR bibliography resolution was corrected. The known conditional thesis figure loss
is warned when available project graphics are entirely absent from Word. Original source and
archive hashes were preserved. These checks sample content and structure. Full fidelity still
requires document review.

## Word rendering

Earlier checks used Microsoft Word 16.0 build 16.0.14334 with read-only documents. The original
synthetic example exported one PDF page containing two native equations, a table, a footnote
and three comments. Its author, included text and signed values were checked visually.

Five earlier corpus samples exported 56 PDF pages. All 20 selected text expectations passed,
and original DOCX hashes persisted. Overview sheets and selected full-size pages were inspected.

| Sample | PDF pages | Tables | Native equations | Inline images |
| --- | --- | --- | --- | --- |
| Elsevier elsarticle | 2 | 1 | 9 | 0 |
| Elsevier CAS | 7 | 1 | 4 | 2 |
| IEEEtran | 1 | 0 | 0 | 0 |
| Springer Nature | 11 | 5 | 44 | 0 |
| Scientific thesis | 35 | 10 | 14 | 1 |

A separate local manuscript review exported 51 native comments, with 34 beside matching body
text and 17 in Source annotations. Word recognized all comments and two tables and exported
12 PDF pages with markup. Pages 1 and 3 were inspected for visible balloons and anchors.

For the fresh public corpus, Word automation stalled on the arxiv sample and a bounded ANOR
attempt timed out. Those documents retain their original hashes. Rendering acceptance for
that corpus is inconclusive.

## Known limits and remaining acceptance

- Custom macros, complex class semantics and layouts require review. The conditional thesis
  PDF figure and Springer EPS figure need separate preparation.
- Compare representative exports with source/PDF and test editing in Word, including equations,
  signed values, tables, references, figures and comment anchors.
- Record LibreOffice rendering separately, with its version.
- Exercise native macOS/Linux desktops and display scaling using the public downloads.

The Windows executable is unsigned. The macOS app has no Developer ID signature or
Apple notarization. Dependency notices and exact Qt/PySide corresponding
sources accompany the release. Runtime versions, source delivery and replacement instructions
are maintained in [third-party notices](../THIRD_PARTY_NOTICES.md). Build and acceptance commands
are in [development](BUILDING.md).
