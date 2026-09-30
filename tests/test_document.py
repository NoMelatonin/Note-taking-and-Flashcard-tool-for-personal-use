import codecs
import os
import stat

import pytest

from bluebell.document import Document
from bluebell.vault import ConflictError, Vault, VaultError


@pytest.fixture
def document(sandbox):
    root = sandbox / "Vault"
    root.mkdir()
    (root / "Note.md").write_bytes(b"# Original\r\n\r\nA thought.\r\n")
    return Document(Vault(root), "Note.md")


def test_open_and_clean_save_are_byte_and_stat_preserving(document):
    path = document.vault.root / document.relative
    before = path.stat()
    original = path.read_bytes()
    document.save()
    assert path.read_bytes() == original
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    assert path.stat().st_ino == before.st_ino


def test_atomic_save_retains_newlines_permissions_and_no_temporary_files(document):
    path = document.vault.root / document.relative
    path.chmod(0o640)
    document.reload()
    document.text += "More.\n"
    document.save()
    assert path.read_bytes() == b"# Original\r\n\r\nA thought.\r\nMore.\r\n"
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert not document.dirty
    assert not list(document.vault.root.glob(".bluebell-*.tmp"))


@pytest.mark.parametrize("data", [codecs.BOM_UTF8 + b"a\r\nb\r\n", b"a\nb\r\nc\rd\n", b"No trailing newline"])
def test_bom_mixed_and_missing_final_newlines(document, data):
    path = document.vault.root / document.relative
    path.write_bytes(data)
    document.reload()
    document.text = document.text.replace("a", "A", 1) if b"\r" in data else document.text + "!"
    document.save()
    result = path.read_bytes()
    if data.startswith(codecs.BOM_UTF8):
        assert result.startswith(codecs.BOM_UTF8)
        assert result.endswith(b"b\r\n")
    elif b"\r" in data:
        assert result.endswith(b"b\r\nc\rd\n")
    else:
        assert result == data + b"!"


def test_conflict_detects_changed_bytes_even_with_same_mtime(document):
    path = document.vault.root / document.relative
    original_stat = path.stat()
    document.text = "Local unsaved\n"
    path.write_bytes(b"# External\r\n\r\nA thought.\r\n")
    os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    with pytest.raises(ConflictError):
        document.save()
    assert document.conflict
    assert document.text == "Local unsaved\n"
    assert b"External" in path.read_bytes()
    copy = document.vault.create(".", "Conflict copy", content=document.encoded())
    assert (document.vault.root / copy).read_bytes() == b"Local unsaved\r\n"
    assert b"External" in path.read_bytes()


def test_failure_and_second_version_check_preserve_original(document, monkeypatch):
    path = document.vault.root / document.relative
    original = path.read_bytes()
    document.text = "Unsaved\n"
    def fail(*args, **kwargs):
        raise PermissionError("synthetic denied write")
    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(PermissionError):
        document.save()
    assert document.dirty and document.error
    assert document.text == "Unsaved\n"
    assert path.read_bytes() == original
    assert not list(document.vault.root.glob(".bluebell-*.tmp"))


def test_external_write_while_staging_blocks_replace(document, monkeypatch):
    path = document.vault.root / document.relative
    document.text = "Local\n"
    original_fsync = os.fsync
    changed = False
    def edit_during_fsync(descriptor):
        nonlocal changed
        original_fsync(descriptor)
        if not changed:
            changed = True
            path.write_text("External during save\n")
    monkeypatch.setattr(os, "fsync", edit_during_fsync)
    with pytest.raises(ConflictError):
        document.save()
    assert path.read_text() == "External during save\n"
    assert not list(document.vault.root.glob(".bluebell-*.tmp"))


def test_removed_note_never_silently_recreated(document):
    path = document.vault.root / document.relative
    document.text = "Keep my text\n"
    path.unlink()
    assert document.check_external() == "missing"
    with pytest.raises(FileNotFoundError):
        document.save()
    assert not path.exists()
    assert document.text == "Keep my text\n"


def test_clean_external_change_reload_and_invalid_utf8_retains_state(document):
    path = document.vault.root / document.relative
    path.write_text("Fresh from outside\n")
    assert document.check_external() == "reloaded"
    assert document.text == "Fresh from outside\n"
    baseline = document.snapshot
    path.write_bytes(b"\xffinvalid")
    assert document.check_external() == "error"
    assert document.text == "Fresh from outside\n"
    assert document.snapshot == baseline


def test_save_refuses_replaced_symlink(document, sandbox):
    path = document.vault.root / document.relative
    outside = sandbox / "Outside.md"
    outside.write_text("private synthetic\n")
    path.unlink()
    path.symlink_to(outside)
    document.text = "local\n"
    with pytest.raises(VaultError):
        document.save()
    assert outside.read_text() == "private synthetic\n"
