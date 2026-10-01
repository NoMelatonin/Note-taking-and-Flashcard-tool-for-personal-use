from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import QDialog, QMessageBox

from bluebell.ui import MainWindow, NameDialog
from bluebell.document import Document
import pytest


@pytest.mark.parametrize("part", ["chevron", "icon", "label", "empty space"])
def test_entire_folder_row_toggles_and_resets_descendants(qtbot, sandbox, part):
    root = sandbox / "Vault"
    (root / "Parent/Child/Grandchild").mkdir(parents=True)
    (root / "Parent/Child/Grandchild/Note.md").write_text("keep")
    window = MainWindow(restore=False)
    qtbot.addWidget(window)
    window.show()
    window.open_vault(root)
    window.raise_()
    window.activateWindow()
    qtbot.waitUntil(window.isActiveWindow)
    parent = window.items["Parent"]
    child = window.items["Parent/Child"]
    grandchild = window.items["Parent/Child/Grandchild"]
    rect = window.tree.visualItemRect(parent)
    x = {"chevron": rect.left() - 10, "icon": rect.left() + 8,
         "label": rect.left() + 45, "empty space": window.tree.viewport().width() - 8}[part]
    point = QPoint(x, rect.center().y())
    qtbot.mouseClick(window.tree.viewport(), Qt.LeftButton, pos=point)
    assert parent.isExpanded()
    child.setExpanded(True)
    grandchild.setExpanded(True)
    qtbot.mouseClick(window.tree.viewport(), Qt.LeftButton, pos=point)
    assert not parent.isExpanded() and not child.isExpanded() and not grandchild.isExpanded()
    window.refresh_tree()
    parent = window.items["Parent"]
    assert not parent.isExpanded()
    qtbot.mouseClick(window.tree.viewport(), Qt.LeftButton, pos=point)
    assert parent.isExpanded()
    assert not window.items["Parent/Child"].isExpanded()
    assert (root / "Parent/Child/Grandchild/Note.md").read_text() == "keep"


def test_keyboard_parent_collapse_resets_subfolders(qtbot, sandbox):
    root = sandbox / "Vault"
    (root / "Parent/Child/Grandchild").mkdir(parents=True)
    window = MainWindow(restore=False)
    qtbot.addWidget(window)
    window.show()
    window.open_vault(root)
    parent, child = window.items["Parent"], window.items["Parent/Child"]
    parent.setExpanded(True)
    child.setExpanded(True)
    window.tree.setCurrentItem(parent)
    window.tree.setFocus()
    qtbot.keyClick(window.tree, Qt.Key_Left)
    assert not parent.isExpanded() and not child.isExpanded()


def test_dialog_duplicate_and_cancel_preserves_file(qtbot, sandbox):
    vault = sandbox / "Vault"
    vault.mkdir()
    (vault / "Keep.md").write_text("protected")
    window = MainWindow(restore=False)
    qtbot.addWidget(window)
    assert window.open_vault(vault)
    dialog = NameDialog(window, "New note", ".", lambda name: window.vault.create(".", name))
    qtbot.addWidget(dialog)
    dialog.name.setText("KEEP")
    dialog.attempt()
    assert dialog.error.text()
    assert dialog.result_path is None
    assert (vault / "Keep.md").read_text() == "protected"
    dialog.reject()
    assert set(window.items) == {".", "Keep.md"}


def test_real_creation_from_selected_folder_and_note(qtbot, sandbox):
    vault = sandbox / "Vault"
    (vault / "Ideas" / "Nested").mkdir(parents=True)
    (vault / "Ideas" / "Nested" / "One.md").write_text("one")
    window = MainWindow(restore=False)
    qtbot.addWidget(window)
    window.open_vault(vault)
    window.select_path("Ideas/Nested")
    assert window.destination() == "Ideas/Nested"
    def enter_name():
        dialog = window.findChild(NameDialog)
        dialog.name.setText("Grüße")
        dialog.attempt()
    QTimer.singleShot(0, enter_name)
    window.create_entry(False)
    assert (vault / "Ideas/Nested/Grüße.md").exists()
    assert window.active_path == "Ideas/Nested/Grüße.md"
    assert window.destination() == "Ideas/Nested"
    window.tree.setCurrentItem(None)
    assert window.destination() == "."


def test_note_and_folder_rename_updates_active_path(qtbot, sandbox, monkeypatch):
    path = sandbox / "Vault"
    (path / "Old").mkdir(parents=True)
    (path / "Old/One.md").write_text("content")
    window = MainWindow(restore=False)
    qtbot.addWidget(window)
    window.open_vault(path)
    window.open_note("Old/One.md")
    window.select_path("Old")
    def rename():
        dialog = window.findChild(NameDialog)
        dialog.name.setText("New")
        dialog.attempt()
    QTimer.singleShot(0, rename)
    window.rename_entry()
    assert window.active_path == "New/One.md"
    assert (path / "New/One.md").read_text() == "content"
    assert "Old" not in window.items


@pytest.mark.parametrize("action", ["create", "rename", "trash"])
def test_pending_filesystem_target_survives_conflict_copy_selection(qtbot, sandbox, monkeypatch, action):
    root = sandbox / "Vault"
    (root / "Original folder").mkdir(parents=True)
    (root / "Original folder/Child.md").write_text("keep child")
    window = MainWindow(restore=False)
    qtbot.addWidget(window, before_close_func=lambda widget: setattr(widget, "document", None))
    window.open_vault(root)
    window.select_path("Original folder")
    resolved = False
    def resolve_save():
        nonlocal resolved
        if not resolved:
            resolved = True
            copy = window.vault.create(".", "Kept copy", content=b"Keep these saved edits\n")
            window._adopt_document(Document(window.vault, copy))
            window.refresh_tree()
            window.select_path(copy)
        return True
    monkeypatch.setattr(window, "flush_pending", resolve_save)
    def name_entry():
        from PySide6.QtWidgets import QApplication
        dialog = QApplication.activeModalWidget()
        dialog.name.setText("Created")
        dialog.attempt()
    if action == "create":
        QTimer.singleShot(0, name_entry)
        window.create_entry(False)
        assert (root / "Original folder/Created.md").is_file()
        assert not (root / "Created.md").exists()
    elif action == "rename":
        QTimer.singleShot(0, name_entry)
        window.rename_entry()
        assert (root / "Created/Child.md").read_text() == "keep child"
    else:
        calls, prompts = [], []
        monkeypatch.setattr(window.vault, "trash", calls.append)
        def confirm(box):
            prompts.append(box.text())
            return QMessageBox.Yes
        monkeypatch.setattr(QMessageBox, "exec", confirm)
        window.trash_entry()
        assert calls == ["Original folder"]
        assert "Original folder" in prompts[0] and "contents" in prompts[0]
    assert (root / "Kept copy.md").read_bytes() == b"Keep these saved edits\n"
