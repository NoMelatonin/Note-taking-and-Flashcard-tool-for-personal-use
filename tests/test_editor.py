from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from bluebell.editor import MarkdownEditor


def editor_at_end(qtbot, text):
    editor = MarkdownEditor()
    qtbot.addWidget(editor)
    editor.setPlainText(text)
    editor.moveCursor(QTextCursor.End)
    return editor


def test_list_continuation_exit_indent_and_undo(qtbot):
    editor = editor_at_end(qtbot, "- First")
    qtbot.keyClick(editor, Qt.Key_Return)
    assert editor.toPlainText() == "- First\n- "
    qtbot.keyClick(editor, Qt.Key_Return)
    assert editor.toPlainText() == "- First\n"
    editor.undo()
    assert editor.toPlainText() == "- First\n- "
    qtbot.keyClick(editor, Qt.Key_Tab)
    assert editor.toPlainText().endswith("  - ")
    assert editor.textCursor().position() == len(editor.toPlainText())
    qtbot.keyClick(editor, Qt.Key_Backtab)
    assert editor.toPlainText().endswith("\n- ")


def test_numbered_and_task_lists(qtbot):
    editor = editor_at_end(qtbot, "  9. Done")
    qtbot.keyClick(editor, Qt.Key_Return)
    assert editor.toPlainText() == "  9. Done\n  10. "
    editor.setPlainText("- [x] Done")
    editor.moveCursor(QTextCursor.End)
    qtbot.keyClick(editor, Qt.Key_Return)
    assert editor.toPlainText() == "- [x] Done\n- [ ] "


def test_fenced_code_does_not_continue_markdown_lists(qtbot):
    editor = editor_at_end(qtbot, "```text\n- Code")
    qtbot.keyClick(editor, Qt.Key_Return)
    assert editor.toPlainText() == "```text\n- Code\n"


def test_bold_italic_and_atomic_undo(qtbot):
    editor = editor_at_end(qtbot, "Thought")
    editor.selectAll()
    editor.wrap_selection("**")
    assert editor.toPlainText() == "**Thought**"
    editor.undo()
    assert editor.toPlainText() == "Thought"
    editor.redo()
    assert editor.toPlainText() == "**Thought**"
    editor.selectAll()
    editor.wrap_selection("**")
    assert editor.toPlainText() == "Thought"
