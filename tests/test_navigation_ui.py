from urllib.parse import quote

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QTextCursor
import pytest

from bluebell.ui import MainWindow


@pytest.fixture
def window(qtbot, sandbox):
    root = sandbox / "Vault"
    (root / "Ideas").mkdir(parents=True)
    (root / "Home.md").write_text("# Home\n\n[[Ideas/Thought|Go]] [Next](Ideas/Thought.md)\n")
    (root / "Ideas" / "Thought.md").write_text("# Thought\n\nA small beginning. [[Home]]\n")
    (root / "100% real.md").write_text("# Percent\n")
    window = MainWindow(restore=False)
    qtbot.addWidget(window, before_close_func=lambda widget: setattr(widget, "document", None))
    window.show()
    window.open_vault(root)
    window.open_note("Home.md")
    return window


def test_search_results_and_literal_navigation(qtbot, window):
    window.search_text.setText("SMALL")
    qtbot.waitUntil(lambda: window.search_results.count() == 1, timeout=2000)
    item = window.search_results.item(0)
    assert item.data(Qt.UserRole) == "Ideas/Thought.md"
    assert "small beginning" in item.text()
    window.open_search_result(item)
    assert window.active_path == "Ideas/Thought.md"
    window.search_text.clear()
    assert window.explorer_views.currentWidget() is window.tree


def test_reading_and_source_links_flush_changes_and_keep_mode(qtbot, window):
    window.editor.moveCursor(QTextCursor.End)
    window.editor.insertPlainText("Local addition\n")
    window.set_mode("read")
    window.preview_link(QUrl("bluebell-wiki:" + quote("Ideas/Thought", safe="")))
    assert window.active_path == "Ideas/Thought.md" and window.mode == "read"
    assert (window.vault.root / "Home.md").read_text().endswith("Local addition\n")
    window.preview_link(QUrl("bluebell-note:" + quote("../Home.md", safe="")))
    assert window.active_path == "Home.md"
    window.source_link("100% real", True)
    assert window.active_path == "100% real.md"


def test_missing_ambiguous_and_external_click_handling(qtbot, window, monkeypatch):
    messages, calls = [], []
    monkeypatch.setattr(window, "show_error", lambda title, error: messages.append(str(error)))
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: calls.append(url.toString()) or True)
    window.set_mode("read")
    assert not calls  # Rendering itself never launches the browser.
    assert not window.navigate_link("Missing", wiki=True)
    assert "No note" in messages[-1]
    (window.vault.root / "Thought.md").write_text("duplicate")
    window.refresh_tree()
    assert not window.navigate_link("Thought", wiki=True)
    assert "ambiguous" in messages[-1]
    window.preview_link(QUrl("https://example.invalid/explicit-click"))
    assert calls == ["https://example.invalid/explicit-click"]
    window.preview_link(QUrl("file:///etc/passwd"))
    window.source_link("javascript:alert(1)", False)
    assert len(calls) == 1


def test_external_creation_rename_removal_and_current_conflict(qtbot, window):
    path = window.vault.root
    (path / "New.md").write_text("External addition\n")
    qtbot.waitUntil(lambda: "New.md" in window.items, timeout=1500)
    (path / "New.md").rename(path / "Renamed.md")
    qtbot.waitUntil(lambda: "Renamed.md" in window.items and "New.md" not in window.items, timeout=1500)
    (path / "Renamed.md").unlink()
    qtbot.waitUntil(lambda: "Renamed.md" not in window.items, timeout=1500)
    window.editor.moveCursor(QTextCursor.End)
    window.editor.insertPlainText("Local\n")
    (path / "Home.md").write_text("External\n")
    qtbot.waitUntil(lambda: window.document.conflict, timeout=1500)
    assert "Local" in window.editor.toPlainText()
    assert (path / "Home.md").read_text() == "External\n"


def test_external_content_reloads_clean_current_note(qtbot, window):
    (window.vault.root / "Home.md").write_text("Changed outside\n")
    qtbot.waitUntil(lambda: window.editor.toPlainText() == "Changed outside\n", timeout=1500)


def test_old_vault_scan_is_ignored_after_switch(qtbot, window, sandbox):
    other = sandbox / "Other vault"
    other.mkdir()
    (other / "Other.md").write_text("Other")
    window.tick()
    assert window.open_vault(other)
    qtbot.waitUntil(lambda: not window.jobs, timeout=2000)
    assert set(window.items) == {".", "Other.md"}


def test_percent_encoded_image_and_link_names(qtbot, window):
    window.preview_link(QUrl("bluebell-wiki:" + quote("100% real", safe="")))
    assert window.active_path == "100% real.md"


def test_actual_reading_click_and_source_control_click(qtbot, window):
    window.set_mode("read")
    cursor = window.preview.document().find("Go")
    cursor.setPosition(cursor.selectionStart() + 1)
    point = window.preview.cursorRect(cursor).center()
    assert window.preview.anchorAt(point).startswith("bluebell-wiki:")
    qtbot.mouseClick(window.preview.viewport(), Qt.LeftButton, pos=point)
    assert window.active_path == "Ideas/Thought.md"
    window.open_note("Home.md")
    window.set_mode("edit")
    cursor = window.editor.textCursor()
    cursor.setPosition(window.editor.toPlainText().index("[[") + 4)
    window.editor.setTextCursor(cursor)
    point = window.editor.cursorRect(cursor).center()
    qtbot.mouseClick(window.editor.viewport(), Qt.LeftButton, Qt.ControlModifier, point)
    assert window.active_path == "Ideas/Thought.md"
