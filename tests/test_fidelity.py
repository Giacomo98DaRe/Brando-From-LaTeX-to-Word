from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from brando.core import convert
from brando.fidelity import numbers, observe
from brando.project import capture

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/article"


def test_signed_decimal_and_scientific_tokens_are_atomic():
    assert numbers(r"-0.25 & +0.125 & $-2.50\times 10^{-3}$") == ["-0.25", "+0.125", "-2.50×10-3"]
    assert numbers("\u22120.25 | +0.125 | \u22122.50×10\u22123") == [
        "-0.25",
        "+0.125",
        "-2.50×10-3",
    ]


def test_independent_table_check_detects_changed_sign_and_exponent(tmp_path):
    result = convert(EXAMPLE, tmp_path)
    report = observe(capture(EXAMPLE), "main.tex", result)
    assert len(report["numeric_tables"]) == 1
    assert report["numeric_tables"][0]["numbers"] == ["-0.25", "+0.125", "-2.50×10-3"]
    assert report["missing_numeric_tables"] == []
    with ZipFile(result) as z:
        parts = {name: z.read(name) for name in z.namelist()}
    parts["word/document.xml"] = parts["word/document.xml"].replace(b"-0.25", b"0.25")
    changed = tmp_path / "tampered.docx"
    with ZipFile(changed, "w", ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    assert observe(capture(EXAMPLE), "main.tex", changed)["missing_numeric_tables"] == [1]


def test_numeric_only_cells_stay_separate(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.tex").write_text(
        r"\documentclass{article}\begin{document}"
        r"\begin{tabular}{rr}1 & 2 \\ 3 & 4 \\\end{tabular}\end{document}"
    )
    result = convert(source, tmp_path / "out")
    assert observe(capture(source), "main.tex", result)["missing_numeric_tables"] == []
