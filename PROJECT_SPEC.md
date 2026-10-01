# Local notes and flashcards — project specification

Status: Milestone 1 implemented and verified on macOS, 30 September 2026. Python/PySide6 selected; the temporary app name is Bluebell. See PLAN.md and docs/VERIFICATION.md. Later-milestone technology choices remain proposals.

Project: Remnote-Obsidian rebuild.

Canonical repository: `/Users/max/Desktop/Second-Brain/Own Projects/Remnote-Obsidian rebuild`. All future authored project files belong in this repository.

## Agreed requirements

- Start with a macOS desktop app. Choose portable components so Windows and Linux versions can share the codebase; each platform still requires its own packaging and testing.
- A vault is an ordinary local folder containing folders and Markdown text files.
- Provide an Obsidian-style Markdown editor. Files remain readable and editable outside the app.
- UI refinement, 1 October 2026: follow the supplied workspace screenshot with a compact icon rail/sidebar, slim active-note tab/header, bottom vault selector, filename heading and centered frameless writing column; match the reference light palette (white canvas, light-gray sidebar, charcoal text and gray selections). Multiple tabs remain deferred.
- First deliverable: a friendly desktop note-taking interface with the supplied screenshot's white and neutral-gray palette (refined 1 October 2026). Vault folders and notes are real filesystem entries, created immediately from the app.
- Support references between notes and a clickable graph showing their connections.
- Generate question–answer flashcards from completed note bullets, with generation running in the background.
- Provide a separate card interface and spaced repetition: difficult or forgotten cards return sooner; successfully remembered cards receive longer intervals.
- Use local AI with no required AI subscription or per-request service fees. Immediate generation and offline operation are not requirements.
- Develop collaboratively using Codex in VS Code. The user makes product decisions and tries each milestone; Codex handles most implementation and verification.

## Proposed implementation

These are recommendations, not settled requirements:

- Python for application logic, PySide6 for the desktop interface — selected and implemented for Milestone 1.
- Markdown files as the authoritative note storage; SQLite for cards and review history.
- `[[note links]]` for references and backlinks.
- Ollama with a locally downloaded model for background card generation. Select the model after checking available memory and evaluating sample cards.
- Store persistent card identities and source references so note edits do not create duplicate cards or erase review history.
- Make generated cards editable; decide later whether drafts need approval before review.

## Development milestones

1. **Note-taking system:** vault selection, folder tree, new folders and Markdown files at any depth, editing and reading views, safe autosave, search, basic note links and the requested colour scheme. Follow `docs/MILESTONE_1.md` for the precise scope and acceptance criteria. Done when the complete first-milestone workflow is verified.
2. **Knowledge graph:** display a clickable graph and add richer backlink navigation. Done when graph connections reflect saved notes.
3. **Cards and review:** manually create/edit cards to establish the source mapping, then implement persistent scheduling and a due-card review screen. Done when ratings affect future reviews and history survives an app restart.
4. **Background generation:** add the local model, a generation queue and editable questions and answers. Done when generation leaves the editor responsive and repeated processing does not duplicate cards.
5. **Distribution:** package a Mac app, then build and test Windows and Linux packages. Consider Mac signing/notarization when offering downloads publicly.

For each milestone: explain the design, implement, verify, let the user try it, and create a Git checkpoint.

## Decisions to revisit

- App display name, if different from the repository name.
- Obsidian-like inline Live Preview after the initial source editor and reading view. The initial editing modes are an explicit first-milestone default, not a claim of full Obsidian parity.
- What marks a bullet as complete and eligible for generation, including nested bullets and surrounding context.
- What happens to cards when their source bullets are changed or deleted.
- Existing-note imports, backup workflow and supported operating-system versions.

## Implementation entry point

- `README.md`: overview and how to start the Codex implementation task.
- `AGENTS.md`: working rules, location and security requirements.
- `PLAN.md`: staged implementation and verification progress.
- `docs/MILESTONE_1.md`: first-deliverable requirements and acceptance criteria.
- `docs/VERIFICATION.md`: acceptance evidence, tested environment and limitations.
- `Launch.command`: local macOS development launcher after setup.

The first task is the note-taking system only. Graphs, flashcards, AI, cloud sync, plugins and public distribution remain subsequent work.

## Distribution and local-AI references

- [Qt for Python deployment](https://doc.qt.io/qtforpython-6/deployment/index.html): desktop support for macOS, Windows and Linux.
- [PyInstaller operating model](https://pyinstaller.org/en/stable/operating-mode.html): packaged output is specific to the build operating system.
- [Apple Developer ID certificates](https://developer.apple.com/help/account/certificates/create-developer-id-certificates/): signing and notarization for downloads outside the Mac App Store.
- [Apple Developer Program enrollment](https://developer.apple.com/programs/enroll/): standard membership is USD 99 per year, with regional pricing and eligible fee waivers.
- [Ollama quickstart](https://docs.ollama.com/quickstart): local models run without a cloud API key.

Development and personal use of this Python desktop app do not require paid Apple Developer Program membership. Public Mac distribution with Developer ID signing and Apple notarization normally does. Local inference avoids AI service fees but still uses the user's hardware and electricity.
