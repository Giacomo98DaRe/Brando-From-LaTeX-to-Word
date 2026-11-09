import stat
import threading
from zipfile import ZipFile, ZipInfo

import pytest

from brando.project import Cancelled, ConversionError, capture, split_comment

ARTICLE = rb"\documentclass{article}\begin{document}Body\end{document}"


def test_folder_and_enclosing_zip_have_same_paths(tmp_path):
    folder = tmp_path / "source"
    (folder / "parts").mkdir(parents=True)
    (folder / "main.tex").write_bytes(ARTICLE)
    (folder / "parts/child.tex").write_bytes(b"Child")
    archive = tmp_path / "project.zip"
    with ZipFile(archive, "w") as z:
        for f in folder.rglob("*"):
            if f.is_file():
                z.write(f, "Outer/" + f.relative_to(folder).as_posix())
    assert capture(folder).files == capture(archive).files
    assert capture(archive).enclosing_directory == "Outer"


@pytest.mark.parametrize(
    "name", ["../escape.tex", "/absolute.tex", "C:/drive.tex", "..\\escape.tex"]
)
def test_zip_traversal_rejected(tmp_path, name):
    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as z:
        z.writestr(name, ARTICLE)
    with pytest.raises(ConversionError, match="path"):
        capture(archive)


def test_zip_symlink_rejected(tmp_path):
    archive = tmp_path / "link.zip"
    info = ZipInfo("main.tex")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with ZipFile(archive, "w") as z:
        z.writestr(info, "../outside")
    with pytest.raises(ConversionError, match="symbolic"):
        capture(archive)


def test_duplicate_case_paths_rejected(tmp_path):
    archive = tmp_path / "case.zip"
    with ZipFile(archive, "w") as z:
        z.writestr("main.tex", ARTICLE)
        z.writestr("MAIN.tex", ARTICLE)
    with pytest.raises(ConversionError, match="colliding"):
        capture(archive)


def test_import_limits_are_enforced_before_reading(tmp_path, monkeypatch):
    import brando.project as module

    (tmp_path / "main.tex").write_bytes(ARTICLE)
    monkeypatch.setattr(module, "MAX_BYTES", 1)
    with pytest.raises(ConversionError, match="limit"):
        capture(tmp_path)


def test_subfiles_and_commented_classes_are_not_roots(tmp_path):
    (tmp_path / "main.tex").write_bytes(ARTICLE)
    (tmp_path / "supplement.tex").write_bytes(ARTICLE)
    (tmp_path / "chapter.tex").write_text(
        r"\documentclass[main.tex]{subfiles}\begin{document}Chapter\end{document}"
    )
    (tmp_path / "fragment.tex").write_text("% " + ARTICLE.decode())
    assert capture(tmp_path).candidates() == ["main.tex", "supplement.tex"]


def test_cancelled_capture(tmp_path):
    (tmp_path / "main.tex").write_bytes(ARTICLE)
    event = threading.Event()
    event.set()
    with pytest.raises(Cancelled):
        capture(tmp_path, event)


def test_literal_and_escaped_percent_are_not_notes():
    assert split_comment(r"95\% \verb|50%| % actual") == (r"95\% \verb|50%| ", " actual")
