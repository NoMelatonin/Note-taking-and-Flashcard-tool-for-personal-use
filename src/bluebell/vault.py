"""Vault boundary and real filesystem operations. No database stores note text."""

from contextlib import contextmanager
from dataclasses import dataclass
import ctypes
import errno
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import unicodedata

from send2trash import send2trash

MAX_NOTE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024


class VaultError(ValueError):
    """An unsafe path or an action the vault cannot complete."""


class ConflictError(VaultError):
    """Disk version changed since the document was loaded."""


@dataclass(frozen=True)
class Entry:
    path: str
    folder: bool


@dataclass(frozen=True)
class Scan:
    entries: tuple[Entry, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class Snapshot:
    data: bytes
    digest: str
    device: int
    inode: int
    mtime: int
    mode: int
    links: int

    @property
    def version(self):
        return (self.digest, self.device, self.inode, self.mtime)


def name_key(name: str) -> str:
    return unicodedata.normalize("NFC", name).casefold()


def validate_name(name: str, *, note: bool = False) -> str:
    if not name or not name.strip() or name in {".", ".."}:
        raise VaultError("Enter a name, not '.' or '..'.")
    if any(ord(char) < 32 or ord(char) == 127 for char in name) or re.search(r'[<>:"/\\|?*]', name):
        raise VaultError("Use one name without separators, control characters or <>:\"|?*.")
    if name.endswith((" ", ".")):
        raise VaultError("Names cannot end with a space or dot.")
    if name.startswith("."):
        raise VaultError("Use a visible name; names beginning with a dot are reserved.")
    base = name.split(".", 1)[0].upper()
    if base in {"CON", "PRN", "AUX", "NUL"} or re.fullmatch(r"(?:COM|LPT)[1-9¹²³]", base):
        raise VaultError("That name is reserved by the operating system.")
    if note and not name.lower().endswith(".md"):
        name += ".md"
    if len(os.fsencode(name)) > 255:
        raise VaultError("That name is too long for a filesystem entry.")
    return name


class Vault:
    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)
        info = self.root.stat()
        if not stat.S_ISDIR(info.st_mode):
            raise VaultError("Choose an existing folder as your vault.")
        self.identity = (info.st_dev, info.st_ino)
        self.use_dir_fd = os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW")

    def _relative(self, relative: str) -> PurePosixPath:
        if "\\" in relative or ":" in relative or "\0" in relative:
            raise VaultError("Unsafe vault path.")
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts:
            raise VaultError("The path must stay inside the selected vault.")
        return path

    def _check_root(self):
        info = self.root.lstat()
        if stat.S_ISLNK(info.st_mode) or (info.st_dev, info.st_ino) != self.identity:
            raise VaultError("The vault folder moved or changed. Reopen it before continuing.")

    def resolve(self, relative: str, *, must_exist: bool = True) -> Path:
        """Validate every component; never browse or operate on symlinks."""
        parts = self._relative(relative).parts
        self._check_root()
        current = self.root
        for index, part in enumerate(parts):
            current /= part
            try:
                info = current.lstat()
            except FileNotFoundError:
                if not must_exist and index == len(parts) - 1:
                    return current
                raise
            if stat.S_ISLNK(info.st_mode):
                raise VaultError("Symbolic links are not opened or modified by Bluebell.")
            if index < len(parts) - 1 and not stat.S_ISDIR(info.st_mode):
                raise VaultError("A parent path is not a folder.")
        return current

    @contextmanager
    def directory(self, relative: str):
        """POSIX descriptors keep intermediate symlink swaps out of file operations."""
        path = self.resolve(relative)
        if not path.is_dir():
            raise VaultError("The destination folder is unavailable.")
        if not self.use_dir_fd:
            yield None, path
            return
        descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            info = os.fstat(descriptor)
            if (info.st_dev, info.st_ino) != self.identity:
                raise VaultError("The vault folder changed. Reopen it.")
            for part in self._relative(relative).parts:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            yield descriptor, path
        finally:
            os.close(descriptor)

    def _collision(self, directory: int | None, path: Path, name: str, *, exclude: str | None = None):
        names = os.listdir(directory if directory is not None else path)
        if any(item != exclude and name_key(item) == name_key(name) for item in names):
            raise VaultError("An entry with that name already exists (including letter-case variants).")

    def scan(self) -> Scan:
        self._check_root()
        entries, warnings = [], []
        pending = ["."]
        while pending:
            relative = pending.pop()
            try:
                with self.directory(relative) as (descriptor, path):
                    with os.scandir(descriptor if descriptor is not None else path) as items:
                        for item in items:
                            child = str(PurePosixPath(relative) / item.name)
                            if item.is_symlink():
                                warnings.append(f"Skipped symlink: {child}")
                            elif item.is_dir(follow_symlinks=False):
                                if not item.name.startswith("."):
                                    entries.append(Entry(child, True))
                                    pending.append(child)
                            elif item.is_file(follow_symlinks=False) and item.name.lower().endswith(".md"):
                                entries.append(Entry(child, False))
            except OSError as error:
                if relative == ".":
                    raise
                warnings.append(f"Cannot read folder {relative}: {error.strerror or 'filesystem error'}")
            except VaultError as error:
                warnings.append(f"Cannot read folder {relative}: {error}")
        return Scan(tuple(sorted(entries, key=lambda entry: (entry.path.count('/'), not entry.folder, name_key(entry.path)))), tuple(warnings))

    def create(self, parent: str, name: str, *, folder: bool = False, content: bytes = b"") -> str:
        name = validate_name(name, note=not folder)
        relative = str(self._relative(parent) / name)
        with self.directory(parent) as (descriptor, path):
            self._collision(descriptor, path, name)
            if folder:
                os.mkdir(name, dir_fd=descriptor) if descriptor is not None else (path / name).mkdir()
            else:
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
                handle = os.open(name, flags, 0o666, dir_fd=descriptor) if descriptor is not None else os.open(path / name, flags, 0o666)
                try:
                    with os.fdopen(handle, "wb") as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                except BaseException:
                    if descriptor is not None:
                        os.unlink(name, dir_fd=descriptor)
                    else:
                        (path / name).unlink()
                    raise
        return relative

    def read(self, relative: str, *, limit: int = MAX_NOTE_BYTES) -> Snapshot:
        path = self._relative(relative)
        if not path.parts:
            raise VaultError("Select a note, not the vault root.")
        self.resolve(relative)
        with self.directory(str(path.parent)) as (descriptor, parent):
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
            handle = os.open(path.name, flags, dir_fd=descriptor) if descriptor is not None else os.open(parent / path.name, flags)
            with os.fdopen(handle, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise VaultError("Only regular files can be opened.")
                if info.st_size > limit:
                    raise VaultError(f"This file exceeds the {limit // (1024 * 1024)} MiB safety limit.")
                data = stream.read(limit + 1)
                after = os.fstat(stream.fileno())
                if len(data) > limit:
                    raise VaultError("This file is too large to open safely.")
                if (info.st_size, info.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ConflictError("The file changed while it was being read. Try again.")
        return Snapshot(data, hashlib.sha256(data).hexdigest(), info.st_dev, info.st_ino, info.st_mtime_ns, stat.S_IMODE(info.st_mode), info.st_nlink)

    def rename(self, relative: str, name: str) -> str:
        old = self._relative(relative)
        if not old.parts:
            raise VaultError("The vault root cannot be renamed here.")
        original = self.resolve(relative)
        folder = original.is_dir()
        name = validate_name(name, note=not folder)
        if name == old.name:
            return relative
        with self.directory(str(old.parent)) as (descriptor, parent):
            self._collision(descriptor, parent, name, exclude=old.name)
            self.resolve(relative)
            if sys.platform == "darwin" and descriptor is not None:
                rename = ctypes.CDLL(None, use_errno=True).renameatx_np
                rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
                rename.restype = ctypes.c_int
                # Apple's SDK sys/stdio.h: RENAME_EXCL = 0x00000004.
                result = rename(descriptor, os.fsencode(old.name), descriptor, os.fsencode(name), 4)
                if result:
                    code = ctypes.get_errno()
                    raise OSError(code, os.strerror(code))
            elif sys.platform.startswith("linux") and descriptor is not None:
                library = ctypes.CDLL(None, use_errno=True)
                if not hasattr(library, "renameat2"):
                    raise VaultError("Safe exclusive rename is unavailable on this system; use your file manager.")
                rename = library.renameat2
                rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
                rename.restype = ctypes.c_int
                if rename(descriptor, os.fsencode(old.name), descriptor, os.fsencode(name), 1):
                    code = ctypes.get_errno()
                    raise OSError(code, os.strerror(code))
            elif os.name == "nt":
                # Windows os.rename fails when the target already exists.
                os.rename(parent / old.name, parent / name)
            else:
                raise VaultError("Safe exclusive rename is unavailable on this system.")
        return str(old.parent / name)

    def trash(self, relative: str):
        path = self._relative(relative)
        if not path.parts:
            raise VaultError("The vault root cannot be moved to Trash here.")
        with self.directory(str(path.parent)):
            target = self.resolve(relative)
            # The OS Trash API is path-based; revalidate immediately before calling.
            # Never fall back to unlink/rmtree when Trash fails.
            send2trash(str(target))
