"""Copied Finder flags must not hide Qt plugins or affect linked files."""

import os
import stat
import sys

import pytest

from bluebell.qt_runtime import prepare_plugin_directory


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS file flags")
def test_copied_hidden_plugins_are_repaired_without_following_links(sandbox):
    plugins = sandbox / "plugins"
    platforms = plugins / "platforms"
    platforms.mkdir(parents=True)
    cocoa = platforms / "libqcocoa.dylib"
    cocoa.write_bytes(b"synthetic plugin")
    outside = sandbox / "outside"
    outside.mkdir()
    linked = outside / "untouched"
    linked.write_bytes(b"preserve")
    (plugins / "linked-directory").symlink_to(outside, target_is_directory=True)
    (plugins / "linked-file").symlink_to(linked)
    for path in (plugins, platforms, cocoa, outside, linked):
        os.chflags(path, path.stat().st_flags | stat.UF_HIDDEN)

    prepare_plugin_directory(plugins)
    prepare_plugin_directory(plugins)

    for path in (plugins, platforms, cocoa):
        assert not path.stat().st_flags & stat.UF_HIDDEN
    assert cocoa.read_bytes() == b"synthetic plugin"
    for path in (outside, linked):
        assert path.stat().st_flags & stat.UF_HIDDEN


def test_other_platforms_leave_directory_untouched(sandbox, monkeypatch):
    monkeypatch.setattr("bluebell.qt_runtime.sys.platform", "linux")
    prepare_plugin_directory(sandbox / "does-not-exist")
