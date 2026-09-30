"""Launch the real native window and retain a repository-local QA image."""

from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from bluebell.ui import MainWindow
from make_demo_vault import create_demo_vault

root = Path(__file__).resolve().parents[1]
(root / "work").mkdir(exist_ok=True)
app = QApplication([])
window = MainWindow(restore=False)
window.show()


def verify():
    assert window.isVisible()
    print(f"Native GUI platform: {app.platformName()}", flush=True)
    assert window.grab().save(str(root / "work" / "empty-state.png"))
    assert window.open_vault(create_demo_vault())
    assert window.open_note("Welcome.md")
    app.processEvents()
    assert window.grab().save(str(root / "work" / "explorer.png"))
    window.set_mode("read")
    app.processEvents()
    assert window.grab().save(str(root / "work" / "reading.png"))
    window.preview.verticalScrollBar().setValue(window.preview.verticalScrollBar().maximum())
    app.processEvents()
    assert window.grab().save(str(root / "work" / "reading-image.png"))
    window.close()
    app.quit()


QTimer.singleShot(1000, verify)
app.exec()
