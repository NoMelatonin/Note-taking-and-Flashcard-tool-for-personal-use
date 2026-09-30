from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QMessageBox

from bluebell.ui import MainWindow, NameDialog


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
