import os
from pathlib import Path
import stat

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QImage, QPalette, QTextCursor, QTextDocument
from PySide6.QtWidgets import QFileDialog, QFrame, QPushButton
import pytest

from bluebell.editor import MarkdownEditor
from bluebell.settings import load_settings, save_settings, settings_path
from bluebell.ui import MainWindow
from bluebell.vault import MAX_NOTE_BYTES, Vault, VaultError


@pytest.fixture
def window(qtbot, sandbox):
    root = sandbox / "Vault"
    root.mkdir()
    (root / "Note.md").write_text("# Note\n\nA thought\n")
    window = MainWindow(restore=False)
    qtbot.addWidget(window, before_close_func=lambda widget: setattr(widget, "document", None))
    window.show()
    window.raise_()
    window.activateWindow()
    window.open_vault(root)
    window.open_note("Note.md")
    qtbot.waitUntil(lambda: window.isActiveWindow())
    return window


def test_standard_shortcuts_and_source_undo_redo(qtbot, window, monkeypatch):
    cursor = window.editor.document().find("thought")
    window.editor.setTextCursor(cursor)
    window.editor.setFocus()
    qtbot.keyClick(window.editor, Qt.Key_B, Qt.ControlModifier)
    assert "**thought**" in window.editor.toPlainText()
    qtbot.keyClick(window.editor, Qt.Key_I, Qt.ControlModifier)
    assert "***thought***" in window.editor.toPlainText()
    qtbot.keyClick(window.editor, Qt.Key_Z, Qt.ControlModifier)
    assert "***thought***" not in window.editor.toPlainText()
    qtbot.keyClick(window.editor, Qt.Key_Z, Qt.ControlModifier)
    assert "**thought**" not in window.editor.toPlainText()
    qtbot.keyClick(window.editor, Qt.Key_Z, Qt.ControlModifier | Qt.ShiftModifier)
    assert "**thought**" in window.editor.toPlainText()
    qtbot.keyClick(window.editor, Qt.Key_S, Qt.ControlModifier)
    assert window.save_state.text() == "Saved"
    assert "**thought**" in (window.vault.root / "Note.md").read_text()
    qtbot.keyClick(window.editor, Qt.Key_E, Qt.ControlModifier)
    assert window.mode == "read"
    qtbot.keyClick(window.preview, Qt.Key_F, Qt.ControlModifier)
    assert window.findbar.isVisible()
    qtbot.keyClick(window.find_text, Qt.Key_F, Qt.ControlModifier | Qt.ShiftModifier)
    assert window.search_text.hasFocus()
    calls = []
    monkeypatch.setattr(window, "create_entry", lambda folder=False: calls.append(folder))
    qtbot.keyClick(window.search_text, Qt.Key_N, Qt.ControlModifier)
    assert calls == [False]


def test_tab_moves_focus_on_plain_text(qtbot, window):
    window.editor.setFocus()
    qtbot.waitUntil(window.editor.hasFocus)
    qtbot.keyClick(window.editor, Qt.Key_Tab)
    assert not window.editor.hasFocus()


def test_zoom_resize_and_remembered_size(qtbot, window):
    window.resize(860, 600)
    window.splitter.setSizes([280, 580])
    assert window.editor.width() > 300
    assert window.new_note_button.isVisible() and window.save_button.isVisible()
    assert window.search_text.palette().color(QPalette.PlaceholderText).name() == "#496070"
    assert window.search_text.palette().color(QPalette.PlaceholderText).alpha() == 255
    original = window.font_size
    window.zoom(1)
    assert window.font_size == original + 1
    assert load_settings()["font_size"] == original + 1
    window.set_mode("read")
    assert f"font-size: {window.font_size}px" in window.preview.document().defaultStyleSheet()
    reopened = MainWindow(restore=False)
    qtbot.addWidget(reopened)
    assert reopened.font_size == window.font_size


def test_writing_surface_and_explorer_are_frameless(window):
    for widget in (window.editor, window.preview, window.tree, window.search_results):
        assert widget.frameShape() == QFrame.NoFrame
    assert not any(button.isVisible() for button in window.pages.findChildren(QPushButton))
    assert not hasattr(window, "zoom_in_button")


def test_workspace_search_sidebar_and_tab_controls(qtbot, window):
    assert not window.search_container.isVisible()
    window.toggle_sidebar()
    assert not window.sidebar.isVisible()
    window.focus_search()
    assert window.sidebar.isVisible() and window.search_container.isVisible()
    assert window.search_text.hasFocus()
    window.search_text.setText("thought")
    window.show_files()
    assert window.search_text.text() == ""
    assert not window.search_container.isVisible()
    assert window.tab_label.text() == "Note"
    assert window.note_heading.text() == "Note"
    window.editor.appendPlainText("Saved when the tab closes")
    qtbot.mouseClick(window.close_note_button, Qt.LeftButton)
    assert window.document is None and window.pages.currentIndex() == 0
    assert "Saved when the tab closes" in (window.vault.root / "Note.md").read_text()
    assert window.note_heading.text() == ""
    assert window.open_note("Note.md")
    qtbot.mouseClick(window.mode_button, Qt.LeftButton)
    assert window.mode == "read"
    qtbot.mouseClick(window.mode_button, Qt.LeftButton)
    assert window.mode == "edit"


def test_cancelled_tab_close_preserves_editor_and_title(window, monkeypatch):
    window.editor.appendPlainText("Keep these edits")
    monkeypatch.setattr(window, "flush_pending", lambda: False)
    assert not window.close_note()
    assert window.active_path == "Note.md"
    assert window.tab_label.text() == "Note"
    assert "Keep these edits" in window.editor.toPlainText()


def test_chooser_button_cancellation_and_missing_restore(qtbot, sandbox, monkeypatch):
    window = MainWindow(restore=False)
    qtbot.addWidget(window)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: "")
    qtbot.mouseClick(window.open_button, Qt.LeftButton)
    assert window.vault is None
    root = sandbox / "Vault"
    root.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: str(root))
    qtbot.mouseClick(window.open_button, Qt.LeftButton)
    assert window.vault.root == root
    root.rmdir()
    restored = MainWindow()
    qtbot.addWidget(restored)
    assert restored.vault is None and "unavailable" in restored.empty_hint.text()


def test_private_settings_permissions_and_symlink_preservation(sandbox):
    save_settings({"font_size": 16})
    assert stat.S_IMODE(settings_path().stat().st_mode) == 0o600
    original = sandbox / "Unrelated.json"
    original.write_text('{"keep": true}')
    settings_path().unlink()
    settings_path().symlink_to(original)
    assert load_settings() == {}
    with pytest.raises(OSError, match="symbolic link"):
        save_settings({"overwrite": True})
    assert original.read_text() == '{"keep": true}'


def test_emoji_selection_and_link_click(qtbot):
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("🙂 thought")
    editor.selectAll()
    editor.wrap_selection("**")
    assert editor.toPlainText() == "**🙂 thought**"
    assert editor.textCursor().selectedText() == "🙂 thought"
    editor.setPlainText("🙂 [[Note]]")
    editor.show()
    cursor = editor.document().find("Note")
    cursor.setPosition(cursor.selectionStart() + 1)
    point = editor.cursorRect(cursor).center()
    calls = []
    editor.linkRequested.connect(lambda target, wiki: calls.append((target, wiki)))
    qtbot.mouseClick(editor.viewport(), Qt.LeftButton, Qt.ControlModifier, point)
    assert calls == [("Note", True)]


def test_oversized_notes_fail_without_filesystem_change(sandbox):
    root = sandbox / "Vault"
    root.mkdir()
    vault = Vault(root)
    with pytest.raises(VaultError, match="8 MiB"):
        vault.create(".", "Oversized", content=b"x" * (MAX_NOTE_BYTES + 1))
    assert not list(root.iterdir())
    (root / "Oversized.md").write_bytes(b"x" * (MAX_NOTE_BYTES + 1))
    with pytest.raises(VaultError, match="8 MiB"):
        vault.read("Oversized.md")
    assert (root / "Oversized.md").stat().st_size == MAX_NOTE_BYTES + 1


def test_percent_unicode_image_names(qtbot, window):
    image = QImage(8, 8, QImage.Format_RGB32)
    image.fill(0x416881)
    name = "Grüße 100%.png"
    image.save(str(window.vault.root / name))
    window.preview.show_markdown("![local](Gr%C3%BC%C3%9Fe%20100%25.png)", window.vault, "Note.md")
    from urllib.parse import quote
    resource = window.preview.document().resource(QTextDocument.ImageResource, QUrl("vault-image:" + quote(name, safe="")))
    assert isinstance(resource, QImage) and not resource.isNull()
