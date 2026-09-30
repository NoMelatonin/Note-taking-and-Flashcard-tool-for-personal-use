# Remnote-Obsidian rebuild

A Python desktop application for local Markdown notes, with linked notes and spaced-repetition flashcards planned for later milestones. macOS is the first target; the implementation should remain portable to Windows and Linux.

## Current status

Milestone 1 is being implemented as **Bluebell**, a native Python/PySide6 application. The explorer, Markdown editor/reading view, safe autosave, search and note links are verified on macOS. Final usability review is in progress; see [PLAN.md](PLAN.md).

## Setup, launch and tests

Use Python 3.11–3.14 (verified: Python 3.14.5, PySide6 6.11.2, macOS). Run from this repository:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m bluebell --no-restore
.venv/bin/python -m pytest
```

Choose **Open vault…** to select an existing folder. Installation downloads dependencies once; the app itself needs no network. `--vault PATH` opens a folder directly. `python tools/smoke_gui.py` briefly launches the native app and saves a screenshot under ignored `work/`.

Try an isolated example:

```sh
.venv/bin/python tools/make_demo_vault.py
.venv/bin/python -m bluebell --vault work/demo-vault
```

Select a folder to create inside it, or a note to create in its parent. Root/no selection creates at the vault root. Rename warns about links; Trash asks for confirmation and never falls back to permanent deletion. All symlinks are skipped. Existing non-Markdown files remain untouched.

For headless tests, use `QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest`. A terminal with normal macOS GUI access is required to verify the native window. Windows/Linux packaging and execution are unverified.

## Start working with Codex

1. Open this repository as a local project in Codex, or as a folder in VS Code with the Codex extension.
2. Open [START_CODEX.md](START_CODEX.md) and send its implementation prompt to Codex.
3. Let Codex implement and verify one step at a time. Try the app at the checkpoints in [PLAN.md](PLAN.md).

## Project documents

- [PROJECT_SPEC.md](PROJECT_SPEC.md): overall requirements and later milestones.
- [docs/MILESTONE_1.md](docs/MILESTONE_1.md): exact first-task scope, appearance and acceptance criteria.
- [PLAN.md](PLAN.md): implementation sequence and verification status.
- [AGENTS.md](AGENTS.md): project instructions and security rules.

## Storage and security

Notes live as ordinary `.md` files in a vault folder chosen by the user. Development scratch work belongs in ignored `work/`, and private development settings/data in ignored `.local/`. Use synthetic notes in tests.

The first milestone requires no AI service, API key or `.env` file. If later work introduces credentials, keep them out of Git. `.gitignore` does not remove already tracked secrets.

Edit ordinary Markdown, switch to **Read** for formatted text, and use **Find**, **Bold**, **Italic**, **Undo** and **Redo**. Lists continue on Enter; an empty item ends a list. Tab/Shift-Tab change list indentation and move focus on ordinary text. Saves run after 500 ms idle and before switching/closing; **Save** is always available.

If another editor changes a note, Bluebell reloads a clean note or pauses autosave when local edits conflict. **Reload from disk** explicitly discards local edits; **Save a conflict copy…** preserves both. If a note disappears, save a new copy; the old path is never recreated automatically. A failed write keeps your text and blocks leaving until resolved/cancelled.

Search names and contents with **Search notes…** or Cmd/Ctrl+Shift+F. Results include paths and context. Clear search to return to the folder tree. `[[Note]]`, `[[folder/Note|Label]]` and relative `[Label](../Note.md)` links navigate on a reading-view click or Cmd/Ctrl-click in source. Bare duplicate names are reported as ambiguous. External tree changes normally appear after the 750 ms poll; **Refresh** is the fallback.

Reading escapes raw HTML, permits only vault-contained raster images, and never fetches remote/data images or executes scripts. HTTP/HTTPS links open in the default browser only when clicked. Note text is limited to 8 MiB; image input to 20 MiB/24 million pixels. All symlinks are refused. Atomic save/version checks reduce conflict risk but cannot eliminate the concurrent check/replace gap. Graphs, AI, flashcards and distribution remain later milestones.
