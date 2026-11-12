# Using Brando

## Install and open

Download the archive for your computer from the
[release page](https://github.com/digital-medicine-research-group-UNAV/Brando-From-LaTeX-to-Word/releases/tag/v0.1.0).
The app includes Python and the conversion engine. Extract the whole archive before opening it.

### Windows

Use the x86-64 ZIP and open `Brando/Brando.exe`. Keep `_internal` beside the executable.
Windows 11 is the tested desktop baseline. Successful trials on additional Windows PCs
have also been reported.

If Windows reports a missing Microsoft runtime DLL, install the official x64 runtime and
retry. The current executable is unsigned. If an organization policy blocks it, contact your
IT administrator. The prerequisite installer is available from
[Microsoft](https://aka.ms/vc14/vc_redist.x64.exe).

### macOS

Choose **arm64** for Apple Silicon (M-series chips) or **x86_64** for Intel. Find your chip
under **Apple menu > About This Mac**. Extract the ZIP and open `Brando.app`. The baseline
is macOS 14 or later, with automated native checks on macOS 15 for both architectures.

The app has no Developer ID signature or Apple notarization. If macOS blocks the first launch,
use **System Settings > Privacy & Security > Open Anyway** for this app after attempting to
open it. Follow [Apple's opening instructions](https://support.apple.com/en-us/102445).
The included example is inside `Brando.app/Contents/Resources/example-project`, accessible
through Finder's **Show Package Contents**.

### Linux

Use the x86-64 archive on **Ubuntu 24.04**. Extract it, then install the Ubuntu runtime
packages listed in the archive and launch the app from a terminal.

```sh
tar -xzf Brando-0.1.0-linux-x86_64.tar.gz
sudo apt update
sudo apt install $(cat Brando/linux-system-dependencies.txt)
./Brando/Brando
```

Keep the complete `Brando` directory together. Other distributions require compatible
system libraries and have separate compatibility requirements. macOS and Linux downloads
have passed native automated conversion checks. Interactive desktop feedback is welcome.

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

For Google Chat, send the release-page link so colleagues can choose their system, and pin
the message. Chat blocks executable
attachments, including those inside ZIPs. See [Google Chat attachment restrictions](https://support.google.com/chat/answer/7651457?hl=en).

Include the Brando version, operating system, Word version, expected behavior and actual behavior in
your report. A small original example helps reproduce a problem. Review conversion reports
for local paths and source text before posting. Submit feedback through
[GitHub issues](https://github.com/digital-medicine-research-group-UNAV/Brando-From-LaTeX-to-Word/issues).
