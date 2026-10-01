# Bluebell — local Markdown notes

Milestone 1 is implemented: a native desktop notebook with baby-blue accents, dimmed-white surfaces, a real vault explorer, Markdown editing/reading, safe autosave, search and internal links. Graphs, AI and flashcards remain later milestones.

## Setup and launch

Run from the project folder below; open this same folder in VS Code:

```text
/Users/max/Desktop/Second-Brain/Own Projects/Remnote-Obsidian rebuild
```

The local `.venv` is ready; run `./Launch.command`. The launcher loads the source from its own project folder. The setup commands below are only needed for a fresh environment. Virtual environments are machine-specific: recreate `.venv` when copying the project to another computer.

Requires Python 3.11–3.14; verified on **Python 3.14.5, PySide6 6.11.2, macOS 26.5.2, Apple Silicon**. The pinned Qt wheels require macOS 13 or later; older Macs and other Python versions in the supported range have not been tested.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -c requirements.lock -e '.[dev]'
.venv/bin/python -m bluebell
```

Installation downloads dependencies once. The running app needs no account, AI service, database or network connection. **Open vault…** uses the native folder chooser. `--no-restore` starts at the empty chooser; `--vault PATH` opens an existing folder directly.

After setup, double-click **Launch.command** in Finder or run `./Launch.command`. This is a development launcher, not a packaged/signed Mac application. Use a terminal with normal macOS GUI access; the restricted Codex shell blocks Cocoa/clipboard services without a permitted native launch.

Try the isolated example:

```sh
.venv/bin/python tools/make_demo_vault.py
.venv/bin/python -m bluebell --vault work/demo-vault
```

The generator creates synthetic notes and an image under ignored `work/`. An existing demo is left untouched, including your edits. Select **Welcome.md**, then try **Read** and its internal links.

## Everyday workflow

- Select a folder, then **New folder** or **New note** to create inside it. A selected note uses its parent; root/no selection uses the vault root. The name dialog shows the destination. Files/directories are created immediately; duplicate or unsafe names never overwrite existing entries.
- Write ordinary Markdown in **Edit**, then choose **Read** for headings, formatting, lists, tasks, tables, quotes, code and local images. Source is never reformatted merely by opening it. **A− / A+** zoom the note; drag the divider to resize the sidebar.
- Autosave runs after 500 ms idle. **Save** and switching/closing flush pending edits. Status says **Saving**, **Saved**, **Unsaved** or **Save failed**. **Undo/Redo** apply to editor text, not filesystem operations.
- **Rename** preserves content and warns that links may need updating. **Trash** confirms the item and folder contents, uses macOS Trash, and leaves the item intact when Trash fails. Non-Markdown files are preserved; dot-directories are hidden.
- Search filenames and contents in **Search notes…**. Results show paths and context; current unsaved text is labelled. Clear search to return to the tree. Results are capped at 200; narrow the query when capped. Unreadable notes are reported as skipped.
- Click links in **Read**, or Cmd/Ctrl-click simple inline links in source. `[[Note]]` resolves only when unique; `[[folder/Note]]` is relative to the vault root; `[[folder/Note.md|Label]]` supports aliases. `[Label](../Note.md)` is relative to the current note. Missing/ambiguous links show an error and never create files.
- External additions, renames, removals and active-note changes normally appear after the 750 ms poll. **Refresh** is the fallback. Search/scan workers keep those operations off the UI thread.

## Conflicts and failed saves

A clean note changed elsewhere reloads automatically. If local edits conflict, autosave pauses: **Reload from disk** explicitly discards local edits, while **Save a conflict copy…** creates a separate note and preserves the disk version. If a note is removed or renamed outside the app, its editor text stays available; save an explicit new copy inside the vault. The old path is never recreated silently.

Permission/disk failures keep the editor text and show an error. Leaving or closing with unsaved changes requires resolving the save, saving a copy, explicitly reloading/discarding, or cancelling the transition. If the entire vault is unavailable, restore/reopen it before saving there; text can still be copied from the source editor. Pending editor buffers have no crash/force-quit recovery.

## Shortcuts

Use Cmd on macOS and Ctrl on Windows/Linux. Buttons remain available.

| Shortcut | Action |
| --- | --- |
| Cmd/Ctrl+N | New note at the selected destination |
| Cmd/Ctrl+S | Save |
| Cmd/Ctrl+F | Find in the active note |
| Cmd/Ctrl+Shift+F | Search the vault |
| Cmd/Ctrl+E | Toggle Edit/Read |
| Cmd/Ctrl+B / I | Bold / italic source syntax |
| Platform Undo/Redo | Undo/redo source edits |
| Platform zoom shortcuts | Increase/decrease note text size |
| Enter in a list | Continue bullet/number/task list; empty item ends it |
| Tab / Shift-Tab | Indent/outdent lists; otherwise move keyboard focus |

## Verification

```sh
.venv/bin/python -m pytest
QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest
.venv/bin/python tools/smoke_gui.py
.venv/bin/python tools/verify_palette.py
```

The final native acceptance run passed **80 tests**, including the opt-in OS Trash integration. Default tests skip that one case (79 passed, 1 skipped). To reproduce the full native run:

```sh
BLUEBELL_TEST_NATIVE_TRASH=1 .venv/bin/python -m pytest
```

That test leaves a uniquely named `bluebell-synthetic-*` folder in your macOS Trash and verifies its contents are recoverable. All test vaults/settings are synthetic and repository-local under ignored `work/`. The actual study vault was never used for write tests. `smoke_gui.py` launches the real Cocoa window and saves QA images under `work/`; offscreen tests alone do not establish a native launch.

See [PLAN.md](PLAN.md) for verified checkpoints and [docs/VERIFICATION.md](docs/VERIFICATION.md) for acceptance evidence. Setup, CLI help and the development launcher were tested. Windows/Linux execution, packaging, accessibility with a screen reader, and large/network vault performance are unverified.

## Filesystem and preview security

Notes remain ordinary UTF-8 `.md` files; existing uppercase `.MD` files are also supported. Saves stage a same-directory temporary file, fsync it, check the disk version again and atomically replace the note. Clean opening never writes; UTF-8 BOM and practical newline conventions survive edits. Ordinary file mode bits are preserved. Extended ACLs, ownership, Finder tags and other extended metadata are not specifically preserved by replacement. No backup/version history is provided.

Traversal and unsafe names are rejected. All symlinks are refused, including links within the vault. macOS/Linux reads and mutations use directory descriptors and no-follow opens; macOS rename uses exclusive `renameatx_np`, so an existing target cannot be replaced. Creation uses exclusive file opens and case/Unicode-normalization collision checks. New hidden names and Windows-reserved names are refused.

Raw HTML is escaped. The reading view uses Qt Widgets, without a JavaScript/web engine. Only validated, vault-contained raster images load; remote/data images, SVG, arbitrary file resources and unsupported URI schemes are blocked. HTTP/HTTPS links open the default browser only after an explicit click. Note input is capped at 8 MiB; image input at 20 MiB and 24 million pixels. Oversized/invalid UTF-8 notes are left unchanged.

**Remaining race:** hashing/inode/mtime checks detect conflicting versions but cannot atomically compare-and-replace against another writer. A change in the final check/replace gap may still be overwritten. The OS Trash API is path-based, and an already-open directory can be moved by another process; these operations are not an OS sandbox against a concurrent process manipulating the same filesystem. Avoid simultaneous writes to the same note. Static traversal, symlink escapes and unsafe preview resources are covered by the tests.

Private settings (last vault and zoom) live in ignored `.local/settings.json`, written atomically with mode `0600`. `BLUEBELL_SETTINGS_DIR` is a test/development override. No personal vault, credentials or runtime settings belong in Git; `.env` variants, `.local/`, `work/`, virtual environments and generated files are ignored.

Renderer/Trash API references: [Qt QTextBrowser](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QTextBrowser.html), [markdown-it-py security](https://markdown-it-py.readthedocs.io/en/latest/security.html), [Send2Trash](https://github.com/arsenetar/send2trash).

## Code and scope

`src/bluebell/` separates `vault.py` (filesystem boundary/actions), `document.py` (saving/conflicts), `navigation.py` (search/links), `rendering.py` (restricted preview), `editor.py` (source behavior), `workers.py` (background scans) and `ui.py` (native controls). `python -m bluebell` / `bluebell` are the entry points. `requirements.lock` pins the tested runtime/test dependencies.

Inline Live Preview, heading/block anchors, complex source modifier-click parsing, SVG/remote images, LaTeX, callouts, embeds, clipboard attachments, backlinks/graph, AI, flashcards, cloud sync, plugins and public distribution remain outside Milestone 1. Task checkboxes render but are edited in source.

On 1 October 2026, the implementation was copied into the canonical desktop checkout above, on local branch `codex/milestone-1-desktop`. A later startup repair cleared recursively copied macOS hidden flags inside `.venv`: Python 3.14 had skipped the editable-install path file (`No module named bluebell`), and Qt could not discover its Cocoa plugin. The launcher now also loads this folder's `src/` directly. If another copy exhibits these same errors, run `chflags -R nohidden .venv` from the project folder. Earlier desktop docs are preserved in ignored `.local/desktop-copy-originals-2026-10-01/` and a local Git stash. The managed worktree remains available; no GitHub push was performed. Requirements: [PROJECT_SPEC.md](PROJECT_SPEC.md), [docs/MILESTONE_1.md](docs/MILESTONE_1.md), [AGENTS.md](AGENTS.md).
