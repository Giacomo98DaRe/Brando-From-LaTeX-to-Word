import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
from pathlib import Path
from zipfile import ZipFile

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QToolButton

from brando.core import inspect_docx
from brando.gui import Window

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/article"


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def complete(app, window):
    deadline = time.monotonic() + 30
    ticks = 0
    while window.task and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
        ticks += 1
    assert window.task is None, window.log.toPlainText()
    return ticks


@pytest.mark.parametrize("include_comments", [False, True])
def test_ui_scan_convert_and_responsiveness(app, tmp_path, include_comments):
    window = Window()
    try:
        assert not window.comments.isChecked()
        assert Path(window.destination.text()).name == "Brando_exports"
        information = window.findChildren(QToolButton, "optionInfo")
        assert len(information) == 8
        assert all(button.toolTip() and button.accessibleName() for button in information)
        window.input.setText(str(EXAMPLE))
        window.scan()
        assert window.cancel_button.isEnabled()
        complete(app, window)
        assert window.root.currentText() == "main.tex"
        assert "Standard article" in window.detected.text()
        assert window.source_comment_count == 3
        assert "3 percent source notes" in window.comment_status.text()
        window.comments.setChecked(include_comments)
        window.destination.setText(str(tmp_path))
        window.start_conversion()
        assert complete(app, window) > 1
        assert window.output and window.output.is_file(), window.log.toPlainText()
        assert "Avery Example" in inspect_docx(window.output)["text"]
        assert inspect_docx(window.output)["native_comment_count"] == (3 if include_comments else 0)
        assert (
            "Source comments exported: 3" if include_comments else "Source comments were OFF"
        ) in window.log.toPlainText()
        assert window.open_word.isEnabled()
        previous = window.output
        invalid = tmp_path / "invalid.zip"
        invalid.write_bytes(b"Original synthetic invalid archive")
        window.select_project(str(invalid))
        complete(app, window)
        assert window.output is None
        assert not window.open_word.isEnabled()
        assert "retry" in window.drop_area.summary.text()
        assert previous.is_file()
    finally:
        window.close()


@pytest.mark.parametrize("kind", ["folder", "zip"])
def test_drop_project_in_large_target(app, tmp_path, kind):
    window = Window()
    try:
        project = EXAMPLE
        if kind == "zip":
            project = tmp_path / "project.zip"
            with ZipFile(project, "w") as archive:
                for path in EXAMPLE.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(EXAMPLE))
        data = QMimeData()
        data.setUrls([QUrl.fromLocalFile(str(project))])
        enter = QDragEnterEvent(
            QPoint(10, 10),
            Qt.DropAction.CopyAction,
            data,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        app.sendEvent(window.drop_area, enter)
        assert enter.isAccepted()
        assert window.drop_area.property("dragActive")
        event = QDropEvent(
            QPointF(10, 10),
            Qt.DropAction.CopyAction,
            data,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        app.sendEvent(window.drop_area, event)
        assert event.isAccepted()
        assert not window.drop_area.property("dragActive")
        complete(app, window)
        assert window.project is not None
    finally:
        window.close()


def test_theme_switch_keeps_geometry_and_conversion_choices(app, tmp_path):
    window = Window()
    window.show()
    try:
        window.input.setText(str(EXAMPLE))
        window.scan()
        complete(app, window)
        window.comments.setChecked(True)
        window.destination.setText(str(tmp_path))
        # Word-wrapped status text posts a deferred layout request in Qt.
        QTest.qWait(20)
        controls = (
            window.drop_area,
            window.root,
            window.template,
            window.layout_choice,
            window.comments,
            window.comment_status,
            window.reference,
            window.destination,
            window.convert_button,
        )
        geometry = [widget.geometry() for widget in controls]
        captured = window.project
        assert not window.theme_toggle.isChecked()
        window.theme_toggle.setFocus()
        QTest.keyClick(window.theme_toggle, Qt.Key.Key_Space)
        QTest.qWait(20)
        assert window.theme_toggle.isChecked()
        assert [widget.geometry() for widget in controls] == geometry
        assert window.project is captured
        assert window.root.currentText() == "main.tex"
        assert window.comments.isChecked()
        window.start_conversion()
        window.theme_toggle.click()
        assert not window.theme_toggle.isChecked()
        assert complete(app, window) > 1
        assert inspect_docx(window.output)["native_comment_count"] == 3
    finally:
        window.close()


def test_unreadable_comment_preview_keeps_project_importable(app, tmp_path):
    (tmp_path / "main.tex").write_text(r"\documentclass{article}\begin{document}Body\end{document}")
    (tmp_path / "notes.bib").write_bytes(b"\x81")
    window = Window()
    try:
        window.input.setText(str(tmp_path))
        window.scan()
        complete(app, window)
        assert window.project is not None
        assert window.source_comment_count is None
        assert window.convert_button.isEnabled()
    finally:
        window.close()


def test_long_failure_keeps_compact_window_actions_visible(app):
    window = Window()
    window.resize(880, 620)
    window.show()
    try:
        diagnostic = "Synthetic failure details " * 100 + "\n" + "Trace details " * 1000
        window.task_failed(diagnostic)
        QTest.qWait(20)
        assert len(window.status.text()) <= 180
        assert window.log.toPlainText() == diagnostic
        assert window.details_button.isChecked()
        bottom = window.convert_button.mapTo(window, window.convert_button.rect().bottomRight())
        assert bottom.y() < window.height()
    finally:
        window.close()


def test_ambiguous_root_is_not_auto_selected(app, tmp_path):
    article = r"\documentclass{article}\begin{document}Text\end{document}"
    (tmp_path / "main.tex").write_text(article)
    (tmp_path / "supplement.tex").write_text(article)
    window = Window()
    try:
        window.input.setText(str(tmp_path))
        window.scan()
        complete(app, window)
        assert window.root.currentText() == ""
        assert window.root.count() == 2
    finally:
        window.close()


def test_focus_change_keeps_main_selection_and_reselection_refreshes(app, tmp_path):
    original = r"\documentclass{article}\begin{document}Original\end{document}"
    (tmp_path / "main.tex").write_text(original)
    (tmp_path / "supplement.tex").write_text(original)
    window = Window()
    try:
        window.input.setText(str(tmp_path))
        window.scan()
        complete(app, window)
        window.root.setCurrentText("supplement.tex")
        window.input.editingFinished.emit()
        assert window.task is None
        assert window.root.currentText() == "supplement.tex"

        updated = original.replace("Original", "Updated")
        (tmp_path / "main.tex").write_text(updated)
        window.scan(force=True)
        complete(app, window)
        assert window.project.files["main.tex"].decode() == updated
        assert window.root.currentText() == ""
    finally:
        window.close()
