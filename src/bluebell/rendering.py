"""Untrusted Markdown -> restricted QTextBrowser content, without WebEngine."""

import html
from pathlib import PurePosixPath
import posixpath
from urllib.parse import quote, unquote, urlsplit

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin
from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt, QUrl
from PySide6.QtGui import QImage, QImageReader, QTextDocument
from PySide6.QtWidgets import QTextBrowser

from bluebell.vault import MAX_IMAGE_BYTES, VaultError

RASTER_TYPES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def relative_target(current: str, target: str) -> str:
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or target.startswith(("/", "\\")):
        raise VaultError("Only relative paths inside the vault are allowed.")
    decoded = unquote(parsed.path)
    if not decoded or "\\" in decoded or ":" in decoded or "\0" in decoded or decoded.startswith("/"):
        raise VaultError("Unsafe relative path.")
    relative = posixpath.normpath(str(PurePosixPath(current).parent / decoded))
    if relative == ".." or relative.startswith("../"):
        raise VaultError("The link would leave the selected vault.")
    return relative


def wiki_rule(state, silent):
    start = state.pos
    if not state.src.startswith("[[", start) or (start and state.src[start - 1] == "!"):
        return False
    end = state.src.find("]]", start + 2, state.posMax)
    if end < 0:
        return False
    value = state.src[start + 2:end]
    if not value or "\n" in value:
        return False
    if not silent:
        target, separator, label = value.partition("|")
        token = state.push("link_open", "a", 1)
        token.attrSet("href", "bluebell-wiki:" + quote(target.strip(), safe=""))
        state.push("text", "", 0).content = label if separator else target
        state.push("link_close", "a", -1)
    state.pos = end + 2
    return True


class MarkdownRenderer:
    def __init__(self):
        self.parser = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
        self.parser.use(tasklists_plugin)
        self.parser.inline.ruler.before("link", "wiki_link", wiki_rule)
        self.parser.add_render_rule("image", self._image)
        self.parser.add_render_rule("link_open", self._link)
        self.parser.add_render_rule("html_inline", self._checkbox)

    @staticmethod
    def _link(renderer, tokens, index, options, env):
        token = tokens[index]
        target = token.attrGet("href") or ""
        try:
            parsed = urlsplit(target)
        except ValueError:
            token.attrSet("href", "bluebell-blocked:")
            return renderer.renderToken(tokens, index, options, env)
        if parsed.scheme == "bluebell-wiki":
            pass
        elif parsed.scheme in {"http", "https"} and parsed.netloc:
            pass
        elif not parsed.scheme and not parsed.netloc and not target.startswith("//"):
            token.attrSet("href", "bluebell-note:" + quote(target, safe=""))
        else:
            token.attrSet("href", "bluebell-blocked:" + quote(target, safe=""))
        return renderer.renderToken(tokens, index, options, env)

    @staticmethod
    def _checkbox(renderer, tokens, index, options, env):
        content = tokens[index].content
        if content.startswith('<input class="task-list-item-checkbox"'):
            return "☑ " if 'checked="checked"' in content else "☐ "
        return html.escape(content)

    @staticmethod
    def _image(renderer, tokens, index, options, env):
        token = tokens[index]
        description = token.content
        try:
            relative = relative_target(env["current"], token.attrGet("src") or "")
            env["vault"].resolve(relative)
            if PurePosixPath(relative).suffix.lower() not in RASTER_TYPES:
                raise VaultError("Only local raster images are supported.")
        except (OSError, ValueError):
            return '<span style="color: #526979">[' + html.escape(description) + " · image unavailable or blocked]</span>"
        return '<img src="vault-image:' + quote(relative, safe="") + '" alt="' + html.escape(description, quote=True) + '" />'

    def render(self, source: str, vault, current: str) -> str:
        return self.parser.render(source, {"vault": vault, "current": current})


class SafePreview(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.vault = None
        self.renderer = MarkdownRenderer()
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.setSearchPaths([])
        self.setAccessibleName("Formatted Markdown reading view")
        self.document().setDefaultStyleSheet("""
            body { color: #2C4252; font-size: 16px; }
            h1 { font-size: 28px; } h2 { font-size: 22px; } h3 { font-size: 18px; }
            a { color: #416881; text-decoration: underline; }
            pre { background-color: #E6EEF3; white-space: pre-wrap; }
            code { font-family: monospace; background-color: #E6EEF3; }
            blockquote { color: #526979; margin-left: 20px; }
            table { border-collapse: collapse; } th, td { padding: 8px; border: 1px solid #C7D4DD; }
        """)

    def show_markdown(self, source: str, vault, current: str):
        self.vault = vault
        # A new document also drops previously cached local-image resources.
        document = QTextDocument(self)
        document.setDefaultStyleSheet(self.document().defaultStyleSheet())
        self.setDocument(document)
        self.setHtml(self.renderer.render(source, vault, current))

    def loadResource(self, kind, name):
        # Never delegate to QTextBrowser's arbitrary file/resource loader.
        if kind != QTextDocument.ImageResource or name.scheme() != "vault-image" or self.vault is None:
            return QImage()
        try:
            relative = unquote(name.toString(QUrl.FullyEncoded).split(":", 1)[1])
            if PurePosixPath(relative).suffix.lower() not in RASTER_TYPES:
                return QImage()
            data = self.vault.read(relative, limit=MAX_IMAGE_BYTES).data
            buffer = QBuffer()
            buffer.setData(QByteArray(data))
            buffer.open(QIODevice.ReadOnly)
            reader = QImageReader(buffer)
            if bytes(reader.format()).lower() not in {b"png", b"jpeg", b"jpg", b"gif", b"bmp", b"webp"}:
                return QImage()
            size = reader.size()
            if size.width() <= 0 or size.height() <= 0 or size.width() * size.height() > 24_000_000:
                return QImage()
            image = reader.read()
            if image.width() > 720 or image.height() > 640:
                image = image.scaled(720, 640, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            return image
        except (OSError, ValueError):
            return QImage()
