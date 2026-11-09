# Validation record

Date: 2026-11-09. Development host: Windows x86-64, CPython 3.12.16.

## Completed evidence

- Full synthetic regression suite completed with 38 passing tests on the Windows host.
  It includes Qt offscreen scan, conversion, drop and ambiguous-root behavior, numerical
  tampering detection, nested-main paths, encoding adaptation and inline annotation opt-in.
  A simulated report-write failure also verifies cleanup without a partial export.
  Additional regressions cover Springer contribution notes/bottom rules, protected literal
  examples, adaptation reporting, source preservation and Unicode review-list fonts.
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

## Pending final checks

- Interactive packaged GUI acceptance on a clean Windows VM.
- Fresh Windows VM with no development tools installed.
- Full source equivalence and interactive editing acceptance for journal/complex documents.
- Separate LibreOffice compatibility check and version record.
- Native macOS and Ubuntu builds, GUI/clean-machine tests and distribution checks.
- Complete Qt bundled notices/corresponding-source provision before public binary distribution.

No platform is declared publicly supported. Build generation, DOCX structural integrity,
source-content observations, application portability and document rendering remain distinct.
