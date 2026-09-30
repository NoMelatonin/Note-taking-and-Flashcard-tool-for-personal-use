import pytest
from PySide6.QtCore import QTimer
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QMessageBox

from bluebell.ui import MainWindow, NameDialog


@pytest.fixture
def window(qtbot, sandbox):
    path = sandbox / "Vault"
    path.mkdir()
    (path / "One.md").write_bytes(b"# One\r\n")
    (path / "Two.md").write_text("# Two\n")
    window = MainWindow(restore=False)
    qtbot.addWidget(window, before_close_func=lambda widget: setattr(widget, "document", None))
    window.show()
    window.open_vault(path)
    window.open_note("One.md")
    yield window
    window.document = None  # Failure tests intentionally keep unsaved editor text.


def append(window, text):
    window.editor.moveCursor(QTextCursor.End)
    window.editor.insertPlainText(text)


def test_idle_autosave_and_switch_flush(qtbot, window):
    path = window.vault.root / "One.md"
    append(window, "First edit\n")
    assert window.save_state.text() == "Unsaved"
    qtbot.waitUntil(lambda: window.save_state.text() == "Saved", timeout=1800)
    assert path.read_bytes() == b"# One\r\nFirst edit\r\n"
    append(window, "Switch edit\n")
    assert window.open_note("Two.md")
    assert path.read_bytes().endswith(b"Switch edit\r\n")


def test_close_flush_and_restart_restore(qtbot, window, sandbox):
    append(window, "At close\n")
    window.close()
    assert (window.vault.root / "One.md").read_bytes().endswith(b"At close\r\n")
    reopened = MainWindow()
    qtbot.addWidget(reopened)
    assert reopened.vault.root == window.vault.root
    reopened.open_note("One.md")
    assert "At close" in reopened.editor.toPlainText()


def test_conflict_copy_ui_preserves_both_versions(qtbot, window):
    path = window.vault.root / "One.md"
    append(window, "Local\n")
    path.write_text("External\n")
    assert not window.save_document()
    assert window.notice.isVisible()
    assert window.document.conflict
    def choose_copy():
        dialog = window.findChild(NameDialog)
        dialog.name.setText("My conflict copy")
        dialog.attempt()
    QTimer.singleShot(0, choose_copy)
    assert window.save_copy()
    assert path.read_text() == "External\n"
    assert (window.vault.root / "My conflict copy.md").read_bytes() == b"# One\r\nLocal\r\n"
    assert window.save_state.text() == "Saved"


def test_write_failure_retains_text_and_cancelled_switch(qtbot, window, monkeypatch):
    append(window, "Unsaved\n")
    original = (window.vault.root / "One.md").read_bytes()
    def fail(*args):
        raise OSError("synthetic disk full")
    monkeypatch.setattr(window.vault, "atomic_write", fail)
    assert not window.save_document()
    assert window.save_state.text() == "Save failed"
    assert "Unsaved" in window.editor.toPlainText()
    monkeypatch.setattr(QMessageBox, "exec", lambda self: QMessageBox.Cancel)
    assert not window.open_note("Two.md")
    assert window.active_path == "One.md"
    assert "Unsaved" in window.editor.toPlainText()
    assert (window.vault.root / "One.md").read_bytes() == original
    window.close()
    assert window.isVisible()  # The failed close is refused.


def test_removed_note_offers_copy_without_recreating(qtbot, window):
    append(window, "Keep this\n")
    (window.vault.root / "One.md").unlink()
    window.check_external()
    assert window.document.missing and not window.reload_button.isEnabled()
    assert "Keep this" in window.editor.toPlainText()
    assert not window.save_document()
    assert not (window.vault.root / "One.md").exists()


def test_read_find_and_exact_source_open(qtbot, window):
    before = (window.vault.root / "One.md").stat().st_mtime_ns
    window.set_mode("read")
    assert window.views.currentWidget() is window.preview
    assert "One" in window.preview.toPlainText()
    window.show_find()
    window.find_text.setText("one")
    assert window.preview.textCursor().selectedText() == "One"
    window.set_mode("edit")
    assert window.editor.toPlainText() == "# One\n"
    assert (window.vault.root / "One.md").stat().st_mtime_ns == before
