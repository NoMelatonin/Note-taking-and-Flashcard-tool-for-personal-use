# Project instructions

## Location and collaboration

- Canonical project directory: `/Users/max/Desktop/Second-Brain/Own Projects/Remnote-Obsidian rebuild`.
- Put all authored project files here, including source, documentation, tests, assets, deliverables and scratch work. Use `work/` for temporary work.
- Do not create project files in the old generated Codex chat directory.
- Read `PROJECT_SPEC.md` before implementing. Keep settled requirements and progress documented in the repository.
- For the first task, also read `docs/MILESTONE_1.md` and `PLAN.md`. Implement the scoped note-taking system; do not expand into the later graph or flashcard milestones.
- Treat the editing modes, colours and shortcuts in the milestone document as initial implementation defaults. Explain any meaningful departure before making it.
- Give short, precise answers. Explain important design decisions so the user can participate without writing much code.
- Develop in small, runnable milestones; verify the relevant behaviour and let the user try the result.

## Requirements

- macOS first; portable components for later Windows and Linux builds.
- Notes are ordinary local Markdown files, with inter-note references and a graph view.
- Flashcards link back to source bullets and retain review history across edits.
- Card generation runs locally in the background, with no required paid AI service or cloud API.
- Technology choices in the specification remain proposals until settled.
- First-milestone UI: baby-blue accents, dimmed-white surfaces, readable dark text, a vault folder sidebar and Markdown source/reading views.
- Vault changes must affect real folders/files immediately; never substitute a database or in-memory representation for the note files.

## Security and Git hygiene

- Proactively tell the user about concrete security issues and relevant security implications of changes. Explain the issue and practical fix briefly.
- Never commit credentials, tokens, passwords, private keys, real personal vaults or personal review data. Never print secret values in tool output or logs.
- Keep `.env` and secret-bearing variants ignored. An `.env.example` may contain placeholders only.
- Check ignore coverage before creating secret-bearing or private runtime files. Put development runtime data under ignored `.local/`.
- Before committing or pushing, inspect changed files for accidental secrets and personal data. Ignoring a file does not untrack it or remove it from Git history.
- If credentials were committed or exposed, report it without repeating the secret and recommend revocation or rotation; removing the file is insufficient.
- Preserve existing user files and changes. Do not publish project contents or push to GitHub unless the user authorizes it.
- Treat Markdown as untrusted input: render without scripts, automatic remote requests or arbitrary file access. Do not follow symlinks outside the selected vault.
- Never use the user's actual study vault to test file writes, rename or deletion. Use an isolated synthetic vault under ignored `work/`.
