# Implementation plan

Status: steps 1–2 verified on macOS, 30 September 2026; steps 3–5 in progress.

## Milestone 1: note-taking system

Follow `docs/MILESTONE_1.md`. Complete the following in order, keeping each step runnable:

1. **Project foundation and window** — inspect the repository, explain the proposed structure, create Python packaging and an entry point, then build the muted blue/white window and vault chooser. Verify it launches on macOS.
2. **Vault explorer and real filesystem actions** — folder tree, new note/folder controls, nested destinations, rename/Trash, validation and error handling. Verify operations using a synthetic vault under ignored `work/`.
3. **Markdown writing and saving** — source editor, Edit/Read modes, formatting and list shortcuts, autosave, save state and safe switching/restart behaviour. Verify failure and external-edit conflict paths.
4. **Navigation and updates** — vault search, basic internal links, local images and external filesystem refresh. Verify ambiguous links and vault boundaries.
5. **Polish and review** — keyboard navigation, focus/contrast, window resizing and empty/error states. Finish the milestone acceptance checklist and README setup/run instructions.

## Verified checkpoints

### Step 1 — foundation and window

- Python/PySide6 selected; the temporary display name is Bluebell. Separate vault, document, navigation, rendering and UI modules follow in the remaining steps.
- Added editable Python packaging, `bluebell` / `python -m bluebell`, native vault chooser, restored last-vault setting under ignored `.local/`, the specified palette and resizable sidebar.
- Verified with Python 3.14.5 and PySide6 6.11.2 on macOS: `python -m pytest` — 1 passed. `python tools/smoke_gui.py` launched the actual Cocoa window; visually reviewed `work/empty-state.png`.
- Try: `.venv/bin/python -m bluebell --no-restore`, then **Open vault…**. Folder actions/editor arrive in step 2/3.
- Sandbox limitation: Cocoa/clipboard services require a native, unsandboxed launch in this development environment. Headless CI can use `QT_QPA_PLATFORM=offscreen`; it does not verify a native launch.
- This managed worktree started at the initial commit. Requirements were copied from the original checkout's untracked documents; the original checkout and user files were not edited.

### Step 2 — vault explorer and filesystem actions

- Real nested folder tree, note/folder creation, contextual destinations, Unicode names, inline dialog errors, rename and confirmed OS Trash. Notes currently open as read-only source until step 3.
- Name validation rejects traversal, hidden creation names, reserved platform names and case/Unicode-normalization collisions. All symlinks are skipped, including links within the vault. macOS file operations use directory descriptors/no-follow opens, and rename uses exclusive `renameatx_np` rather than overwriting an existing destination.
- Verified: `BLUEBELL_TEST_NATIVE_TRASH=1 .venv/bin/python -m pytest` — 29 passed against native Cocoa. The native Trash test moved one uniquely named synthetic folder and read back its preserved contents from macOS Trash. Failure, duplicate and cancellation tests preserve originals.
- Native explorer screenshot reviewed: `work/explorer.png`.
- Try: `.venv/bin/python tools/make_demo_vault.py`, then `.venv/bin/python -m bluebell --vault work/demo-vault`. Select root/folder/note; use **New folder**, **New note**, **Rename**, **Trash** or the context menu. The demo generator leaves an existing demo untouched.
- Security limitation: Trash is an OS path-based API, so ancestor revalidation cannot eliminate a concurrent malicious directory replacement. Descriptor-based file operations also cannot defend against another process moving an already-open directory outside the vault. See final security notes as implementation progresses.

After each step, report what is usable, what was verified and how the user can try it. Continue the scoped work unless the user asks to pause or a decision is genuinely required. Keep completed steps and actual validation results recorded here; do not mark planned work complete.

Create a local Git checkpoint once a coherent step is verified, inspecting the exact files first. Preserve and leave the user's existing untracked learnings note untouched. Do not push to GitHub without user authorization.

## Later milestones

- Knowledge graph and richer backlink navigation.
- Editable source-linked flashcards and spaced repetition.
- Local background AI generation.
- Packaged macOS release, followed by Windows/Linux builds and testing.

## Current decisions and defaults

- Plain Markdown files are authoritative.
- macOS is the first validation target; portable code is required.
- Python/PySide6 is the proposed stack.
- First editor: Markdown source plus formatted reading view. Inline Live Preview is deferred.
- First task uses no AI service, API credentials or database for note text.
- Code, docs and development artifacts stay in the canonical repository; test vaults are synthetic.
