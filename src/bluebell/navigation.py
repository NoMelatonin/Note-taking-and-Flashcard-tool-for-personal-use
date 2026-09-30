"""Reconstructible literal search and deliberately unambiguous note links."""

from dataclasses import dataclass
from pathlib import PurePosixPath

from bluebell.rendering import relative_target
from bluebell.vault import Entry, Vault, VaultError, name_key


class LinkError(VaultError):
    pass


@dataclass(frozen=True)
class SearchResult:
    path: str
    context: str
    unsaved: bool = False


@dataclass(frozen=True)
class SearchPage:
    results: tuple[SearchResult, ...]
    skipped: tuple[str, ...] = ()
    limited: bool = False


def resolve_link(vault: Vault, current: str, target: str, *, wiki=False, entries: tuple[Entry, ...] | None = None) -> str:
    notes = [entry.path for entry in (entries if entries is not None else vault.scan().entries) if not entry.folder]
    if wiki:
        target = target.partition("|")[0].strip()
        if not target or target.startswith("/") or "\\" in target or ":" in target or "\0" in target or ".." in PurePosixPath(target).parts:
            raise LinkError("This note link must name a note inside the vault.")
        target = target if target.lower().endswith(".md") else target + ".md"
        if "/" in target:
            matches = [note for note in notes if name_key(note) == name_key(target)]
        else:
            matches = [note for note in notes if name_key(PurePosixPath(note).name) == name_key(target)]
    else:
        try:
            target = relative_target(current, target)
        except ValueError as error:
            raise LinkError(str(error)) from error
        if not target.lower().endswith(".md"):
            raise LinkError("Only relative links to Markdown (.md) notes are supported here.")
        matches = [note for note in notes if name_key(note) == name_key(target)]
    if not matches:
        raise LinkError(f'No note matches "{target}". No file was created.')
    if len(matches) > 1:
        raise LinkError("This link is ambiguous. Use a vault-relative folder path:\n" + "\n".join(matches[:8]))
    try:
        vault.resolve(matches[0])
    except (OSError, VaultError) as error:
        raise LinkError("The linked note is missing, inaccessible or a symbolic link. Refresh the vault.") from error
    return matches[0]


def search_notes(vault: Vault, query: str, *, entries=None, overlay=None, limit=200, cancelled=lambda: False) -> SearchPage:
    if not query:
        return SearchPage(())
    needle = query.casefold()
    results, skipped = [], []
    notes = sorted((entry.path for entry in (entries if entries is not None else vault.scan().entries) if not entry.folder), key=name_key)
    overlay = overlay or {}
    for note in notes:
        if cancelled():
            break
        try:
            vault.resolve(note)
            text = overlay[note] if note in overlay else vault.read(note).data.decode("utf-8-sig")
        except (OSError, ValueError):
            skipped.append(note)
            continue
        matching_line = next((line for line in text.splitlines() if needle in line.casefold()), None)
        if matching_line is None and needle not in note.casefold():
            continue
        if len(results) == limit:
            return SearchPage(tuple(results), tuple(skipped), True)
        if matching_line is not None:
            start = max(0, matching_line.casefold().find(needle) - 60)
            context = ("…" if start else "") + matching_line[start:start + 180].strip()
            if start + 180 < len(matching_line):
                context += "…"
            context = context or "(blank line)"
        else:
            context = next((line.strip() for line in text.splitlines() if line.strip()), "Empty note")[:180]
        results.append(SearchResult(note, context, note in overlay))
    return SearchPage(tuple(results), tuple(skipped))
