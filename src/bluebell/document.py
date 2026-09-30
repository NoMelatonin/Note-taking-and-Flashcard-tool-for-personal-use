"""Document text, safe saving and explicit conflict state, independent of Qt."""

import codecs
from difflib import SequenceMatcher
import re

from bluebell.vault import ConflictError, Snapshot, Vault, VaultError


def normalise_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


class Document:
    def __init__(self, vault: Vault, relative: str):
        self.vault = vault
        self.relative = relative
        self.conflict = False
        self.missing = False
        self.error = ""
        self._load(vault.read(relative))

    def _load(self, snapshot: Snapshot):
        original = snapshot.data.decode("utf-8-sig")
        self.snapshot = snapshot
        self.bom = snapshot.data.startswith(codecs.BOM_UTF8)
        self.original = original
        self.baseline = normalise_newlines(self.original)
        self.text = self.baseline
        matches = re.findall(r"\r\n|\r|\n", self.original)
        self.newline = max(set(matches), key=lambda value: (matches.count(value), value == "\r\n")) if matches else "\n"
        self.conflict = self.missing = False
        self.error = ""

    @property
    def dirty(self):
        return self.text != self.baseline

    @property
    def paused(self):
        return self.conflict or self.missing or bool(self.error)

    def encoded(self) -> bytes:
        # Retain exact line endings on unchanged lines, even in mixed-newline notes.
        old_lines = self.original.splitlines(keepends=True)
        old_normal = [normalise_newlines(line) for line in old_lines]
        new_lines = self.text.splitlines(keepends=True)
        output = []
        matcher = SequenceMatcher(None, old_normal, new_lines)
        for tag, start, end, new_start, new_end in matcher.get_opcodes():
            if tag == "equal":
                output.extend(old_lines[start:end])
            else:
                output.extend(line.replace("\n", self.newline) for line in new_lines[new_start:new_end])
        data = "".join(output).encode("utf-8")
        return (codecs.BOM_UTF8 if self.bom else b"") + data

    def save(self):
        if self.conflict:
            raise ConflictError("Autosave is paused because the disk version changed.")
        if self.missing:
            raise FileNotFoundError("The original note is gone. Save a copy inside the vault.")
        if not self.dirty:
            return
        try:
            snapshot = self.vault.atomic_write(self.relative, self.encoded(), self.snapshot)
        except ConflictError:
            self.conflict = True
            raise
        except FileNotFoundError:
            self.missing = True
            raise
        except (OSError, VaultError) as error:
            self.error = str(error)
            raise
        self._load(snapshot)

    def check_external(self) -> str | None:
        if self.conflict or self.missing:
            return None
        try:
            latest = self.vault.read(self.relative)
        except FileNotFoundError:
            self.missing = True
            return "missing"
        except (OSError, VaultError) as error:
            self.error = str(error)
            return "error"
        if latest.version == self.snapshot.version:
            return None
        if self.dirty:
            self.conflict = True
            return "conflict"
        try:
            self._load(latest)
        except UnicodeError as error:
            self.error = "The external version is not valid UTF-8. Your displayed text is retained."
            return "error"
        return "reloaded"

    def reload(self):
        snapshot = self.vault.read(self.relative)
        snapshot.data.decode("utf-8-sig")  # Validate before replacing any editor state.
        self._load(snapshot)
