"""OS-specific desktop identity, kept separate from conversion and portable widgets."""

import ctypes
import sys


def set_process_identity() -> None:
    if sys.platform == "win32":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Brando.Desktop")


def set_titlebar_theme(handle: int, dark: bool) -> None:
    if sys.platform == "win32":
        # DWM applies this to the application window without changing Windows settings.
        enabled = ctypes.c_int(dark)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(handle), 20, ctypes.byref(enabled), ctypes.sizeof(enabled)
        )
