# Implementation plan

Status: **Milestone 1 implemented and verified on macOS**, 30 September 2026. Only this milestone is complete. See [docs/VERIFICATION.md](docs/VERIFICATION.md) for acceptance evidence and [README.md](README.md) for tested setup/launch commands and limitations.

## Milestone 1: note-taking system

Completed in the documented order, keeping each step runnable:

1. **Project foundation and window** — Python packaging/entry point, native PySide6 window, the specified blue/white palette, native vault chooser and remembered last vault.
2. **Vault explorer and real filesystem actions** — actual folder tree, nested note/folder creation, Unicode/name validation, collision prevention, rename, confirmed OS Trash and error handling.
3. **Markdown writing and saving** — source editor and reading view, formatting/list shortcuts, in-note find, 500 ms autosave, save state, atomic replacement, external conflicts and safe switching/restart.
4. **Navigation and updates** — filename/content search, basic internal links, contained raster images, 750 ms external refresh, background search/scan and stale-job protection.
5. **Polish and review** — zoom, keyboard focus/shortcuts, contrast and resizable laptop layout; acceptance checks, pinned dependencies, development launcher and final documentation.

## Local Git checkpoints

| Step | Checkpoint | Verification and how to try |
| --- | --- | --- |
| 1 | `128da94` | One native Qt test passed; Cocoa window launched and empty-state screenshot reviewed. Run `.venv/bin/python -m bluebell --no-restore`, then **Open vault…**. |
| 2 | `c2f3b97` | 29 native tests passed, including a recoverable synthetic OS Trash operation. Generate the demo with `tools/make_demo_vault.py`; select root/folder/note and try creation, rename and Trash. |
| 3 | `dcda4d2` | 53 tests passed (one opt-in Trash test skipped); native Edit/Read screenshots reviewed. Edit **Welcome.md**, wait for **Saved**, use **Read/Find**, and reopen the app. Conflict/failure paths preserve editor text. |
| 4 | `f409097` | Search/link/security tests and native reading/source clicks passed. External creation/rename/removal met 1.5-second test deadlines. Search `thought`, click Welcome's internal links, and change a synthetic file in Finder. |
| 5 | Tip of `codex/milestone-1` | Final native suite: 80 passed. Native 1120×760 and 860×600 layouts reviewed; contrast checks passed. Use **A−/A+**, keyboard shortcuts and **Launch.command**. See `git log -5 --oneline` for the final checkpoint ID. |

Each checkpoint stages only related project files. No credentials, personal vaults, private settings, generated artifacts or personal learnings note were staged. Nothing was pushed.

## Final verification

- Tested setup: `python3 -m venv .venv` and `.venv/bin/python -m pip install -c requirements.lock -e '.[dev]'`.
- Tested launch: module entry point, launcher CLI help and actual native Cocoa window. Native GUI services require a permitted launch outside the development shell's restricted sandbox.
- `BLUEBELL_TEST_NATIVE_TRASH=1 .venv/bin/python -m pytest`: **80 passed** on Python 3.14.5 / PySide6 6.11.2 / macOS 26.5.2 / arm64.
- Default tests skip the native Trash integration. Offscreen tests are useful for CI but do not prove native launching.
- `tools/smoke_gui.py`: native QA images in ignored `work/empty-state.png`, `work/explorer.png`, `work/reading.png`, `work/reading-image.png` and `work/laptop.png`.
- `tools/verify_palette.py`: text contrast 4.89–9.39:1; primary control 5.36:1; focus outline 4.73:1.
- Filesystem, preview and conflict behavior verified with synthetic vaults under ignored `work/`; existing user vault files were never used for write tests.
- Original checkout files were left unchanged. This managed worktree originally contained only the initial README; the requirement docs were copied from the original checkout's untracked files.

## Settled defaults and limitations

- Python/PySide6 selected; temporary app name **Bluebell**. Plain Markdown files are authoritative; no note database or AI dependency.
- Source + Read view, the supplied palette and shortcuts are implemented. Inline Live Preview remains deferred.
- Stronger boundary default: all symlinks are refused, even within the vault. New hidden/unsafe names are refused. Note/image limits and UTF-8-only editing are documented in README.
- Content/inode/mtime checks plus atomic replacement reduce conflicts; the final concurrent check/replace gap remains. Path-based Trash and moving an already-open directory are documented race limits.
- Normal mode bits/newlines/BOM are retained; extended file metadata, persistent undo, backup history and crash recovery are not provided.
- No Windows/Linux validation, public distribution, screen-reader certification or large/network-vault performance claim.

## Later milestones — not implemented

- Knowledge graph and richer backlinks.
- Editable source-linked flashcards and spaced repetition.
- Local background AI generation.
- Packaged macOS release, then Windows/Linux builds and testing.
