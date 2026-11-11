"""Small desktop shell; import and conversion run away from the UI thread."""

from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .appearance import application_icon, apply_theme
from .core import TEMPLATES, Options, convert, detect_template
from .desktop import set_process_identity
from .project import Cancelled, Project, capture, decode, source_notes
from .widgets import DropArea, InformationButton, Switch, dropped_project, option_label


def _file_row(field: QLineEdit, *buttons: QPushButton) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(field, 1)
    for button in buttons:
        row.addWidget(button)
    return row


class Task(QThread):
    succeeded = Signal(object)
    failed = Signal(str)
    progress = Signal(str)

    def __init__(self, action, parent=None):
        super().__init__(parent)
        self.action = action
        self.cancel = threading.Event()

    def run(self):
        try:
            self.succeeded.emit(self.action(self.cancel, self.progress.emit))
        except Cancelled:
            self.failed.emit("Cancelled. No completed export was published.")
        except Exception as exc:
            self.failed.emit(str(exc))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Brando - LaTeX to Word")
        self.setWindowIcon(application_icon())
        self.resize(1160, 820)
        self.setMinimumSize(880, 620)
        self.setAcceptDrops(True)
        self.project: Project | None = None
        self.project_path: Path | None = None
        self.source_comment_count: int | None = None
        self.task: Task | None = None
        self.output: Path | None = None
        body = QWidget()
        body.setObjectName("windowBody")
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(14)
        layout.addLayout(self.build_header())

        content = QWidget()
        columns = QHBoxLayout(content)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(22)
        left = QVBoxLayout()
        left.setSpacing(14)
        self.drop_area = DropArea(application_icon())
        self.drop_area.projectDropped.connect(self.select_project)
        self.input = self.drop_area.input
        self.zip_button = self.drop_area.zip_button
        self.folder_button = self.drop_area.folder_button
        self.input.returnPressed.connect(lambda: self.scan(force=True))
        self.input.textEdited.connect(self.project_path_edited)
        self.zip_button.clicked.connect(self.choose_zip)
        self.folder_button.clicked.connect(self.choose_folder)
        left.addWidget(self.drop_area, 1)
        left.addWidget(self.build_comments())
        columns.addLayout(left, 5)
        columns.addWidget(self.build_options(), 3)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll, 1)

        self.details_button = QToolButton()
        self.details_button.setText("Conversion details")
        self.details_button.setEnabled(False)
        self.details_button.setCheckable(True)
        self.details_button.setArrowType(Qt.ArrowType.RightArrow)
        self.details_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.details_button.toggled.connect(self.show_details)
        details_row = QHBoxLayout()
        details_row.addWidget(self.details_button)
        details_row.addWidget(
            InformationButton(
                "Conversion details",
                "View progress, warnings and errors. Completed exports save notes and a report "
                "beside the Word file. These are separate from Word comments.",
            )
        )
        details_row.addStretch()
        layout.addLayout(details_row)
        self.details_panel = QWidget()
        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(6)
        details_hint = QLabel(
            "Progress, warnings and errors from this session. Completed exports save "
            "conversion-notes.txt and conversion-report.json beside the Word file. "
            "These are separate from Word comments."
        )
        details_hint.setWordWrap(True)
        details_hint.setProperty("secondary", True)
        details_layout.addWidget(details_hint)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(100)
        self.log.setMaximumHeight(140)
        self.log.setAccessibleName("Conversion progress and warnings")
        self.log.textChanged.connect(self.update_details)
        details_layout.addWidget(self.log)
        self.details_panel.hide()
        layout.addWidget(self.details_panel)
        layout.addLayout(self.build_actions())
        self.layout_changed()
        self.update_comment_status()
        self.theme_toggle.toggled.connect(lambda dark: apply_theme(self, dark))
        apply_theme(self, False)

    def build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        picture = QLabel()
        picture.setPixmap(application_icon().pixmap(48, 48))
        header.addWidget(picture)
        brand = QVBoxLayout()
        brand.setSpacing(0)
        title = QLabel("Brando")
        title.setObjectName("brandTitle")
        subtitle = QLabel("LaTeX to editable Word")
        subtitle.setProperty("secondary", True)
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch()
        theme_caption = option_label(
            "Deep Tide",
            "Switch between Lagoon and Deep Tide colors. Each new window starts in Lagoon.",
        )
        theme_caption.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        header.addWidget(theme_caption)
        self.theme_toggle = Switch("Use Deep Tide colors")
        self.theme_toggle.setToolTip("Use Deep Tide colors")
        header.addWidget(self.theme_toggle)
        return header

    def build_comments(self) -> QFrame:
        card = QFrame()
        card.setObjectName("commentsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        row = QHBoxLayout()
        row.addWidget(
            option_label(
                "Include source comments",
                "Add LaTeX notes as Word comments beside the text. Unmatched notes go to "
                "Source annotations at the end. Overleaf Review threads are not imported.",
                "commentTitle",
            ),
            1,
        )
        self.comments = Switch("Include source comments")
        self.comments.setToolTip("Include native Word comments in this export")
        self.comments.toggled.connect(self.update_comment_status)
        row.addWidget(self.comments)
        layout.addLayout(row)
        self.comment_status = QLabel()
        self.comment_status.setWordWrap(True)
        self.comment_status.setProperty("secondary", True)
        layout.addWidget(self.comment_status)
        return card

    def build_options(self) -> QFrame:
        card = QFrame()
        card.setObjectName("optionsCard")
        card.setMinimumWidth(336)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(12)
        heading = QLabel("Conversion options")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        self.root = QComboBox()
        self.root.setEditable(True)
        self.root.setAccessibleName("Main document")
        self.root.setPlaceholderText("Choose a project first")
        self.root.currentTextChanged.connect(self.update_template)
        self.template = QComboBox()
        self.template.setAccessibleName("Source template")
        self.template.addItems(TEMPLATES)
        self.layout_choice = QComboBox()
        self.layout_choice.setAccessibleName("Word layout")
        self.layout_choice.addItems(["Readable review", "Reference DOCX"])
        self.layout_choice.currentIndexChanged.connect(self.layout_changed)
        self.reference = QLineEdit()
        self.reference.setAccessibleName("Reference DOCX path")
        self.reference.setPlaceholderText("Choose a Word style reference")
        self.reference_button = QPushButton("...")
        self.reference_button.setAccessibleName("Browse reference Word document")
        self.reference_button.clicked.connect(self.choose_reference)
        self.destination = QLineEdit()
        self.destination.setAccessibleName("Export destination")
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        self.destination.setText(str(Path(documents) / "Brando_exports"))
        self.destination_button = QPushButton("...")
        self.destination_button.setAccessibleName("Browse export destination")
        self.destination_button.clicked.connect(self.choose_destination)
        for title, explanation, field, buttons in (
            (
                "Main document",
                "Choose the .tex manuscript root. Convert supplements separately.",
                self.root,
                (),
            ),
            (
                "Source template",
                "Detect the LaTeX template automatically, or choose one. "
                "Template support is experimental.",
                self.template,
                (),
            ),
            (
                "Word layout",
                "Readable review uses one column. Reference DOCX uses styles and "
                "page settings from a Word file you choose.",
                self.layout_choice,
                (),
            ),
            (
                "Reference DOCX",
                "Choose a DOCX supplying styles and page settings.",
                self.reference,
                (self.reference_button,),
            ),
            (
                "Destination",
                "Each conversion creates a new folder containing Word, conversion "
                "notes and a report.",
                self.destination,
                (self.destination_button,),
            ),
        ):
            group = QVBoxLayout()
            group.setSpacing(5)
            group.addWidget(option_label(title, explanation))
            group.addLayout(_file_row(field, *buttons))
            layout.addLayout(group)
        self.detected = QLabel("Template support is experimental.")
        self.detected.setProperty("secondary", True)
        self.detected.setWordWrap(True)
        self.detected.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.detected)
        layout.addStretch()
        return card

    def build_actions(self) -> QHBoxLayout:
        actions = QHBoxLayout()
        self.status = QLabel("Choose a project to begin.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        state = QVBoxLayout()
        state.addWidget(self.status)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1)
        self.bar.setTextVisible(False)
        self.bar.hide()
        state.addWidget(self.bar)
        actions.addLayout(state, 1)
        self.open_word = QPushButton("Open Word file")
        self.open_folder = QPushButton("Open folder")
        self.open_word.clicked.connect(lambda: self.open_path(self.output))
        self.open_folder.clicked.connect(
            lambda: self.open_path(self.output.parent if self.output else None)
        )
        for button in (self.open_word, self.open_folder):
            button.setEnabled(False)
            button.hide()
            actions.addWidget(button)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_task)
        self.cancel_button.hide()
        actions.addWidget(self.cancel_button)
        self.convert_button = QPushButton("Convert to Word")
        self.convert_button.setObjectName("convertButton")
        self.convert_button.setMinimumSize(200, 44)
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self.start_conversion)
        actions.addWidget(self.convert_button)
        return actions

    def show_details(self, visible: bool):
        self.details_panel.setVisible(visible)
        self.details_button.setArrowType(
            Qt.ArrowType.DownArrow if visible else Qt.ArrowType.RightArrow
        )

    def update_details(self):
        has_entries = not self.log.document().isEmpty()
        self.details_button.setEnabled(has_entries)
        if not has_entries:
            self.details_button.setChecked(False)

    def project_path_edited(self):
        self.convert_button.setEnabled(False)
        self.status.setText("Press Enter to load this project path.")

    def select_project(self, path: str):
        self.input.setText(path)
        self.scan(force=True)

    def open_path(self, path):
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def choose_zip(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Overleaf source ZIP", "", "ZIP archives (*.zip)"
        )
        if path:
            self.input.setText(path)
            self.scan(force=True)

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Project folder")
        if path:
            self.input.setText(path)
            self.scan(force=True)

    def choose_reference(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Reference Word file", "", "Word files (*.docx)"
        )
        if path:
            self.reference.setText(path)

    def choose_destination(self):
        path = QFileDialog.getExistingDirectory(self, "Output folder", self.destination.text())
        if path:
            self.destination.setText(path)

    def layout_changed(self):
        enabled = self.layout_choice.currentIndex() == 1
        self.reference.setEnabled(enabled)
        self.reference_button.setEnabled(enabled)

    def update_comment_status(self):
        count = self.source_comment_count
        detected = f"{count} percent source notes detected. " if count is not None else ""
        if self.comments.isChecked():
            self.comment_status.setText(
                detected + "On. Matching notes appear beside the text. "
                "Unmatched notes use Source annotations."
            )
        else:
            self.comment_status.setText(detected + "Off. Source comments will be omitted.")

    def set_busy(self, busy):
        for widget in (
            self.input,
            self.zip_button,
            self.folder_button,
            self.root,
            self.template,
            self.layout_choice,
            self.comments,
            self.destination,
            self.destination_button,
        ):
            widget.setEnabled(not busy)
        self.reference.setEnabled(not busy and self.layout_choice.currentIndex() == 1)
        self.reference_button.setEnabled(self.reference.isEnabled())
        self.convert_button.setEnabled(
            not busy
            and self.project is not None
            and Path(self.input.text().strip()) == self.project_path
        )
        self.cancel_button.setEnabled(busy)
        self.cancel_button.setVisible(busy)
        self.drop_area.setAcceptDrops(not busy)
        self.setAcceptDrops(not busy)
        self.bar.setRange(0, 0 if busy else 1)
        self.bar.setVisible(busy)

    def run_task(self, action, success):
        self.set_busy(True)
        self.task = Task(action, self)
        self.task.progress.connect(self.log.appendPlainText)
        self.task.progress.connect(self.status.setText)
        self.task.succeeded.connect(success)
        self.task.failed.connect(self.task_failed)
        self.task.finished.connect(self.task_finished)
        self.task.start()

    def task_failed(self, message):
        self.log.appendPlainText(message)
        summary = message.splitlines()[0] if message else "The operation could not be completed."
        self.status.setText(summary[:180])
        self.details_button.setChecked(True)
        if self.project is None:
            self.drop_area.summary.setText("Choose a source ZIP or project folder to retry.")

    def task_finished(self):
        task = self.task
        self.task = None
        self.set_busy(False)
        if task:
            task.deleteLater()

    def cancel_task(self):
        if self.task:
            self.task.cancel.set()
            self.cancel_button.setEnabled(False)
            self.log.appendPlainText("Cancelling…")

    def scan(self, force: bool = False):
        if self.task or not self.input.text().strip():
            return
        path = Path(self.input.text().strip())
        # Focus changes retain the snapshot and manual root selection. Explicit
        # reselection refreshes source bytes that may have changed on disk.
        if not force and self.project is not None and path == self.project_path:
            return
        self.project = None
        self.project_path = None
        self.source_comment_count = None
        self.update_comment_status()
        self.root.clear()
        self.log.clear()
        self.output = None
        for button in (self.open_word, self.open_folder):
            button.setEnabled(False)
            button.hide()
        self.details_button.setChecked(False)
        self.status.setText("Reading the project...")
        self.drop_area.summary.setText("Reading the project...")
        self.log.appendPlainText("Reading the project…")

        def read_project(cancel, progress):
            project = capture(path, cancel)
            try:
                notes, _ = source_notes(project)
                count = len(notes)
            except UnicodeDecodeError:
                # Optional comment preview must not block an otherwise valid import.
                count = None
            return path, project, count

        self.run_task(read_project, self.scanned)

    def scanned(self, value):
        self.project_path, self.project, self.source_comment_count = value
        self.update_comment_status()
        candidates = self.project.candidates()
        self.root.blockSignals(True)
        self.root.clear()
        self.root.addItems(candidates)
        others = sorted(n for n in self.project.files if n.endswith(".tex") and n not in candidates)
        self.root.addItems(others)
        if len(candidates) != 1:
            self.root.setCurrentIndex(-1)
            self.root.setEditText("")
        else:
            self.root.setCurrentIndex(0)
        self.root.blockSignals(False)
        self.update_template()
        message = (
            f"Captured {len(self.project.files)} files; {len(candidates)} candidate main documents."
        )
        if len(candidates) != 1:
            message += " Select the manuscript root; supplements are converted separately."
        self.log.appendPlainText(message)
        self.drop_area.summary.setText(
            f"{len(self.project.files)} captured files. {len(candidates)} candidate main documents."
        )
        self.status.setText(
            "Ready to convert." if len(candidates) == 1 else "Choose a main document."
        )

    def update_template(self):
        if self.project and self.root.currentText() in self.project.files:
            name = detect_template(decode(self.project.files[self.root.currentText()])[0])
            self.detected.setText(
                f"Detected: {name}. Support: experimental; inspect the output and notes."
            )

    def start_conversion(self):
        if (
            not self.project
            or not self.project_path
            or self.task
            or not self.convert_button.isEnabled()
        ):
            return
        if not self.root.currentText() or not self.destination.text().strip():
            QMessageBox.information(
                self,
                "Choose document and destination",
                "Select a main document and an output folder.",
            )
            return
        ref = None
        if self.layout_choice.currentIndex() == 1:
            if not self.reference.text().strip():
                QMessageBox.information(
                    self,
                    "Choose a reference",
                    "Select a reference DOCX or use the readable review layout.",
                )
                return
            ref = Path(self.reference.text())
        opts = Options(
            self.root.currentText(), self.template.currentText(), self.comments.isChecked(), ref
        )
        path, project, destination = self.project_path, self.project, Path(self.destination.text())
        self.open_word.setEnabled(False)
        self.open_folder.setEnabled(False)
        self.open_word.hide()
        self.open_folder.hide()
        self.log.clear()
        self.run_task(
            lambda cancel, progress: convert(path, destination, opts, cancel, progress, project),
            self.converted,
        )

    def converted(self, path):
        self.output = path
        report = json.loads((path.parent / "conversion-report.json").read_text(encoding="utf-8"))
        self.log.appendPlainText(f"Saved: {path}")
        if report["source_comments_enabled"]:
            self.log.appendPlainText(
                f"Source comments exported: {report['source_comments_exported']} "
                f"({report.get('body_source_comments', 0)} beside text, "
                f"{report['appendix_source_comments']} appendix, "
                f"{report['inline_engine_comments']} inline)."
            )
        else:
            self.log.appendPlainText("Source comments were OFF for this export.")
        for warning in report["warnings"]:
            self.log.appendPlainText("• " + warning)
        self.log.appendPlainText(
            "Saved beside Word: conversion-notes.txt and conversion-report.json. "
            "Review content and layout before sharing."
        )
        self.open_word.setEnabled(True)
        self.open_folder.setEnabled(True)
        self.open_word.show()
        self.open_folder.show()
        self.status.setText("Word file ready.")
        self.details_button.setChecked(bool(report["warnings"]))
        self.bar.setValue(1)

    def dragEnterEvent(self, event):
        if not self.task and dropped_project(event.mimeData()):
            self.drop_area.set_drag_active(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.drop_area.set_drag_active(False)
        event.accept()

    def dropEvent(self, event):
        self.drop_area.set_drag_active(False)
        path = dropped_project(event.mimeData())
        if not self.task and path:
            self.select_project(path)
            event.acceptProposedAction()

    def closeEvent(self, event):
        if self.task:
            self.cancel_task()
            self.log.appendPlainText("Wait for cancellation to finish, then close the window.")
            event.ignore()
        else:
            event.accept()


def _smoke_ui(app: QApplication, window: Window) -> None:
    """Exercise the frozen desktop using the same switch as an interactive user."""
    output = os.environ.get("BRANDO_UI_SMOKE_DIR")
    folder = Path(output) if output else None
    try:
        if folder:
            folder.mkdir(parents=True, exist_ok=True)
        assert not window.windowIcon().pixmap(32, 32).isNull()
        assert not app.windowIcon().pixmap(32, 32).isNull()
        controls = (window.drop_area, window.root, window.comments, window.convert_button)
        geometry = [widget.geometry() for widget in controls]
        states = {}
        for dark, name in ((True, "deep-tide"), (False, "lagoon")):
            window.theme_toggle.setChecked(dark)
            app.processEvents()
            assert [widget.geometry() for widget in controls] == geometry
            states[name] = window.palette().window().color().name()
            if folder:
                assert window.grab().save(str(folder / f"{name}.png"))
        assert states == {"deep-tide": "#0a1923", "lagoon": "#f3f7f8"}
        if folder:
            (folder / "result.json").write_text(json.dumps(states), encoding="utf-8")
        app.quit()
    except Exception as exc:
        if folder:
            (folder / "error.txt").write_text(str(exc), encoding="utf-8")
        app.exit(1)


def main() -> int:
    set_process_identity()
    app = QApplication(sys.argv)
    app.setApplicationName("Brando")
    app.setOrganizationName("Brando")
    app.setWindowIcon(application_icon())
    window = Window()
    window.show()
    if "--ui-smoke" in sys.argv:
        QTimer.singleShot(300, lambda: _smoke_ui(app, window))
    return app.exec()
