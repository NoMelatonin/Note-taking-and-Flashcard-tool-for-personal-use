from pathlib import Path
import os

import pytest

from bluebell.vault import Vault, VaultError, validate_name


@pytest.fixture
def vault(sandbox):
    path = sandbox / "Synthetic vault"
    path.mkdir()
    return Vault(path)


def test_open_scan_preserves_all_files(vault):
    originals = {"Note.md": b"# Keep\r\n", "image.png": b"image", "data.bin": b"\x00\x01"}
    for name, content in originals.items():
        (vault.root / name).write_bytes(content)
    (vault.root / ".git").mkdir()
    (vault.root / ".git" / "hidden.md").write_text("hidden")
    assert [entry.path for entry in vault.scan().entries] == ["Note.md"]
    for name, content in originals.items():
        assert (vault.root / name).read_bytes() == content


def test_nested_unicode_creation_and_no_overwrite(vault):
    first = vault.create(".", "Ideas", folder=True)
    second = vault.create(first, "Grüße 日本", folder=True)
    note = vault.create(second, "My note.MD")
    assert note == "Ideas/Grüße 日本/My note.MD"
    assert (vault.root / note).is_file()
    (vault.root / note).write_text("keep me")
    with pytest.raises(VaultError, match="already exists"):
        vault.create(second, "my NOTE.md")
    assert (vault.root / note).read_text() == "keep me"


@pytest.mark.parametrize("name", ["", " ", ".", "..", "../escape", "folder/note", "a\\b", "CON", "nul.txt", "COM1", "LPT²", "trail.", "trail ", "a:b", "a\x00b", ".git"])
def test_invalid_entry_names(name):
    with pytest.raises(VaultError):
        validate_name(name, note=True)


def test_rename_folder_and_note_preserves_contents(vault):
    folder = vault.create(".", "Drafts", folder=True)
    note = vault.create(folder, "One", content=b"# Content\r\n")
    renamed_note = vault.rename(note, "Two")
    renamed_folder = vault.rename(folder, "Writing")
    assert renamed_note == "Drafts/Two.md"
    assert renamed_folder == "Writing"
    assert (vault.root / "Writing/Two.md").read_bytes() == b"# Content\r\n"
    vault.create("Writing", "other", content=b"protected")
    with pytest.raises(VaultError):
        vault.rename("Writing/Two.md", "OTHER")
    assert (vault.root / "Writing/other.md").read_bytes() == b"protected"


def test_symlink_and_traversal_rejected(vault, sandbox):
    outside = sandbox / "Outside"
    outside.mkdir()
    (outside / "secret.md").write_text("do not touch")
    (vault.root / "escape").symlink_to(outside, target_is_directory=True)
    (vault.root / "alias.md").symlink_to(outside / "secret.md")
    assert not vault.scan().entries
    for relative in ("escape/secret.md", "alias.md", "../Outside/secret.md", "/etc/passwd"):
        with pytest.raises(VaultError):
            vault.read(relative)
    with pytest.raises(VaultError):
        vault.create("escape", "new")
    with pytest.raises(VaultError):
        vault.rename("alias.md", "new")
    with pytest.raises(VaultError):
        vault.trash("alias.md")
    assert (outside / "secret.md").read_text() == "do not touch"


def test_failed_create_has_no_phantom(vault, monkeypatch):
    def fail(*args):
        raise OSError("synthetic disk failure")
    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(OSError):
        vault.create(".", "New", content=b"incomplete")
    assert not (vault.root / "New.md").exists()


def test_trash_failure_keeps_original(vault, monkeypatch):
    path = vault.create(".", "Keep", content=b"keep")
    def fail(*args):
        raise OSError("synthetic unavailable Trash")
    monkeypatch.setattr("bluebell.vault.send2trash", fail)
    with pytest.raises(OSError):
        vault.trash(path)
    assert (vault.root / path).read_bytes() == b"keep"


def test_trash_invokes_os_backend_only(vault, monkeypatch):
    path = vault.create(".", "Trash me")
    calls = []
    monkeypatch.setattr("bluebell.vault.send2trash", calls.append)
    vault.trash(path)
    assert calls == [str(vault.root / path)]


def test_root_replacement_blocks_access(vault, sandbox):
    vault.root.rename(sandbox / "Moved vault")
    vault.root.mkdir()
    with pytest.raises(VaultError, match="moved or changed"):
        vault.create(".", "Wrong vault")
