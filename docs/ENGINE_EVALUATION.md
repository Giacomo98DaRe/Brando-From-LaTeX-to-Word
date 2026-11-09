# Engine evaluation - 2026-11-09

Host: Windows x86-64, CPython 3.12.16. Engines: Pandoc 3.9 via evaluation-only
pypandoc_binary 1.17; tex2word 1.2.0, source pin
`6c467479946643480f8e90b1078066b59d10d5b4`. Final comparison used pylatexenc 2.10.
Source and dependency license metadata were inspected, not just advertised features.

## Shared comparison

`scripts/benchmark.py` ran both engines on a controlled multi-file probe and five local
official/commit-pinned source roots supplied with the handoff. Upstream source files were
copied unchanged into temporary directories. For tex2word, the Springer main source was
decoded as cp1252 only after UTF-8 failed; this is an explicit benchmark adaptation, not an
upstream modification. TeX tool discovery was disabled. No project build script ran.

| Independent observation | Pandoc | tex2word |
| --- | --- | --- |
| Probe author and signed table number | Present | Present |
| Probe image, footnote and native equation | Present | Present |
| Elsevier abstract, section and caption phrases | All four present | All four present |
| CAS title fragment and four author names | All five present | All five present |
| IEEE: three expected author names | All absent | All present |
| Springer: three expected author names | All absent | All present |
| Thesis: two expected introduction phrases | Both absent | Both present |
| CAS PDF figure handling | PDF media part embedded | PNG rendition embedded |
| Springer EPS figure handling | EPS media part embedded | Not embedded; reported |

All 12 engine processes returned success; the content differences show why exit codes are
insufficient. Presence checks are deliberately narrow and do not establish full fidelity.
Table/math counts are recorded as observations. The shared comparison now checks actual
Elsevier abstract/section/caption text and CAS title/author text. The upstream Elsevier sample
has an empty title. Earlier exploratory checks for the literal word `Title` were discarded.

The original six legacy tests only establish behavior for their tailored Elsevier fixture.
The new implementation does not import legacy NAIARA path/logger helpers or reuse the old
unconditional Elsevier frontmatter adapter. No legacy source or CSL asset is copied into the app.

## Decision

Use tex2word 1.2.0 for the first slice: fewer adapters are needed for independently observed
author/chapter preservation, and its pure Python parsing/OMML/field pipeline can be bundled
without an external conversion executable. MIT terms and attribution were verified at the
pinned source. Optional rendering/subprocess paths are disabled in Brando's engine worker.
Pandoc remains a comparator, not a runtime dependency. A future regression can reopen this choice.

## Application ingestion checks

`scripts/evaluate_app.py` exercises the same five roots through Brando using both the original
archive and the project folder: 10 app conversions. Main documents are selected explicitly
from captured paths. Twenty independently specified text expectations cover the Elsevier
abstract/section/captions, CAS title/authors/highlight/caption, four IEEE authors, three Springer
authors and two thesis chapter phrases. All were present in relevant DOCX and in Word's text
model. Original upstream bytes were preserved.

Word rendering exposed two Springer commands that remained literal and missing review bullet
glyphs. Brando now maps Springer equal-contribution notes and bottom rules in temporary source
copies, protects literal examples and reports applied changes. Review bullet numbering uses
a Unicode text font. These adaptations are application behavior layered on the unchanged
tex2word package. The shared engine benchmark still evaluates direct engine behavior.

Missing CTAN example images/citations are fixture dependencies, not silently repaired converter
regressions. CAS custom macros, Springer EPS and the thesis's extensive custom packages remain
limitations. In particular, the thesis produced over 1,000 engine messages; retaining two
chapter phrases does not make it a supported thesis converter. All source families remain
experimental. Source comments and rendering need their own checks.

Raw JSON, stderr, DOCX and downloaded source are deliberately ignored under `evaluation/`
and `overleaf_word_handoff/`. They are not copied to the public tree or uploaded to CI.
To replay locally, provide the handoff bundle, install the optional `evaluation` dependency
group and run the two scripts. Public CI uses original synthetic examples only.

Primary sources: [tex2word source](https://github.com/yfyang86/tex2word/tree/6c467479946643480f8e90b1078066b59d10d5b4),
[Pandoc](https://pandoc.org/), upstream provenance/hashes in the local handoff's `downloads.json`.
