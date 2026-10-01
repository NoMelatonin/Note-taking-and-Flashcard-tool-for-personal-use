# Milestone 1 verification

Verified 30 September 2026: Python 3.14.5, PySide6/Qt 6.11.2, macOS 26.5.2, arm64. All write tests use uniquely isolated synthetic vaults/settings under this repository's ignored `work/`.

## Acceptance evidence

| Contract | Evidence |
| --- | --- |
| Native opening screen, specified palette, vault choice | `test_window.py`, `test_polish.py`; real Cocoa launch in `tools/smoke_gui.py`; native empty-state image visually reviewed. Chooser routing/cancellation uses test-selected paths; the OS picker itself is supplied by Qt's native API. |
| Opening preserves existing contents | `test_vault.py::test_open_scan_preserves_all_files`, clean-document byte/mtime/inode tests; non-Markdown and hidden-directory fixtures stay untouched. |
| Root/nested/Unicode creation, real tree agreement | `test_vault.py`, `test_explorer.py`; real file/directory assertions, contextual destinations and immediate active note. |
| Duplicates, invalid names, cancellation and failure | Case/Unicode normalization checks, reserved names/traversal tests, dialog retry/cancel tests, injected fsync/write failures; no overwritten originals or phantom files. |
| Source/read views and representative Markdown | `test_editor.py`, `test_rendering.py`, `test_saving_ui.py`; tasks/tables/nested lists/code/formatting/quotes; actual local QImage resource loaded and native Read/image screenshots reviewed. |
| Save/autosave/switch/close/restart | `test_document.py`, `test_saving_ui.py`; timed idle save, close flush, restored vault/reopened note, CRLF/mixed endings/BOM/no-final-newline and mode bits. |
| Rename and confirmed OS Trash | `test_vault.py`, `test_explorer.py`; descendant path/content preservation; native Trash integration reads the synthetic folder's preserved contents from macOS Trash. Failure never falls back to permanent deletion. |
| External edit/create/rename/remove and conflict | `test_navigation_ui.py`, `test_document.py`; GUI refresh deadlines 1.5 seconds, clean reload, same-mtime byte conflict, edit during staging, deleted-path preservation and explicit conflict copy. |
| Search and note links | `test_navigation.py`, `test_navigation_ui.py`; case-insensitive literal names/content, snippets around long-line matches, unsaved overlay, skipped unreadable notes, limits/cancellation, actual reading click and source modifier-click, ambiguity/missing messages. |
| Filesystem and preview boundaries | Traversal, unsafe/intermediate symlinks and stale-index escapes rejected; no outside fixture altered. Raw HTML escaped; remote/data/file resources refused; disguised SVG rejected before decoding. No resource loader fallback. |
| Keyboard, focus, zoom, resizing and status | `test_polish.py`, list/editor tests; native shortcuts, Tab focus, Unicode/emoji cursor positions, zoom restoration, visible Save/folder controls; 1120×760 and 860×600 layouts reviewed. Palette script verifies text/control/focus contrast. |
| Setup and reproducible checks | Constrained editable installation, module/launcher entry points, native GUI and test commands run successfully. Tested package versions are pinned in `requirements.lock`. |
| Git hygiene and preservation | Explicit staged-file lists inspected at every checkpoint; `.local/`, `work/`, virtual environments, secrets and generated files ignored; secret-pattern scan and tracked-file audit; original checkout unmodified and no push. |

## Commands and results

```sh
BLUEBELL_TEST_NATIVE_TRASH=1 .venv/bin/python -m pytest
.venv/bin/python tools/smoke_gui.py
.venv/bin/python tools/verify_palette.py
```

Final acceptance suite: **80 passed**. Default run: one opt-in native Trash test skipped. The full run leaves one uniquely named synthetic folder in the system Trash as proof of recoverability; it never trashes real notes. Native QA images remain in ignored `work/`, not in Git.

Follow-up checks cover italic/standard undo-redo shortcuts, modal-dialog cleanup and preservation of a pending filesystem action's original target when conflict resolution selects a new copy. The setup command in README was rerun with pinned constraints. These results verify local behavior; they do not establish Windows/Linux compatibility, a signed installer, screen-reader accessibility, large-vault throughput or browser delivery beyond the click-dispatch contract.

## Security and practical limits

- A source note cannot execute HTML/scripts or trigger remote image requests. No WebEngine is used. External HTTP/HTTPS is opened only by the explicit click handler; tests replace browser dispatch with a spy.
- All symlinks are skipped/refused; path validation and no-follow directory/file descriptors cover the tested traversal and symlink replacement cases. Readable note text stays in local files and the active editor; no cloud service or database participates.
- Atomic replacement is not a compare-and-swap transaction. Another process can write during the last check/replace gap. OS Trash uses a path API; a concurrently moved open directory can outlive path revalidation. These limits are disclosed, not described as fully race-free containment.
- Input limits: regular UTF-8 Markdown, 8 MiB per note; local raster images 20 MiB and 24 million pixels. SVG is refused, including SVG disguised with a raster filename.
- Autosave failures preserve the live buffer and block unresolved transitions. Pending buffers do not survive a forced process exit/crash. Ordinary mode bits/BOM/practical line endings are preserved; extended ACLs/ownership/Finder metadata are not specifically copied.
- Task checkboxes are source-edited. Heading anchors, embeds, callouts, LaTeX and complex source link parsing remain later work. Graphs, AI, flashcards and distribution were not added.


## Reference workspace refinement — 1 October 2026

Verified the compact screenshot-inspired workspace natively on macOS. Full automated suite: 89 passed, one optional native Trash integration skipped. Native explorer/polish/window tests: 23 passed. Additional tests exercise hidden-sidebar search, returning to files, the filename/tab heading, closing with unsaved edits, cancelled close and the reading-mode icon. Wide and laptop synthetic screenshots are retained under ignored `work/reference-design.png` and `work/reference-laptop.png`. The app still edits exact Markdown source and supports one note at a time; the tab-shaped header does not imply multi-tab support. Cream colours remain the user's earlier preference.
