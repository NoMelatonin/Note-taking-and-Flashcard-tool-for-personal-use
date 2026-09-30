# Implementation plan

Status: steps 1–4 verified on macOS, 30 September 2026; final polish/review in progress.

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

### Step 3 — Markdown writing, reading and saving

- Editable monospace source, Edit/Read controls, Markdown tables/tasks/nested lists/code, safe local raster images, source formatting, list continuation/indentation, undo/redo and in-note find.
- Idle autosave after 500 ms; explicit Save and platform Save shortcut; pending edits flush before note/vault switching, rename, Trash and normal close. Save state is textual. Failed saves retain editor text and pause automatic retries.
- Same-directory temporary files, fsync and atomic replacement preserve practical permissions, UTF-8 BOM and existing line endings. Clean opening never writes. Content hashes plus inode/mtime detect external edits, including a same-size edit with restored mtime; a second check covers changes during staging. The final check/replace gap still exists with concurrent writers.
- Conflicts offer explicit reload/discard or a new conflict copy; removed paths are never silently recreated. Save-as uses a validated single name/destination inside the vault.
- Verified: 53 passed, 1 opt-in native Trash test skipped, both headless and native Cocoa. Native Edit/Read screenshots reviewed (`work/explorer.png`, `work/reading.png`). Tests cover restart/close, switch flush, write failure, cancelled transitions, conflict copies, external removal, BOM/newlines/permissions, source list behavior, rendered tasks/tables, raw HTML, remote/data/file resources and a disguised SVG.
- Try the demo from step 2: edit **Welcome.md**, wait for **Saved**, switch to **Read**, try **Find**, then reopen the app. To test conflicts, edit a synthetic note in both Bluebell and a separate editor before the idle save; use **Save a conflict copy…**.
- New note text is UTF-8. Files above 8 MiB are refused without rewriting; raster resources are capped at 20 MiB/24 million pixels. Scripts/raw HTML and all automatic external resources are blocked. Qt Widgets, not a web browser, renders the note.

### Step 4 — navigation and external updates

- Literal case-insensitive filename/content search with paths and context around the match; up to 200 results, skipped-note feedback and a labelled overlay for current unsaved text. Search/scan run in Qt workers; stale jobs cannot replace a newer query or vault.
- Wiki links support unambiguous names, vault-root paths, aliases and optional `.md`. Ordinary relative `.md` links may use parent directories while remaining inside the vault. Missing/ambiguous/unsafe links report an error and never create a note.
- Links work through an actual reading-view click and Cmd/Ctrl-click in source. HTTP/HTTPS is dispatched to the default browser only on an explicit click; other schemes are refused.
- External tree additions/renames/removals and active-document changes poll every 750 ms. File stamps also invalidate active search after outside content edits. Manual **Refresh** remains available; delayed jobs from earlier vaults/operations are ignored.
- Verified: full headless suite — 66 passed, 1 optional native Trash test skipped before the final click test was added. All 12 native navigation/preview cases passed after correcting a Qt test-call argument; the actual click case was rerun successfully. Creation/rename/removal refresh met 1.5-second test deadlines. Native image screenshot reviewed (`work/reading-image.png`).
- Try: search for `thought` in the demo, clear search to return to the tree, and click **your first thought** in Welcome's reading view. Create/rename a synthetic `.md` file in Finder or another editor; the tree updates automatically. Duplicate note basenames deliberately produce an ambiguity message.
- No graph/backlink database, AI, flashcards, networking or later-milestone implementation added.

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
