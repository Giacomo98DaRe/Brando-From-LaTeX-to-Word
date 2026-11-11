# Public project evaluation

Evaluated on Windows x86-64 on 2026-11-11 with Brando 0.1.0, tex2word 1.2.0 and PDFium 5.15.2.
Nine freshly downloaded public repositories provided ten manuscripts. Each document was
converted from a folder and ZIP with comments disabled, then from ZIP with comments enabled.
Archives were pinned to the revisions below. Upstream scripts and TeX compilers were never run.
Downloads, original inputs, generated documents and raw evidence remain in ignored local storage.

## Results

All 30 conversions completed. All independently selected title/author/body text checks and
the 18 row checks passed, including the negative value `-0.0018`, decimals and interval bounds
in the CS321M manuscript. The minimum structure checks passed in 27 conversions. Three runs
of the same thesis failed the expected PDF-figure check. These checks sample content and
structure. They do not establish complete semantic or visual fidelity.

| Project and selected root | Revision | Findings |
| --- | --- | --- |
| [arxiv-style](https://github.com/kourgeorge/arxiv-style), `template.tex` | `920514696f6e` | Selected text, table and native math retained; macro warnings require review. |
| [ANOR](https://github.com/iftaken/anor-template), `anor-article.tex` | `dfeb5372e921` | Title/authors, four tables and selected numerical row associations retained. |
| [Cyrraz thesis](https://github.com/cyrraz/thesis-template), `thesis.tex` | `aebbd6917c58` | Text/table/math retained; available PDF figure becomes a missing-figure placeholder. |
| [UCL thesis](https://github.com/UCL/ucl-latex-thesis-templates), `Main.tex` | `534cabd19beb` | Title, author and included chapter sentinels retained; unsupported class macros remain. |
| [Alcazar](https://github.com/dpmj/alcazar), `main.tex` | `f5c4eef41c4c` | Selected text, 20 tables and 19 image parts retained; many custom-macro warnings. |
| [PLOS](https://github.com/petarmaric/template4plos), `paper.tex` | `7236a2f8aa5d` | Included title/authors, table and three image parts retained; root must be chosen manually. |
| [CS321M](https://github.com/ankaggarwal94/cs321m-paper), `pap.tex` | `b0b9390a1758` | Protocol title/author, eight tables and native math retained. |
| Same CS321M project, `final_project.tex` | `b0b9390a1758` | Nine tables, four images and checked signed/decimal row values retained. |
| [ACL](https://github.com/acl-org/acl-style-files), `acl_latex.tex` | `d5adc823ff0f` | Selected text, three tables and native math retained; example images require external `mwe` resources. |
| [ICLR](https://github.com/ICLR/Master-Template), `iclr2026/iclr2026_conference.tex` | `46ed6f4c6cef` | Nested bibliography resolution corrected; selected reference titles now retained. Figure/formatting macros require review. |

The corpus includes templates and two populated manuscript roots from an Overleaf mirror.
It is deliberately varied rather than a statistical sample of all Overleaf projects. Source
SHA-256 hashes were checked before and after evaluation. Every captured source and archive
retained its original hash. Repository licenses were recorded locally, including unidentified
or mixed declarations. Third-party source files are excluded from the published repository.

## Corrections made from these observations

- Bibliographies beside an included or nested `.tex` file are qualified within the temporary
  captured project when root lookup would fail. Existing root files retain precedence. Literal
  examples are preserved, and the report records each changed path. Original source bytes persist.
- An independent graphics check now warns when static source references resolve to available
  captured graphics but the DOCX has no embedded images. It catches the Cyrraz conditional-wrapper
  case. Rendering that particular `IfFileExists` wrapper remains an engine limitation.
- Synthetic regressions cover local bibliography paths, source preservation, literal examples
  and loss of available graphics. The complete regression suite has 54 passing tests; Ruff passes.

Comments were inspected in DOCX structures and reports in both option states. Enabled exports
contain 1,602 source comments across the ten documents, with actual body/appendix placement
recorded. Many template notes belong to preambles or unused files and therefore use the final
Source annotations section. Disabled exports contain zero native comments.

## Rendering and colleague acceptance

Read-only Word automation stalled on the arxiv sample and a second ANOR attempt exceeded its
65-second limit. The owned automation instances were stopped and input DOCX hashes remained
unchanged. The cause is undetermined; Word rendering acceptance is inconclusive for this run.

Before relying on a colleague's document, open its Word export and inspect equation editing,
wide tables, figure placement, bibliography and comment anchors. Refresh Word fields for the
table of contents and references. Compare important results against the source project's PDF.
Complex macros, external TeX assets, custom drawing commands and complete layout fidelity remain
review points. Clean-machine and native macOS/Linux acceptance are tracked in [BUILDING.md](BUILDING.md).
