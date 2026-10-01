# Milestone 1 — local Markdown note-taking

Status: Milestone 1 implemented and verified on macOS, 30 September 2026. Acceptance evidence and explicit limitations: [VERIFICATION.md](VERIFICATION.md). The requirements below define the delivered scope.

## Outcome

The user opens a macOS desktop app, chooses one folder as a vault, creates folders and notes at any depth, and writes Markdown. The app and the local filesystem show the same structure. Notes remain readable outside the app and survive reopening it.

"Obsidian-like" in this milestone means a filesystem vault, an expandable folder sidebar, plain Markdown editing, a formatted reading view, search and basic internal note navigation. It does not mean reproducing every Obsidian feature. Inline Live Preview, graph view, AI, flashcards, plugins, cloud sync and distribution installers are later work.

## 1. Vault selection and folder tree

- On first launch, show a friendly empty state with an **Open vault** button and a native folder chooser. No account or network connection is required.
- The vault is the selected existing directory, including its subdirectories. Opening it must not import, convert, move or rewrite existing files.
- Show its name and an expandable folder tree. List Markdown notes; preserve all other files. Dot-directories such as `.git` are hidden by default, and links to paths outside the vault are not browsable.
- Provide an **Open another vault** control. Resolve unsaved changes before switching.
- Remember the last vault locally. If unavailable on restart, return to the chooser with an understandable message.
- Refresh changes made through the app immediately after a successful filesystem operation. Reflect external additions, removals and renames within approximately one second under normal conditions; provide a manual refresh fallback.

## 2. Create and manage actual folders and notes

- Keep accessible **New note** and **New folder** icon buttons visible in the sidebar toolbar, with equivalent context-menu actions.
- If a folder is selected, create inside it. If a note is selected, create in its parent. With no selection, create at the vault root. The name dialog must show the destination.
- A new note is a real UTF-8 `.md` file. Append `.md` when omitted; avoid appending it twice. Create the file before adding it to the sidebar and open it immediately.
- A new folder is a real directory, visible both in the app and Finder immediately. Support nested creation using the same controls.
- Accept normal names containing spaces and Unicode. Reject empty names, reserved navigation names such as `.` and `..`, path separators and unsafe platform-specific names. A name field is one entry name, not a path.
- Existing files and folders, including case-insensitive collisions, must never be overwritten. Keep the dialog open with a useful error and allow another name.
- Allow note/folder renaming. Flush pending edits first, refresh descendant paths and preserve content. Warn that links to renamed paths may need updating; automatic link rewriting is later work.
- Allow deletion with confirmation, using the operating system's Trash rather than permanent deletion. Folder confirmation names the folder and states that its contents will also move to Trash. If Trash is unavailable, report the failure and leave the item intact.
- Show permission or disk errors in the app. Failed actions must not create phantom tree entries or lose the current editor text.

## 3. Markdown editor and reading view

- Use a two-pane layout: folder sidebar on the left and the current note on the right. One active note is sufficient initially; multiple tabs are later work.
- The editable source is the exact Markdown text. Do not reformat or normalise an existing note merely by opening it. Preserve existing newline conventions when saving, where practical.
- Provide **Edit** and **Read** view controls. Edit shows Markdown syntax; Read displays formatted content. A side-by-side preview is optional. Inline syntax-hiding Live Preview is not required for this milestone.
- Support headings, paragraphs, bold, italics, strikethrough, nested bullet lists, numbered lists, task lists, blockquotes, inline code, fenced code blocks, horizontal rules, tables, hyperlinks and local images in reading view.
- Markdown checkboxes must render correctly. Interactive checkbox toggles in reading view are optional; their source remains editable.
- Provide readable wrapping and scrolling, undo/redo, selection, copy/paste and in-note find. Continue bullet/numbered/task lists on Enter; Enter on an empty list item ends it. Tab/Shift-Tab indent/outdent list items without trapping keyboard focus.
- Show the note name or vault-relative path and an explicit save state: **Saving**, **Saved**, **Unsaved** or **Save failed**.
- Read unsupported syntax without deleting it. LaTeX rendering, callouts, note embeds, block references and attachments imported from the clipboard are later enhancements.

## 4. Search and note links

- Provide **Search notes** across Markdown filenames and contents inside the vault. Basic literal case-insensitive search is sufficient; no query language is required. Results show the relative path and useful text context.
- Support `[[Note]]`, `[[folder/Note]]` and `[[folder/Note|Label]]`, with optional `.md`. Explicit paths are relative to the vault root; unqualified names resolve only when unambiguous across the vault.
- Support normal relative Markdown links to `.md` files. Follow internal links from reading view; Cmd-click/Ctrl-click from source is recommended.
- A missing or ambiguous link must display a clear message without guessing or silently creating a file. Optional explicit creation of a missing note may be offered inside the vault.
- Render standard `![description](relative-image-path)` images only when their resolved path is inside the vault. Preserve other Obsidian-specific image syntax as text initially.
- Permit external HTTP/HTTPS links only on an explicit user click, opening the default browser. Do not automatically fetch external images or execute other URI schemes.
- Basic link navigation is part of this milestone. Backlinks and the graph are the next milestone.

## 5. Saving, filesystem safety and conflicts

- Autosave after a short idle interval, approximately 500 ms. Flush pending saves when leaving a note, switching vaults or closing normally. Cmd/Ctrl+S also saves explicitly.
- Write safely using a temporary file in the note's directory followed by atomic replacement where supported. Preserve file permissions where practical, clean temporary files and keep editor text on failure.
- Detect whether the file changed externally since it was loaded/last saved before writing. If an external change conflicts with local edits, pause autosave and offer **Reload from disk** or **Save a conflict copy**. Keep both versions unless the user explicitly discards one. Avoid pretending a stat check makes concurrent writes fully race-free.
- If the current note is externally removed or renamed, preserve unsaved text and offer an explicit save-as inside the vault; do not silently recreate the removed path.
- Resolve paths before file operations. Creation, save, rename, deletion and embedded-image loading must stay within the chosen vault. Reject traversal and symlinks that escape it, including unsafe intermediate directories.
- Treat rendered notes as untrusted input: disable/escape raw HTML as needed, execute no scripts, and allow no arbitrary local-file access or automatic network requests.
- Editing notes requires no database and no AI dependency. Markdown files are authoritative; indexes may be reconstructed from them.
- Development settings belong in ignored `.local/`; temporary test vaults and scratch work belong in ignored `work/`, inside the repository. Never modify the user's real vault during tests.

## 6. Friendly, low-glare visual design

The user's latest refinement on 1 October 2026 replaces the earlier blue/cream palette with the supplied screenshot's light theme. Keep the compact icon controls, frameless surfaces, bottom vault selector, one active-note tab, slim header and centered text column. Avoid neon accents, heavy shadows and distracting motion.

| Role | Current colour |
| --- | --- |
| Main background/editor | `#FFFFFF` |
| Sidebar and secondary panels | `#F6F6F6` |
| Tab strip | `#FAFAFA` |
| File selection | `#E7E7E7` |
| Editor text selection | `#EDE6FD` |
| Focus outline | `#737373` |
| Main text | `#2E2E2E` |
| Secondary text | `#666666` |
| Quiet separators / tree guides | `#E5E5E5` / `#DDDDDD` |


- Use clear labels, generous spacing, softly rounded controls and subtle hover/selection states. Pair icons with text labels or accessible names.
- Use a comfortable system font for app controls and a readable monospace font for Markdown source. Start around 14–16 px and allow zoom.
- Keep text and focus states legible against the muted surfaces; do not use pale colours for body text. Verify contrast and keyboard usability during implementation.
- Resizable sidebar and main area; the first screen should remain usable on a typical laptop. Save/error status must use text, not colour alone.
- Empty states explain the next action: choose a vault, select a note or create the first note.

## 7. Initial shortcuts

Use Cmd on macOS and Ctrl on Windows/Linux. Prefer Qt's platform-aware standard key sequences where available.

| Shortcut | Action |
| --- | --- |
| Cmd/Ctrl+N | New note in the current destination |
| Cmd/Ctrl+S | Save |
| Cmd/Ctrl+F | Find in current note |
| Cmd/Ctrl+Shift+F | Search vault |
| Cmd/Ctrl+E | Toggle Edit/Read |
| Cmd/Ctrl+B / I | Apply bold/italic source syntax |
| Standard Undo/Redo shortcuts | Undo/redo edits |

Buttons must remain available for users who do not use shortcuts. Undo/redo applies to editor changes, not filesystem operations.

## 8. Suggested implementation and delivery

Use Python and PySide6 as the recommended starting point, separating vault operations, document saving/conflicts, link/search logic and UI. Choose a Markdown renderer and Trash integration suitable for the above contracts. Explain a material technology change briefly before adopting it; no paid services are permitted.

Provide a `pyproject.toml`, a clear runnable entry point, appropriate tests, and updated README instructions for setup, launch, tests, supported Python version and limitations. Verify the GUI actually launches on macOS; syntax checks alone do not establish that. Do not claim Windows/Linux validation until performed.

## 9. Acceptance checklist

- [x] App launches on macOS with the specified palette and an Open vault empty state.
- [x] Opening a synthetic existing vault preserves every file's contents before editing.
- [x] Root, nested and Unicode-named folders/notes can be created; filesystem entries and sidebar agree immediately.
- [x] Duplicate names, cancelled dialogs and write failures cause no overwrite or phantom entry.
- [x] Markdown editing, reading view, lists, tables and a local image work with a representative synthetic note.
- [x] Save, autosave, note switching and normal restart retain edits and produce readable `.md` files.
- [x] Rename/delete affect real entries; deletion uses Trash; unsaved text survives failures.
- [x] External edits/creation/removal refresh correctly; a conflicting edit preserves both versions.
- [x] Filename/content search and internal links work; missing/ambiguous links are handled clearly.
- [x] Traversal, symlink escape, scripts and remote-image requests are blocked without altering source notes.
- [x] Keyboard actions, focus visibility, resizing and save/error feedback are checked visually and functionally.
- [x] README launch instructions are tested; relevant automated tests pass; unverified behaviours are disclosed.
- [x] Git changes contain no personal vault, credentials, private settings or generated files.

## Obsidian reference behaviour

These official references explain the inspiration; the explicit scope above governs this implementation:

- [Vaults](https://help.obsidian.md/vault)
- [Editing and reading views](https://help.obsidian.md/edit-and-read)
- [Markdown syntax](https://help.obsidian.md/syntax)
- [Internal links](https://help.obsidian.md/links)
