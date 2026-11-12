# Using Brando

## Install and open

Download `Brando-0.1.0-win32-AMD64.zip`, extract the whole archive to a writable local folder
and open `Brando/Brando.exe`. Keep `_internal` beside the executable. The app includes its
Python runtime and conversion engine. Downloads are available on the
[Windows release page](https://github.com/Giacomo98DaRe/Brando-From-LaTeX-to-Word/releases/tag/v0.1.0-preview.1).

If Windows reports a missing Microsoft runtime DLL, install the official x64 runtime and
retry. The current executable is unsigned. If an organization policy blocks it, contact your
IT administrator. The prerequisite installer is available from
[Microsoft](https://aka.ms/vc14/vc_redist.x64.exe).

## Choose conversion options

- Drop the Overleaf **source ZIP** or complete project folder. Select the main `.tex` file
  if several documents are found. Convert independent supplements separately.
- Leave **Source template** on Auto or select the intended family.
- Use **Readable review** or choose a **Reference DOCX** for Word styles and page geometry.
- Enable **Source comments** to export source notes as native Word comments.
- Choose the destination and select **Convert to Word**. The default is `Documents/Brando_exports`.

The information buttons beside each option provide short explanations. Select the project
again after editing its source files to refresh the captured input.

## Find your files and comments

Each conversion creates a timestamped folder containing `manuscript.docx`, readable
`conversion-notes.txt` and detailed `conversion-report.json`. **Open Word file** and
**Open folder** take you to the result. **Conversion details** shows progress and warnings.

Source notes attach beside uniquely matching manuscript text. Unmatched notes, including
notes from unused files, appear in a final **Source annotations** section. The report lists
their actual placement. Overleaf Review-panel discussions require a separate data source.
Word edits are independent of the LaTeX source.

## Review the result

Compare important text, authors, numerical values, equations, tables, references and figures
against the source or its PDF. Refresh Word fields for the table of contents and references.

| Issue | What to check |
| --- | --- |
| Missing image or citation | Include the required graphics and bibliography inside the project. External TeX example assets may need preparation. |
| Custom macros or conditional figures | Read the warnings and inspect the output. A known conditional image wrapper can omit an available figure. |
| EPS figure | Prepare a supported image format. PDF figures may be rasterized to PNG. |
| Ambiguous main file | Select the manuscript root explicitly. |
| Layout differs from the PDF | A reference DOCX controls Word styling. Complex LaTeX layouts need review. |

All source-template families currently have experimental support. Compatibility evidence
and remaining checks are recorded in [validation](VALIDATION.md).

## Share and report a problem

For Google Chat, send the Windows download link and pin the message. Chat blocks executable
attachments, including those inside ZIPs. See [Google Chat attachment restrictions](https://support.google.com/chat/answer/7651457?hl=en).

Include the Brando version, Windows/Word versions, expected behavior and actual behavior in
your report. A small original example helps reproduce a problem. Review conversion reports
for local paths and source text before posting. Submit feedback through
[GitHub issues](https://github.com/Giacomo98DaRe/Brando-From-LaTeX-to-Word/issues).
