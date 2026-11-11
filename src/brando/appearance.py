"""Shared desktop geometry uses two interchangeable color palettes."""

from pathlib import Path
from string import Template

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication, QToolTip, QWidget

from .desktop import set_titlebar_theme
from .widgets import Switch

RESOURCES = Path(__file__).with_name("resources")

LAGOON = {
    "background": "#F3F7F8",
    "surface": "#FFFFFF",
    "input": "#FFFFFF",
    "text": "#15313B",
    "muted": "#526B75",
    "border": "#D4E2E6",
    "drop_border": "#89BFB9",
    "accent": "#087F79",
    "accent_hover": "#066B66",
    "on_accent": "#FFFFFF",
    "comment": "#E9F7F3",
    "comment_border": "#9DCFC5",
    "info": "#E5F1EF",
    "hover": "#DCEFEA",
    "disabled": "#EDF2F3",
    "disabled_text": "#607881",
    "tooltip": "#15313B",
    "tooltip_text": "#FFFFFF",
}
DEEP_TIDE = {
    "background": "#0A1923",
    "surface": "#122A36",
    "input": "#10232E",
    "text": "#E9F5F6",
    "muted": "#A2BCC3",
    "border": "#38545F",
    "drop_border": "#438E89",
    "accent": "#49D6C1",
    "accent_hover": "#78E6D4",
    "on_accent": "#09272B",
    "comment": "#143A40",
    "comment_border": "#38877D",
    "info": "#21454B",
    "hover": "#254653",
    "disabled": "#152E3A",
    "disabled_text": "#91A9B2",
    "tooltip": "#E9F5F6",
    "tooltip_text": "#15313B",
}


def application_icon() -> QIcon:
    return QIcon(str(RESOURCES / "brando.ico"))


def apply_theme(window: QWidget, dark: bool) -> None:
    colors = DEEP_TIDE if dark else LAGOON
    palette = QPalette()
    for role, key in (
        (QPalette.ColorRole.Window, "background"),
        (QPalette.ColorRole.WindowText, "text"),
        (QPalette.ColorRole.Base, "input"),
        (QPalette.ColorRole.AlternateBase, "surface"),
        (QPalette.ColorRole.Text, "text"),
        (QPalette.ColorRole.Button, "surface"),
        (QPalette.ColorRole.ButtonText, "text"),
        (QPalette.ColorRole.Highlight, "accent"),
        (QPalette.ColorRole.HighlightedText, "on_accent"),
        (QPalette.ColorRole.PlaceholderText, "muted"),
        (QPalette.ColorRole.Mid, "disabled_text"),
        (QPalette.ColorRole.Light, "surface"),
        (QPalette.ColorRole.ToolTipBase, "tooltip"),
        (QPalette.ColorRole.ToolTipText, "tooltip_text"),
    ):
        palette.setColor(role, QColor(colors[key]))
    window.setPalette(palette)
    QToolTip.setPalette(palette)
    # Native tooltip fades can overlap rapid changes between adjacent help controls.
    # This affects only Brando's Qt process, not Windows animation preferences.
    QApplication.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    QApplication.setEffectEnabled(Qt.UIEffect.UI_FadeTooltip, False)
    stylesheet = Template((RESOURCES / "desktop.qss").read_text(encoding="utf-8"))
    window.setStyleSheet(
        stylesheet.substitute(colors, chevron=(RESOURCES / "chevron.svg").as_posix())
    )
    # Styled buttons can retain the platform highlight unless their palette is explicit.
    for switch in window.findChildren(Switch):
        switch.setPalette(palette)
    set_titlebar_theme(int(window.winId()), dark)
