"""Launch the real native window and retain a repository-local QA image."""

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from bluebell.ui import MainWindow

root = Path(__file__).resolve().parents[1]
(root / "work").mkdir(exist_ok=True)
app = QApplication([])
window = MainWindow(restore=False)
window.show()


def verify():
    assert window.isVisible()
    print(f"Native GUI platform: {app.platformName()}", flush=True)
    assert window.grab().save(str(root / "work" / "empty-state.png"))
    window.close()
    app.quit()


QTimer.singleShot(1000, verify)
app.exec()
