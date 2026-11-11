"""Generate a real Qt UI screenshot using only the synthetic example and relative paths."""

import argparse
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import time
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from brando.gui import Window

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dark", action="store_true", help="Capture Deep Tide colors")
args = parser.parse_args()
os.chdir(ROOT)
app = QApplication([])
# The Windows offscreen Qt plugin does not enumerate native system fonts.
# Load installed fonts for this screenshot only; no font files are redistributed.
if os.name == "nt":
    fonts = Path(os.environ.get("SystemRoot", "C:/Windows")) / "Fonts"
    for filename in ("segoeui.ttf", "segoeuib.ttf"):
        QFontDatabase.addApplicationFont(str(fonts / filename))
    app.setFont(QFont("Segoe UI", 10))
window = Window()
window.theme_toggle.setChecked(args.dark)
window.input.setText("examples/article")
window.destination.setText("outputs")
window.show()
window.scan()
deadline = time.monotonic() + 20
while window.task and time.monotonic() < deadline:
    app.processEvents()
    time.sleep(0.01)
assert window.project is not None
assert window.root.currentText() == "main.tex"
app.processEvents()
target = ROOT / "docs/images" / ("desktop-dark.png" if args.dark else "desktop.png")
target.parent.mkdir(parents=True, exist_ok=True)
assert window.grab().save(str(target))
window.close()
print(target.relative_to(ROOT))
