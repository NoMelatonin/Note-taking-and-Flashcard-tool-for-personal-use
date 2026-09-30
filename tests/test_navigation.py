import pytest

from bluebell.navigation import LinkError, resolve_link, search_notes
from bluebell.vault import Vault


@pytest.fixture
def vault(sandbox):
    root = sandbox / "Vault"
    (root / "Ideas").mkdir(parents=True)
    (root / "Reading").mkdir()
    for relative, text in {"Home.md": "# Home\n\nLiteral *stars* and Grüße\n", "Ideas/Shared.md": "# First shared\n", "Reading/Shared.md": "# Second shared\n", "Ideas/Unique.md": "# A thought\n\n" + "x" * 250 + " NeedLE context\n", "100% real.md": "percent\n"}.items():
        (root / relative).write_text(text, encoding="utf-8")
    return Vault(root)


def test_wiki_links_unique_explicit_optional_extension_and_alias(vault):
    assert resolve_link(vault, "Home.md", "Unique", wiki=True) == "Ideas/Unique.md"
    assert resolve_link(vault, "Home.md", "ideas/shared.md|Label", wiki=True) == "Ideas/Shared.md"
    assert resolve_link(vault, "Home.md", "100% real", wiki=True) == "100% real.md"
    with pytest.raises(LinkError, match="ambiguous"):
        resolve_link(vault, "Home.md", "Shared", wiki=True)
    with pytest.raises(LinkError, match="No note"):
        resolve_link(vault, "Home.md", "Missing", wiki=True)
    assert not (vault.root / "Missing.md").exists()


def test_relative_markdown_links_stay_inside_vault(vault):
    assert resolve_link(vault, "Ideas/Unique.md", "../Home.md") == "Home.md"
    assert resolve_link(vault, "Home.md", "100%25%20real.md") == "100% real.md"
    for target in ("../../outside.md", "%2e%2e/outside.md", "/etc/passwd.md", "file:///etc/passwd.md", "javascript:alert(1)", "//host/file.md", "https://example.invalid/note.md"):
        with pytest.raises(LinkError):
            resolve_link(vault, "Home.md", target)
    for target in ("../Home", "Ideas/../Home", "C:\\Home", "/Home"):
        with pytest.raises(LinkError):
            resolve_link(vault, "Home.md", target, wiki=True)


def test_search_filenames_content_literal_case_and_context(vault):
    assert {result.path for result in search_notes(vault, "SHARED").results} == {"Ideas/Shared.md", "Reading/Shared.md"}
    result = search_notes(vault, "needle").results[0]
    assert result.path == "Ideas/Unique.md" and "NeedLE context" in result.context
    assert result.context.startswith("…")
    assert [result.path for result in search_notes(vault, "*stars*").results] == ["Home.md"]
    assert [result.path for result in search_notes(vault, "GRÜSSE").results] == ["Home.md"]
    assert not search_notes(vault, "not here").results


def test_search_skips_symlinks_invalid_utf8_and_hidden_folders(vault, sandbox):
    outside = sandbox / "Outside.md"
    outside.write_text("Needle private synthetic\n")
    (vault.root / "Alias.md").symlink_to(outside)
    (vault.root / "Invalid.md").write_bytes(b"\xff")
    (vault.root / ".hidden").mkdir()
    (vault.root / ".hidden" / "Secret.md").write_text("Needle")
    page = search_notes(vault, "needle")
    assert [match.path for match in page.results] == ["Ideas/Unique.md"]
    assert page.skipped == ("Invalid.md",)


def test_search_unsaved_overlay_limit_and_cancellation(vault):
    page = search_notes(vault, "draft", overlay={"Home.md": "A new draft\n"})
    assert page.results[0].unsaved and page.results[0].context == "A new draft"
    page = search_notes(vault, "shared", limit=1)
    assert len(page.results) == 1 and page.limited
    assert not search_notes(vault, "shared", cancelled=lambda: True).results


def test_stale_index_does_not_follow_new_symlink(vault, sandbox):
    entries = vault.scan().entries
    note = vault.root / "Home.md"
    note.unlink()
    outside = sandbox / "Outside.md"
    outside.write_text("private synthetic")
    note.symlink_to(outside)
    with pytest.raises(LinkError, match="symbolic link"):
        resolve_link(vault, "Ideas/Unique.md", "Home", wiki=True, entries=entries)
    assert not search_notes(vault, "private", entries=entries).results
