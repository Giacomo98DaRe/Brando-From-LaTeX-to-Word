"""Small native desktop controls for source selection and accessible switches."""

from html import escape
from pathlib import Path

from PySide6.QtCore import QEvent, QMimeData, QPoint, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)


class InformationButton(QToolButton):
    """Short, wrapped help anchored to its control, for hover or keyboard activation."""

    def __init__(self, title: str, explanation: str):
        super().__init__()
        self.setObjectName("optionInfo")
        self.setText("i")
        self.setFixedSize(22, 22)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(f"About {title.lower()}")
        self.setAccessibleDescription(explanation)
        # Plain tooltip strings do not wrap; escape copy before enabling Qt rich text.
        self.setToolTip(f"<qt><p>{escape(explanation)}</p></qt>")
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.setInterval(250)
        self.hover_timer.timeout.connect(self.show_help)
        self.clicked.connect(self.show_help)

    def show_help(self):
        self.hover_timer.stop()
        QToolTip.showText(
            self.mapToGlobal(QPoint(0, self.height() + 4)),
            self.toolTip(),
            self,
            self.rect(),
            10000,
        )

    def enterEvent(self, event):
        self.hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_timer.stop()
        QToolTip.hideText()
        super().leaveEvent(event)

    def event(self, event):
        # Suppress the platform's second tooltip timer and cursor-relative positioning.
        if event.type() == QEvent.Type.ToolTip:
            event.accept()
            return True
        if event.type() in (QEvent.Type.Hide, QEvent.Type.FocusOut):
            self.hover_timer.stop()
            QToolTip.hideText()
        return super().event(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            QToolTip.hideText()
            event.accept()
        else:
            super().keyPressEvent(event)


def option_label(text: str, explanation: str, name: str = "optionLabel") -> QWidget:
    widget = QWidget()
    row = QHBoxLayout(widget)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(7)
    label = QLabel(text)
    label.setObjectName(name)
    row.addWidget(label)
    row.addWidget(InformationButton(text, explanation))
    row.addStretch()
    return widget


class Switch(QAbstractButton):
    """Checkable Qt button with a painted slide and native keyboard activation."""

    def __init__(self, label: str):
        super().__init__()
        self.setCheckable(True)
        self.setAccessibleName(label)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFixedSize(48, 28)

    def sizeHint(self) -> QSize:
        return QSize(48, 28)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        role = QPalette.ColorRole.Highlight if self.isChecked() else QPalette.ColorRole.Mid
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.palette().color(role))
        painter.drawRoundedRect(QRectF(2, 2, 44, 24), 12, 12)
        painter.setBrush(QColor("#FFFFFF"))
        painter.drawEllipse(QRectF(24 if self.isChecked() else 4, 4, 20, 20))
        if self.hasFocus():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(self.palette().color(QPalette.ColorRole.Highlight), 2))
            painter.drawRoundedRect(QRectF(1, 1, 46, 26), 13, 13)


def dropped_project(mime: QMimeData) -> str | None:
    urls = mime.urls()
    if len(urls) != 1 or not urls[0].isLocalFile():
        return None
    path = Path(urls[0].toLocalFile())
    return str(path) if path.suffix.lower() == ".zip" or path.is_dir() else None


class DropArea(QFrame):
    projectDropped = Signal(str)

    def __init__(self, icon: QIcon):
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumSize(360, 350)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(9)
        layout.addWidget(option_label("LaTeX project", "Choose an Overleaf source ZIP or folder."))
        layout.addStretch()
        picture = QLabel()
        picture.setPixmap(icon.pixmap(80, 80))
        picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(picture)
        self.title = QLabel("Drop your project here")
        self.title.setObjectName("dropTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title)
        hint = QLabel("Overleaf ZIP or complete project folder")
        hint.setProperty("secondary", True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self.zip_button = QPushButton("Choose ZIP")
        self.folder_button = QPushButton("Choose folder")
        buttons.addWidget(self.zip_button)
        buttons.addWidget(self.folder_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        layout.addStretch()
        path_label = QLabel("Project path (optional)")
        path_label.setProperty("secondary", True)
        layout.addWidget(path_label)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Paste a ZIP or folder path, then press Enter")
        self.input.setAccessibleName("Project path")
        self.input.setAccessibleDescription(
            "Optional. Paste a project path and press Enter to load."
        )
        path_label.setBuddy(self.input)
        layout.addWidget(self.input)
        self.summary = QLabel("Conversion stays on this computer.")
        self.summary.setProperty("secondary", True)
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)

    def set_drag_active(self, active: bool):
        self.setProperty("dragActive", active)
        self.title.setText("Release to import" if active else "Drop your project here")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def dragEnterEvent(self, event):
        if self.acceptDrops() and dropped_project(event.mimeData()):
            self.set_drag_active(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.set_drag_active(False)
        event.accept()

    def dropEvent(self, event):
        self.set_drag_active(False)
        path = dropped_project(event.mimeData())
        if self.acceptDrops() and path:
            self.projectDropped.emit(path)
            event.acceptProposedAction()
