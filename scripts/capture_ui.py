"""Generate a real Qt UI screenshot using only the synthetic example and relative paths."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path
import time

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QFontDatabase
from brando.gui import Window

ROOT = Path(__file__).resolve().parents[1]
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
window.input.setText("examples/article")
window.destination.setText("outputs")
window.show()
window.scan()
deadline = time.monotonic() + 20
while window.task and time.monotonic() < deadline:
    app.processEvents()
    time.sleep(0.01)
assert window.project is not None
app.processEvents()
target = ROOT / "docs/images/desktop.png"
target.parent.mkdir(parents=True, exist_ok=True)
assert window.grab().save(str(target))
window.close()
print(target.relative_to(ROOT))
