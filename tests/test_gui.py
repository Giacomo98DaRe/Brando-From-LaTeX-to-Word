import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
from pathlib import Path
from zipfile import ZipFile

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QToolButton, QToolTip

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


def wait_for_tooltip(text):
    # Hover timers and native event delivery vary with CI scheduler load.
    deadline = time.monotonic() + 2
    while QToolTip.text() != text and time.monotonic() < deadline:
        QTest.qWait(20)
    assert QToolTip.isVisible()
    assert QToolTip.text() == text


@pytest.mark.parametrize("include_comments", [False, True])
def test_ui_scan_convert_and_responsiveness(app, tmp_path, include_comments):
    window = Window()
    try:
        assert not window.comments.isChecked()
        assert window.status_chip.property("state") == "idle"
        assert window.findChild(QLabel, "commentTitle").text() == "Source comments"
        assert window.theme_toggle.accessibleName() == "Use dark mode"
        assert any(label.text() == "Dark mode" for label in window.findChildren(QLabel))
        assert Path(window.destination.text()).name == "Brando_exports"
        information = window.findChildren(QToolButton, "optionInfo")
        assert len(information) == 9
        assert all(button.toolTip() and button.accessibleName() for button in information)
        window.select_project(EXAMPLE)
        assert window.status_chip.property("state") == "busy"
        assert window.cancel_button.isEnabled()
        complete(app, window)
        assert window.root.currentText() == "main.tex"
        assert window.status_chip.property("state") == "ready"
        assert "Standard article" in window.detected.text()
        assert window.source_comment_count == 3
        assert "3 source notes found" in window.comment_status.text()
        window.comments.setChecked(include_comments)
        expected_status = (
            "Source notes will be included as Word comments."
            if include_comments
            else "Enable to include source notes as Word comments."
        )
        assert window.comment_status.text() == "3 source notes found. " + expected_status
        window.destination.setText(str(tmp_path))
        window.start_conversion()
        assert window.status_chip.property("state") == "busy"
        assert complete(app, window) > 1
        assert window.output and window.output.is_file(), window.log.toPlainText()
        assert "Avery Example" in inspect_docx(window.output)["text"]
        assert inspect_docx(window.output)["native_comment_count"] == (3 if include_comments else 0)
        assert (
            "Source comments exported: 3" if include_comments else "Source comments excluded"
        ) in window.log.toPlainText()
        assert window.open_word.isEnabled()
        assert window.status_chip.property("state") == "ready"
        assert (window.output.parent / "conversion-notes.txt").is_file()
        assert "Saved beside Word: conversion-notes.txt" in window.log.toPlainText()
        previous = window.output
        invalid = tmp_path / "invalid.zip"
        invalid.write_bytes(b"Original synthetic invalid archive")
        window.select_project(str(invalid))
        complete(app, window)
        assert window.output is None
        assert window.status_chip.property("state") == "error"
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
        window.select_project(EXAMPLE)
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
        window.select_project(tmp_path)
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
        assert window.status.fontMetrics().horizontalAdvance(window.status.text()) <= (
            window.status.contentsRect().width()
        )
        assert window.status.height() >= window.status.fontMetrics().height()
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
        window.select_project(tmp_path)
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
    window.show()
    try:
        window.select_project(tmp_path)
        complete(app, window)
        window.root.setCurrentText("supplement.tex")
        window.destination.setFocus()
        QTest.qWait(20)
        assert window.task is None
        assert window.root.currentText() == "supplement.tex"

        updated = original.replace("Original", "Updated")
        (tmp_path / "main.tex").write_text(updated)
        window.select_project(tmp_path)
        complete(app, window)
        assert window.project.files["main.tex"].decode() == updated
        assert window.root.currentText() == ""
    finally:
        window.close()


@pytest.mark.parametrize("dark", [False, True])
def test_information_tips_wrap_and_stay_anchored(app, dark):
    window = Window()
    window.theme_toggle.setChecked(dark)
    window.show()
    try:
        assert window.findChild(QLabel, "brandTitle").text() == "Brando"
        buttons = window.findChildren(QToolButton, "optionInfo")
        comments = next(b for b in buttons if b.accessibleName() == "About source comments")
        QTest.mouseMove(comments, QPoint(4, 4))
        wait_for_tooltip(comments.toolTip())
        tip = next(w for w in app.topLevelWidgets() if w.objectName() == "qtooltip_label")
        assert tip.width() <= 340
        assert tip.height() > 40  # Actual rendered multiline help, not an unwrapped strip.
        geometry = tip.geometry()
        QTest.mouseMove(comments, QPoint(16, 16))
        QTest.qWait(30)
        assert tip.geometry() == geometry

        destination = next(b for b in buttons if b.accessibleName() == "About destination")
        QTest.mouseMove(destination, QPoint(4, 4))
        wait_for_tooltip(destination.toolTip())
        assert tip.width() <= 340
        destination.setFocus()
        QTest.keyClick(destination, Qt.Key.Key_Space)
        QTest.qWait(150)
        assert QToolTip.isVisible()
        assert QToolTip.text() == destination.toolTip()
        QTest.keyClick(destination, Qt.Key.Key_Escape)
        QTest.qWait(350)
        assert not QToolTip.isVisible()
    finally:
        QToolTip.hideText()
        window.close()


def test_project_selection_shows_name_and_details_explain_saved_files(app):
    window = Window()
    window.show()
    try:
        assert not window.details_button.isEnabled()
        assert not window.details_panel.isVisible()
        assert window.drop_area.findChildren(QLineEdit) == []
        window.select_project(EXAMPLE)
        complete(app, window)
        assert window.project is not None
        assert EXAMPLE.name in window.drop_area.summary.text()
        assert window.convert_button.isEnabled()
        assert window.details_button.isEnabled()
        window.details_button.click()
        assert window.details_panel.isVisible()
        hint = " ".join(label.text() for label in window.details_panel.findChildren(QLabel))
        assert "conversion-notes.txt" in hint and "beside the Word file" in hint
        assert "separate from Word comments" in hint
        assert window.log.isReadOnly()

        window.log.clear()
        assert not window.details_button.isEnabled()
        assert not window.details_panel.isVisible()
    finally:
        window.close()


@pytest.mark.parametrize("dark", [False, True])
def test_status_indicator_tracks_required_options(app, tmp_path, dark):
    window = Window()
    window.theme_toggle.setChecked(dark)
    window.show()
    try:
        window.select_project(EXAMPLE)
        complete(app, window)
        assert window.status_chip.property("state") == "ready"
        color = window.status.palette().color(QPalette.ColorRole.WindowText)
        assert color.green() > max(color.red(), color.blue())
        QTest.qWait(20)
        assert window.status.fontMetrics().horizontalAdvance(window.status.text()) <= (
            window.status.contentsRect().width()
        )
        assert window.status.height() >= window.status.fontMetrics().height()

        window.destination.clear()
        assert window.status_chip.property("state") == "idle"
        assert not window.convert_button.isEnabled()
        window.destination.setText(str(tmp_path))
        assert window.status_chip.property("state") == "ready"
        window.root.setEditText("missing.tex")
        assert window.status_chip.property("state") == "idle"
        assert not window.convert_button.isEnabled()
        window.root.setCurrentText("main.tex")
        window.layout_choice.setCurrentIndex(1)
        assert window.status_chip.property("state") == "idle"
        assert not window.convert_button.isEnabled()
        window.reference.setText(str(tmp_path / "reference.docx"))
        assert window.status_chip.property("state") == "ready"
        assert window.convert_button.isEnabled()

        window.task_failed("Synthetic conversion error")
        assert window.status_chip.property("state") == "error"
        color = window.status.palette().color(QPalette.ColorRole.WindowText)
        assert color.red() > max(color.green(), color.blue())
    finally:
        window.close()
