import json
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from brando.adapters import adapt_source
from brando.core import W, convert, inspect_docx


def test_springer_adapter_preserves_literal_examples_and_other_families():
    source = (
        r"\botrule\equalcont{Equal \textbf{contribution}.}"
        "\n"
        r"\verb|\botrule|"
        "\n"
        r"\begin{verbatim}\equalcont{Example}\botrule\end{verbatim}"
        "\n"
        r"% \botrule should remain a source comment"
        "\n"
    )
    adapted, changes = adapt_source(source, "sn-jnl")
    assert changes == {"springer_bottom_rule": 1, "springer_equal_contribution": 1}
    assert r"\bottomrule\par\emph{Equal \textbf{contribution}.}" in adapted
    assert r"\verb|\botrule|" in adapted
    assert r"\begin{verbatim}\equalcont{Example}\botrule\end{verbatim}" in adapted
    assert adapt_source(source, "article") == (source, {})


def test_springer_notes_and_rules_are_readable_and_reported(tmp_path):
    folder = tmp_path / "source"
    folder.mkdir()
    main = (
        r"\documentclass{sn-jnl}\begin{document}\title{Test}\author{Alice Example}"
        r"\equalcont{Equal \textbf{contribution}.}\maketitle\input{table}\end{document}"
    )
    table = r"\begin{tabular}{lr}Negative & -0.25 \\ Positive & +0.125 \\ \botrule\end{tabular}"
    (folder / "main.tex").write_text(main)
    (folder / "table.tex").write_text(table)
    result = convert(folder, tmp_path / "out")
    text = inspect_docx(result)["text"]
    assert "Equal contribution." in text
    assert r"\equalcont" not in text
    assert r"\botrule" not in text
    assert "-0.25" in text and "+0.125" in text
    report = json.loads((result.parent / "conversion-report.json").read_text())
    assert len(report["template_adaptations"]) == 2
    assert report["independent_source_observations"]["numeric_tables"][0]["present_in_output_table"]
    assert (folder / "main.tex").read_text() == main
    assert (folder / "table.tex").read_text() == table


def test_review_bullets_use_a_unicode_font(tmp_path):
    folder = tmp_path / "source"
    folder.mkdir()
    (folder / "main.tex").write_text(
        r"\documentclass{article}\begin{document}\begin{itemize}\item First bullet"
        r"\begin{itemize}\item Nested bullet\end{itemize}\end{itemize}\end{document}"
    )
    result = convert(folder, tmp_path / "out")
    with ZipFile(result) as archive:
        numbering = ET.fromstring(archive.read("word/numbering.xml"))
    bullet_levels = [
        level
        for level in numbering.iter(f"{{{W}}}lvl")
        if level.find(f"{{{W}}}numFmt").get(f"{{{W}}}val") == "bullet"
    ]
    assert bullet_levels
    for level in bullet_levels:
        assert level.find(f"{{{W}}}rPr/{{{W}}}rFonts").get(f"{{{W}}}ascii") == "Calibri"
