from bluebell.ui import MainWindow


def test_empty_state_and_vault_chooser(qtbot, sandbox):
    window = MainWindow(restore=False)
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()
    assert window.open_button.text() == "Open vault…"
    vault = sandbox / "Synthetic vault"
    vault.mkdir()
    (vault / "untouched.md").write_bytes(b"# Original\r\n")
    assert window.open_vault(vault)
    assert window.vault_label.text() == "Synthetic vault"
    assert (vault / "untouched.md").read_bytes() == b"# Original\r\n"
