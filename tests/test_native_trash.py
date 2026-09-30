"""Opt-in: exercise macOS Trash using uniquely named synthetic files only."""

import os
from pathlib import Path
import sys
import uuid

import pytest

from bluebell.vault import Vault


@pytest.mark.skipif(os.environ.get("BLUEBELL_TEST_NATIVE_TRASH") != "1" or sys.platform != "darwin", reason="Opt-in native macOS Trash integration")
def test_native_trash_folder_is_recoverable(sandbox):
    root = sandbox / "Vault"
    root.mkdir()
    vault = Vault(root)
    name = "bluebell-synthetic-" + uuid.uuid4().hex
    folder = vault.create(".", name, folder=True)
    vault.create(folder, "Synthetic", content=b"Synthetic Trash integration fixture\n")
    vault.trash(folder)
    assert not (root / name).exists()
    trashed = Path.home() / ".Trash" / name / "Synthetic.md"
    assert trashed.read_bytes() == b"Synthetic Trash integration fixture\n"
