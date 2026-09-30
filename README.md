# Remnote-Obsidian rebuild

A Python desktop application for local Markdown notes, with linked notes and spaced-repetition flashcards planned for later milestones. macOS is the first target; the implementation should remain portable to Windows and Linux.

## Current status

Milestone 1 is being implemented as **Bluebell**, a native Python/PySide6 application. Step 1 (window and vault chooser) has launched and been visually verified on macOS. See [PLAN.md](PLAN.md) for actual progress.

## Setup, launch and tests

Use Python 3.11–3.14 (verified: Python 3.14.5, PySide6 6.11.2, macOS). Run from this repository:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m bluebell --no-restore
.venv/bin/python -m pytest
```

Choose **Open vault…** to select an existing folder. Installation downloads dependencies once; the app itself needs no network. `--vault PATH` opens a folder directly. `python tools/smoke_gui.py` briefly launches the native app and saves a screenshot under ignored `work/`.

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

Until the remaining steps are complete, only the vault chooser/window are available. Graphs, AI, flashcards and distribution remain later milestones.
