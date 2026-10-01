"""Repair macOS copy metadata that prevents Qt from discovering plugins."""

import os
from pathlib import Path
import stat
import sys


def prepare_plugin_directory(directory: Path) -> None:
    """Remove only Finder's hidden flag, without following symbolic links."""
    if sys.platform != "darwin" or directory.is_symlink():
        return
    for parent, folders, files in os.walk(directory, followlinks=False):
        for path in [Path(parent), *(Path(parent) / name for name in folders + files)]:
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                continue
            if metadata.st_flags & stat.UF_HIDDEN:
                os.chflags(path, metadata.st_flags & ~stat.UF_HIDDEN, follow_symlinks=False)


def prepare_qt_plugins() -> None:
    if sys.platform == "darwin":
        from PySide6.QtCore import QLibraryInfo

        prepare_plugin_directory(Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)))
