from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage, QTextDocument
import pytest

from bluebell.rendering import MarkdownRenderer, SafePreview
from bluebell.vault import Vault


@pytest.fixture
def vault(sandbox):
    root = sandbox / "Vault"
    root.mkdir()
    return Vault(root)


def test_supported_markdown_and_checkboxes(vault):
    source = "# Heading\n\n**Bold** *Italic* ~~Strike~~ `code`\n\n- [x] Done\n- [ ] Pending\n  - Nested\n\n1. Ordered\n\n> Quote\n\n```python\nprint('safe')\n```\n\n---\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n"
    result = MarkdownRenderer().render(source, vault, "Note.md")
    for marker in ("<h1>", "<strong>", "<em>", "<s>", "<code>", "☑", "☐", "<ul", "<ol", "<blockquote>", "<pre>", "<hr", "<table>"):
        assert marker in result
    assert "<input" not in result


def test_untrusted_html_and_remote_images_are_not_resources(vault):
    source = '<script>alert(1)</script>\n\n<img src="https://example.invalid/track">\n\n![tracker](https://example.invalid/pixel.png)\n\n![data](data:image/png;base64,aA==)\n\n[bad](file:///etc/passwd)\n\n![[Note]]\n'
    result = MarkdownRenderer().render(source, vault, "Note.md")
    assert "<script>" not in result and "<img " not in result
    assert "&lt;script&gt;" in result
    assert "![[Note]]" in result
    assert 'href="file:' not in result


def test_image_load_is_bounded_and_never_delegates(qtbot, vault, sandbox):
    image = QImage(32, 32, QImage.Format_RGB32)
    image.fill(0xD4E8F5)
    image.save(str(vault.root / "safe.png"))
    outside = sandbox / "outside.png"
    image.save(str(outside))
    (vault.root / "alias.png").symlink_to(outside)
    (vault.root / "pretend.png").write_text('<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32"><image href="https://example.invalid/tracker"/></svg>')
    preview = SafePreview()
    qtbot.addWidget(preview)
    preview.show_markdown("![safe](safe.png)", vault, "Note.md")
    assert not preview.loadResource(QTextDocument.ImageResource, QUrl("vault-image:safe.png")).isNull()
    for url in ("https://example.invalid/track.png", "file:///etc/passwd", "vault-image:alias.png", "vault-image:..%2Foutside.png", "vault-image:pretend.png"):
        assert preview.loadResource(QTextDocument.ImageResource, QUrl(url)).isNull()
    assert not preview.openLinks() and not preview.openExternalLinks()


def test_reading_preserves_source_and_renders_local_image(qtbot, vault):
    image = QImage(8, 8, QImage.Format_RGB32)
    image.fill(0x416881)
    image.save(str(vault.root / "blue.png"))
    source = "# A note\r\n\r\n![blue](blue.png)\r\n"
    (vault.root / "Note.md").write_bytes(source.encode())
    preview = SafePreview()
    qtbot.addWidget(preview)
    preview.show_markdown(source, vault, "Note.md")
    assert "A note" in preview.toPlainText()
    resource = preview.document().resource(QTextDocument.ImageResource, QUrl("vault-image:blue.png"))
    assert isinstance(resource, QImage) and not resource.isNull()
    assert (vault.root / "Note.md").read_bytes() == source.encode()
