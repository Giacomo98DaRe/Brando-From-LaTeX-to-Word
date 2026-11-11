import json
import shutil
import threading
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pytest

from brando.core import Options, W, convert, inspect_docx
from brando.project import Cancelled, ConversionError

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/article"


def project(tmp_path, source):
    folder = tmp_path / "source"
    folder.mkdir(exist_ok=True)
    (folder / "main.tex").write_text(source, encoding="utf-8")
    return folder


def test_example_preserves_content_numbers_math_citation_and_inputs(tmp_path):
    source = tmp_path / "project with spaces é"
    shutil.copytree(EXAMPLE, source)
    before = {
        p.relative_to(source): sha256(p.read_bytes()).hexdigest()
        for p in source.rglob("*")
        if p.is_file()
    }
    result = convert(source, tmp_path / "outputs")
    facts = inspect_docx(result)
    text = facts["text"].replace("\u2212", "-")
    for expected in (
        "Avery Example",
        "This included section must survive conversion",
        "Nested file content",
        "café",
        "-0.25",
        "+0.125",
        "-2.50",
        "-3",
        "A fictional reference",
    ):
        assert expected in text, (expected, text)
    assert facts["tables"] == 1
    assert facts["native_equations"] >= 2
    assert not facts["native_comments"]
    with ZipFile(result) as z:
        assert b"An editable synthetic footnote" in z.read("word/footnotes.xml")
        root = ET.fromstring(z.read("word/document.xml"))
        assert any("REF " in (e.text or "") for e in root.iter(f"{{{W}}}instrText"))
    assert before == {
        p.relative_to(source): sha256(p.read_bytes()).hexdigest()
        for p in source.rglob("*")
        if p.is_file()
    }
    report = json.loads((result.parent / "conversion-report.json").read_text())
    assert report["source_comments_enabled"] is False
    assert report["source_template"] == "Standard article"


def test_source_comments_use_manuscript_text_and_unmatched_appendix(tmp_path):
    result = convert(EXAMPLE, tmp_path, Options(comments=True))
    with ZipFile(result) as z:
        comments = ET.fromstring(z.read("word/comments.xml"))
        doc = ET.fromstring(z.read("word/document.xml"))
        assert len(comments.findall(f"{{{W}}}comment")) == 3
        assert len(list(doc.iter(f"{{{W}}}commentRangeStart"))) == 3
        assert "Check this sentence" in "".join(comments.itertext())
        comment = next(c for c in comments if "Check this sentence" in "".join(c.itertext()))
        comment_id = comment.get(f"{{{W}}}id")
        paragraph = next(
            p
            for p in doc.iter(f"{{{W}}}p")
            if any(e.get(f"{{{W}}}id") == comment_id for e in p.iter(f"{{{W}}}commentRangeStart"))
        )
        assert "This included section must survive conversion." in "".join(paragraph.itertext())
    assert "Source annotations" in inspect_docx(result)["text"]
    report = json.loads((result.parent / "conversion-report.json").read_text())
    assert report["body_source_comments"] >= 1
    assert report["appendix_source_comments"] >= 1
    assert report["body_source_comments"] + report["appendix_source_comments"] == 3


def test_ambiguous_and_unused_source_notes_never_attach_to_matching_body(tmp_path):
    repeated = "Repeated context appears identically in two manuscript paragraphs."
    unique = "A uniquely identifiable manuscript sentence has its own source annotation."
    source = project(
        tmp_path,
        "\\documentclass{article}\\begin{document}\n"
        + unique
        + " % Unique body note\n\n"
        + repeated
        + " % Ambiguous repeated note\n\n"
        + repeated
        + "\n\\end{document}",
    )
    (source / "unused.tex").write_text(unique + " % Unused source note")
    (source / "refs.bib").write_text("% Bibliography source note")
    result = convert(source, tmp_path / "out", Options(comments=True))
    report = json.loads((result.parent / "conversion-report.json").read_text())
    assert report["source_comments_exported"] == 4
    assert report["body_source_comments"] == 1
    assert report["appendix_source_comments"] == 3
    anchors = report["source_comment_anchors"]
    assert next(a for a in anchors if a["file"] == "unused.tex")["anchor"] == "appendix"
    assert next(a for a in anchors if a["file"] == "refs.bib")["anchor"] == "appendix"


def test_source_notes_before_heading_and_caption_use_their_word_paragraphs(tmp_path):
    source = project(
        tmp_path,
        "\\documentclass{article}\\begin{document}\n"
        "% Heading review\n\\section{Distinct methods section}\nBody sentinel.\n\n"
        "% Caption review\n\\begin{table}\n"
        "\\caption{An original synthetic caption with an identifiable review target}\n"
        "\\begin{tabular}{ll}Measure & Value\\\\\\end{tabular}\n"
        "\\end{table}\\end{document}",
    )
    result = convert(source, tmp_path / "out", Options(comments=True))
    with ZipFile(result) as archive:
        document = ET.fromstring(archive.read("word/document.xml"))
        comments = ET.fromstring(archive.read("word/comments.xml"))
        for note, expected in (
            ("Heading review", "Distinct methods section"),
            ("Caption review", "An original synthetic caption"),
        ):
            comment_id = next(
                c.get(f"{{{W}}}id") for c in comments if note in "".join(c.itertext())
            )
            paragraph = next(
                p
                for p in document.iter(f"{{{W}}}p")
                if any(
                    e.get(f"{{{W}}}id") == comment_id for e in p.iter(f"{{{W}}}commentRangeStart")
                )
            )
            assert expected in "".join(paragraph.itertext())


def test_ambiguous_main_requires_selection_and_supplement_is_separate(tmp_path):
    source = project(tmp_path, r"\documentclass{article}\begin{document}Main only\end{document}")
    (source / "supplement.tex").write_text(
        r"\documentclass{article}\begin{document}Supplement only\end{document}"
    )
    with pytest.raises(ConversionError, match="Select a main"):
        convert(source, tmp_path / "out")
    path = convert(source, tmp_path / "out", Options(main="main.tex"))
    assert "Supplement only" not in inspect_docx(path)["text"]


@pytest.mark.parametrize(
    ("cls", "front"),
    [
        (
            "article",
            r"\title{Synthetic title}\author{Alice Example}\maketitle"
            r"\begin{abstract}Synthetic abstract\end{abstract}",
        ),
        (
            "elsarticle",
            r"\begin{frontmatter}\title{Synthetic title}\author[a]{Alice Example}"
            r"\affiliation[a]{organization={Synthetic Institute},city={Town}}"
            r"\begin{abstract}Synthetic abstract\end{abstract}"
            r"\begin{keyword}Alpha\sep Beta\end{keyword}\end{frontmatter}",
        ),
        (
            "cas-sc",
            r"\title{Synthetic title}\author[1]{Alice Example}"
            r"\affiliation[1]{organization={Synthetic Institute},city={Town}}"
            r"\begin{abstract}Synthetic abstract\end{abstract}"
            r"\begin{keywords}Alpha\sep Beta\end{keywords}\maketitle",
        ),
        (
            "sn-jnl",
            r"\title{Synthetic title}\author*[1]{\fnm{Alice} \sur{Example}}"
            r"\affil*[1]{\orgname{Synthetic Institute}}\abstract{Synthetic abstract}"
            r"\keywords{Alpha,Beta}\maketitle",
        ),
        (
            "IEEEtran",
            r"\title{Synthetic title}\author{\IEEEauthorblockN{Alice Example}"
            r"\IEEEauthorblockA{Synthetic Institute}}\maketitle"
            r"\begin{abstract}Synthetic abstract\end{abstract}"
            r"\begin{IEEEkeywords}Alpha,Beta\end{IEEEkeywords}",
        ),
    ],
)
def test_template_author_title_abstract_and_body(tmp_path, cls, front):
    source = project(
        tmp_path,
        f"\\documentclass{{{cls}}}\\begin{{document}}{front}"
        r"\section{Methods}Body sentinel\end{document}",
    )
    path = convert(source, tmp_path / "out")
    text = inspect_docx(path)["text"]
    for expected in ("Alice Example", "Synthetic title", "Synthetic abstract", "Body sentinel"):
        assert expected in text, (cls, expected, text)
    if cls != "article":
        assert "Synthetic Institute" in text
        assert "Alpha" in text and "Beta" in text


def test_subfileinclude_keeps_chapter_and_nested_paths(tmp_path):
    source = project(
        tmp_path,
        r"\documentclass{article}\begin{document}\subfileinclude{chapters/chapter}\end{document}",
    )
    (source / "chapters").mkdir()
    (source / "chapters/chapter.tex").write_text(
        r"\documentclass[../main.tex]{subfiles}\begin{document}"
        r"Chapter sentinel \input{nested}\end{document}"
    )
    (source / "chapters/nested.tex").write_text("Nested sentinel")
    path = convert(source, tmp_path / "out")
    assert "Chapter sentinel" in inspect_docx(path)["text"]
    assert "Nested sentinel" in inspect_docx(path)["text"]


def test_missing_asset_and_unknown_construct_are_reported(tmp_path):
    source = project(
        tmp_path,
        r"\documentclass{article}\begin{document}\includegraphics{missing.png}"
        r"\begin{unknownbox}Sentinel\end{unknownbox}\end{document}",
    )
    path = convert(source, tmp_path / "out")
    report = json.loads((path.parent / "conversion-report.json").read_text())
    assert any("missing" in x.lower() for x in report["warnings"])
    assert any("unknownbox" in x for x in report["warnings"])


def test_outside_project_read_fails_or_reports_blocked_access(tmp_path):
    outside = tmp_path / "private.tex"
    outside.write_text("PRIVATE SENTINEL MUST NOT APPEAR")
    source = project(
        tmp_path,
        "\\documentclass{article}\\begin{document}\\input{"
        + outside.as_posix()
        + "}\\end{document}",
    )
    try:
        result = convert(source, tmp_path / "out")
    except ConversionError as e:
        assert "blocked" in str(e) or "outside" in str(e)
    else:
        assert "PRIVATE SENTINEL" not in inspect_docx(result)["text"]
        assert "blocked" in (result.parent / "conversion-report.json").read_text()


def test_cancel_and_timeout_do_not_publish_export(tmp_path):
    event = threading.Event()
    event.set()
    with pytest.raises(Cancelled):
        convert(EXAMPLE, tmp_path / "out", cancel=event)
    with pytest.raises(ConversionError, match="exceeded"):
        convert(EXAMPLE, tmp_path / "out", Options(timeout=0))
    assert not list((tmp_path / "out").glob("brando-*"))


def test_later_export_preserves_previous_result(tmp_path):
    first = convert(EXAMPLE, tmp_path)
    digest = sha256(first.read_bytes()).hexdigest()
    second = convert(EXAMPLE, tmp_path)
    assert first != second
    assert sha256(first.read_bytes()).hexdigest() == digest


def test_reference_docx_applies_selected_style(tmp_path):
    from docx import Document
    from docx.shared import Pt

    ref = tmp_path / "reference.docx"
    doc = Document()
    doc.styles["Normal"].font.size = Pt(17)
    doc.save(ref)
    result = convert(EXAMPLE, tmp_path / "out", Options(reference=ref))
    assert Document(result).styles["Normal"].font.size.pt == 17


def test_main_in_nested_folder_resolves_project_root_and_main_relative_inputs(tmp_path):
    source = tmp_path / "source"
    (source / "manuscript").mkdir(parents=True)
    (source / "shared").mkdir()
    (source / "manuscript/main.tex").write_text(
        r"\documentclass{article}\begin{document}\input{shared/root}\input{local}\end{document}"
    )
    (source / "shared/root.tex").write_text("Project root sentinel")
    (source / "manuscript/local.tex").write_text("Main relative sentinel")
    result = convert(source, tmp_path / "out")
    text = inspect_docx(result)["text"]
    assert "Project root sentinel" in text
    assert "Main relative sentinel" in text


def test_non_utf8_included_source_is_normalized_only_in_snapshot(tmp_path):
    source = project(
        tmp_path, r"\documentclass{article}\begin{document}\input{chapter}\end{document}"
    )
    data = "café – nested encoding".encode("cp1252")
    (source / "chapter.tex").write_bytes(data)
    result = convert(source, tmp_path / "out")
    assert "café" in inspect_docx(result)["text"]
    assert (source / "chapter.tex").read_bytes() == data
    assert "chapter.tex" in (result.parent / "conversion-notes.txt").read_text()


def test_inline_review_macros_obey_comments_checkbox(tmp_path):
    source = project(
        tmp_path,
        r"\documentclass{article}\begin{document}Body \todo{Inline review note}."
        r"\footnote{Footnote text \todo{Footnote review note}}\end{document}",
    )
    off = convert(source, tmp_path / "out")
    assert inspect_docx(off)["native_comment_count"] == 0
    with ZipFile(off) as z:
        for name in z.namelist():
            if name.startswith("word/") and name.endswith(".xml"):
                assert b"commentReference" not in z.read(name)
    on = convert(source, tmp_path / "out", Options(comments=True))
    assert inspect_docx(on)["native_comment_count"] == 2
    report = json.loads((on.parent / "conversion-report.json").read_text())
    assert report["inline_engine_comments"] == 2
    assert report["appendix_source_comments"] == 0


def test_failed_report_write_leaves_no_partial_export(tmp_path, monkeypatch):
    original = Path.write_text

    def fail_report(path, *args, **kwargs):
        if path.name == "conversion-report.json":
            raise OSError("Simulated destination write failure")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_report)
    with pytest.raises(OSError, match="Simulated"):
        convert(EXAMPLE, tmp_path / "out")
    assert list((tmp_path / "out").iterdir()) == []
