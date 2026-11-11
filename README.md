# Brando

Convert an Overleaf source ZIP or LaTeX project folder into an editable Word document.
Conversion runs on your computer. No account, upload, Word, Python or TeX installation
is needed with the Windows app.

**[Download the Windows preview](https://github.com/Giacomo98DaRe/Brando-From-LaTeX-to-Word/releases/tag/v0.1.0-preview.1)** |
[Validation and known gaps](docs/PUBLIC_CORPUS.md)

![Brando: drop a project, include source comments and convert to Word](docs/images/demo.gif)

1. Extract the entire Windows ZIP and open `Brando.exe` inside the `Brando` folder.
2. Drop your Overleaf **source ZIP** or project folder. Select the main `.tex` document.
3. Enable **Source comments** if wanted, choose the destination and select **Convert to Word**.

Each conversion creates a new folder with `manuscript.docx`, readable `conversion-notes.txt`
and a detailed `conversion-report.json`. The default destination is `Documents/Brando_exports`.
Inputs and earlier exports stay unchanged. Try the included `example-project` first.

Source notes become native Word comments beside matching text; unmatched notes use a final
**Source annotations** section. Overleaf Review discussions are separate. Word edits do not
synchronize back to LaTeX. A reference DOCX supplies Word styles and page geometry.

This is an **unsigned Windows x86-64 preview**, tested on Windows 11. Review the resulting
text, equations, tables, figures and citations before sharing: custom macros and layouts can
lose content. All template families remain experimental. See the [test evidence](docs/VALIDATION.md)
and [public-project evaluation](docs/PUBLIC_CORPUS.md). Clean-machine acceptance is still pending;
macOS and Linux downloads are not offered yet.

For development, use a separate Python 3.12 environment:

```powershell
uv sync --frozen --extra dev
.venv/Scripts/python.exe -m pytest
.venv/Scripts/pythonw.exe -m brando
```

[Build and CLI instructions](docs/BUILDING.md) | [Architecture](docs/ARCHITECTURE.md) ?
[Sharing and feedback](docs/SHARING.md)

Brando's original code is [MIT licensed](LICENSE). The app uses Qt under LGPLv3 and other
dependencies under their own licenses; see [notices and corresponding sources](THIRD_PARTY_NOTICES.md).
