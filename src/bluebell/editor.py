"""Markdown source editor with light list behavior and ordinary Qt undo/redo."""

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontDatabase, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

LIST = re.compile(r"^(\s*)([-+*]|\d+[.)])\s+(\[[ xX]\]\s+)?(.*)$")


class MarkdownEditor(QPlainTextEdit):
    linkRequested = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.setTabChangesFocus(True)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.setAccessibleName("Markdown source editor")
        self.setPlaceholderText("Start with a thought…")

    def wrap_selection(self, marker):
        cursor = self.textCursor()
        selected = cursor.selectedText() or "text"
        start = cursor.selectionStart()
        cursor.beginEditBlock()
        if selected.startswith(marker) and selected.endswith(marker) and len(selected) >= 2 * len(marker):
            selected = selected[len(marker):-len(marker)]
            cursor.insertText(selected)
            cursor.setPosition(start)
            cursor.setPosition(start + len(selected), QTextCursor.KeepAnchor)
        else:
            cursor.insertText(marker + selected + marker)
            cursor.setPosition(start + len(marker))
            cursor.setPosition(start + len(marker) + len(selected), QTextCursor.KeepAnchor)
        cursor.endEditBlock()
        self.setTextCursor(cursor)
        self.setFocus()

    def _inside_fence(self):
        before = self.toPlainText()[:self.textCursor().block().position()]
        fence = None
        for line in before.splitlines():
            match = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
            if match:
                marker = match.group(1)
                if fence is None:
                    fence = marker
                elif marker[0] == fence[0] and len(marker) >= len(fence):
                    fence = None
        return fence is not None

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        match = LIST.match(cursor.block().text())
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() and match and not cursor.hasSelection() and not self._inside_fence():
            indent, marker, task, content = match.groups()
            if cursor.positionInBlock() >= match.start(4):
                cursor.beginEditBlock()
                if not content.strip():
                    cursor.movePosition(QTextCursor.StartOfBlock)
                    cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                    cursor.removeSelectedText()
                else:
                    if marker[0].isdigit():
                        marker = str(int(marker[:-1]) + 1) + marker[-1]
                    cursor.insertText("\n" + indent + marker + " " + ("[ ] " if task else ""))
                cursor.endEditBlock()
                self.setTextCursor(cursor)
                return
        if event.key() in (Qt.Key_Tab, Qt.Key_Backtab) and (match or cursor.hasSelection()) and not self._inside_fence():
            start, end = cursor.selectionStart(), cursor.selectionEnd()
            first = self.document().findBlock(start)
            last = self.document().findBlock(max(start, end - 1))
            blocks = []
            block = first
            while block.isValid() and block.position() <= last.position():
                blocks.append(block)
                block = block.next()
            if any(LIST.match(block.text()) for block in blocks):
                preserved = QTextCursor(cursor)
                backwards = event.key() == Qt.Key_Backtab or bool(event.modifiers() & Qt.ShiftModifier)
                cursor.beginEditBlock()
                for block in reversed(blocks):
                    cursor.setPosition(block.position())
                    if backwards:
                        count = 1 if block.text().startswith("\t") else min(2, len(block.text()) - len(block.text().lstrip(" ")))
                        cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, count)
                        cursor.removeSelectedText()
                    else:
                        cursor.insertText("  ")
                cursor.endEditBlock()
                self.setTextCursor(preserved)
                return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            cursor = self.cursorForPosition(event.position().toPoint())
            line, position = cursor.block().text(), cursor.positionInBlock()
            for match in re.finditer(r"(?<!!)\[\[([^]\n]+)\]\]|(?<!!)\[[^]\n]*\]\(([^)\n]+)\)", line):
                if match.start() <= position <= match.end():
                    self.linkRequested.emit((match.group(1).split("|", 1)[0] if match.group(1) else match.group(2)).strip(), bool(match.group(1)))
                    return
        super().mousePressEvent(event)
