"""Small desktop shell; import and conversion run away from the UI thread."""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QPoint, QStandardPaths, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from .core import TEMPLATES, Options, convert, detect_template
from .project import Cancelled, Project, capture, decode, source_notes


def _file_row(field: QLineEdit, *buttons: QPushButton) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(field, 1)
    for button in buttons:
        row.addWidget(button)
    return row


def _option_label(text: str, explanation: str) -> QWidget:
    label = QWidget()
    row = QHBoxLayout(label)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(5)
    row.addWidget(QLabel(text))
    info = QToolButton()
    info.setObjectName("optionInfo")
    info.setText("i")
    info.setAutoRaise(True)
    info.setFixedSize(22, 22)
    info.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    info.setAccessibleName(f"About {text.lower()}")
    info.setToolTip(explanation)
    info.clicked.connect(
        lambda: QToolTip.showText(info.mapToGlobal(QPoint(0, info.height())), explanation, info)
    )
    row.addWidget(info)
    row.addStretch()
    return label


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
        self.setWindowTitle("Brando — LaTeX to Word")
        self.resize(790, 710)
        self.setAcceptDrops(True)
        self.project: Project | None = None
        self.project_path: Path | None = None
        self.source_comment_count: int | None = None
        self.task: Task | None = None
        self.output: Path | None = None
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("From your project to Word")
        title_font = title.font()
        title_font.setPointSize(21)
        title_font.setWeight(QFont.Weight.DemiBold)
        title.setFont(title_font)
        layout.addWidget(title)
        intro = QLabel(
            "Drop an Overleaf source ZIP or project folder here. Conversion stays on this computer."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        form.setSpacing(12)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Select or drop a project")
        self.input.editingFinished.connect(self.scan)
        self.zip_button = QPushButton("ZIP…")
        self.folder_button = QPushButton("Folder…")
        self.zip_button.clicked.connect(self.choose_zip)
        self.folder_button.clicked.connect(self.choose_folder)
        form.addRow(
            _option_label("Project", "Choose an Overleaf source ZIP or a project folder."),
            _file_row(self.input, self.zip_button, self.folder_button),
        )
        self.root = QComboBox()
        self.root.setEditable(True)
        self.root.currentTextChanged.connect(self.update_template)
        form.addRow(
            _option_label(
                "Main document",
                "Choose the .tex file that starts the manuscript. Convert supplements separately.",
            ),
            self.root,
        )
        self.template = QComboBox()
        self.template.addItems(TEMPLATES)
        form.addRow(
            _option_label(
                "Source template",
                "Auto uses the LaTeX document class. "
                "Overrides change how the source is interpreted. "
                "All template families are experimental.",
            ),
            self.template,
        )
        self.detected = QLabel(
            "Template support is experimental. Choose a main document to see detection."
        )
        self.detected.setWordWrap(True)
        form.addRow("", self.detected)
        self.layout_choice = QComboBox()
        self.layout_choice.addItems(["Readable review", "Reference DOCX"])
        self.layout_choice.currentIndexChanged.connect(self.layout_changed)
        form.addRow(
            _option_label(
                "Word layout",
                "Readable review uses a single-column Word layout. Reference DOCX uses styles "
                "and page settings from a Word file you choose.",
            ),
            self.layout_choice,
        )
        self.reference = QLineEdit()
        self.reference.setPlaceholderText("Select a reference Word file")
        self.reference_button = QPushButton("Browse…")
        self.reference_button.clicked.connect(self.choose_reference)
        form.addRow(
            _option_label(
                "Reference", "Choose a DOCX whose styles and page settings will be used."
            ),
            _file_row(self.reference, self.reference_button),
        )
        self.comments = QCheckBox("Include source comments")
        self.comments.setToolTip(
            "Native Word comments in a source-location appendix. "
            "Includes unused .tex/.bib files. Overleaf Review discussions are not included."
        )
        self.comment_status = QLabel()
        self.comment_status.setWordWrap(True)
        self.comments.toggled.connect(self.update_comment_status)
        comment_options = QWidget()
        comment_layout = QVBoxLayout(comment_options)
        comment_layout.setContentsMargins(0, 0, 0, 0)
        comment_layout.addWidget(self.comments)
        comment_layout.addWidget(self.comment_status)
        form.addRow(
            _option_label(
                "Source comments",
                "Opt in to native Word comments. Percent notes from captured .tex/.bib files "
                "use appendix anchors, including unused files. Supported inline annotations "
                "keep engine anchors. Overleaf Review discussions require a separate source. "
                "Track Changes is a separate Word feature.",
            ),
            comment_options,
        )
        self.update_comment_status()
        self.destination = QLineEdit()
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        self.destination.setText(str(Path(documents) / "Brando_exports"))
        self.destination_button = QPushButton("Browse…")
        self.destination_button.clicked.connect(self.choose_destination)
        form.addRow(
            _option_label(
                "Destination",
                "Choose where to save the Word document and conversion notes. "
                "Each conversion creates a new export folder.",
            ),
            _file_row(self.destination, self.destination_button),
        )
        layout.addLayout(form)
        self.convert_button = QPushButton("Convert to Word")
        self.convert_button.setMinimumHeight(40)
        self.convert_button.setEnabled(False)
        self.convert_button.clicked.connect(self.start_conversion)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_task)
        actions = QHBoxLayout()
        actions.addWidget(self.convert_button, 1)
        actions.addWidget(self.cancel_button)
        layout.addLayout(actions)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        layout.addWidget(self.bar)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Conversion notes and any unsupported content appear here.")
        layout.addWidget(self.log, 1)
        self.open_word = QPushButton("Open Word file")
        self.open_folder = QPushButton("Open output folder")
        self.open_word.clicked.connect(lambda: self.open_path(self.output))
        self.open_folder.clicked.connect(
            lambda: self.open_path(self.output.parent if self.output else None)
        )
        self.open_word.setEnabled(False)
        self.open_folder.setEnabled(False)
        bottom = QHBoxLayout()
        bottom.addWidget(self.open_word)
        bottom.addWidget(self.open_folder)
        bottom.addStretch()
        layout.addLayout(bottom)
        self.layout_changed()

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
                detected + "Enabled. Percent notes use appendix anchors. "
                "Supported inline annotations keep engine anchors."
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
        self.convert_button.setEnabled(not busy and self.project is not None)
        self.cancel_button.setEnabled(busy)
        self.bar.setRange(0, 0 if busy else 1)

    def run_task(self, action, success):
        self.set_busy(True)
        self.task = Task(action, self)
        self.task.progress.connect(self.log.appendPlainText)
        self.task.succeeded.connect(success)
        self.task.failed.connect(self.task_failed)
        self.task.finished.connect(self.task_finished)
        self.task.start()

    def task_failed(self, message):
        self.log.appendPlainText(message)

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
        self.root.blockSignals(False)
        self.update_template()
        message = (
            f"Captured {len(self.project.files)} files; {len(candidates)} candidate main documents."
        )
        if len(candidates) != 1:
            message += " Select the manuscript root; supplements are converted separately."
        self.log.appendPlainText(message)

    def update_template(self):
        if self.project and self.root.currentText() in self.project.files:
            name = detect_template(decode(self.project.files[self.root.currentText()])[0])
            self.detected.setText(
                f"Detected: {name}. Support: experimental; inspect the output and notes."
            )

    def start_conversion(self):
        if not self.project or not self.project_path or self.task:
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
                f"({report['appendix_source_comments']} appendix, "
                f"{report['inline_engine_comments']} inline)."
            )
        else:
            self.log.appendPlainText("Source comments were OFF for this export.")
        for warning in report["warnings"]:
            self.log.appendPlainText("• " + warning)
        self.log.appendPlainText(
            "Review content and layout before sharing. Full details: conversion-report.json."
        )
        self.open_word.setEnabled(True)
        self.open_folder.setEnabled(True)
        self.bar.setValue(1)

    def dragEnterEvent(self, event):
        if not self.task and event.mimeData().hasUrls() and len(event.mimeData().urls()) == 1:
            if event.mimeData().urls()[0].isLocalFile():
                event.acceptProposedAction()

    def dropEvent(self, event):
        if not self.task:
            self.input.setText(event.mimeData().urls()[0].toLocalFile())
            self.scan(force=True)
            event.acceptProposedAction()

    def closeEvent(self, event):
        if self.task:
            self.cancel_task()
            self.log.appendPlainText("Wait for cancellation to finish, then close the window.")
            event.ignore()
        else:
            event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Brando")
    app.setOrganizationName("Brando")
    window = Window()
    window.show()
    if "--ui-smoke" in sys.argv:
        QTimer.singleShot(300, app.quit)
    return app.exec()
