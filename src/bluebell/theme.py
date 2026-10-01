"""Warm cream surfaces with quiet baby-blue accents."""

STYLE = """
QWidget { color: #2C4252; font-size: 15px; }
QLineEdit, QPlainTextEdit { placeholder-text-color: #496070; }
QMainWindow, QWidget#canvas { background: #E5DFD2; }
QWidget#sidebar { background: #DDD8CC; }
QLabel#brand { font-size: 23px; font-weight: 600; }
QLabel#subtitle, QLabel#hint { color: #496070; }
QLabel#emptyTitle { font-size: 28px; font-weight: 600; }
QPushButton { background: #DDD8CC; border: 1px solid #C7C2B7;
  border-radius: 7px; padding: 8px 12px; }
QPushButton:hover { background: #D4E8F5; }
QPushButton:checked { background: #D4E8F5; border: 1px solid #416881; }
QPushButton#primary { background: #416881; color: #EFE9DD; border: 1px solid #416881; }
QPushButton#primary:hover { background: #35566D; }
QPushButton:disabled { color: #496070; background: #DDD8CC; }
QPushButton:focus, QLineEdit:focus { border: 2px solid #416881; }
QLineEdit { background: #E5DFD2; border: 1px solid #C7C2B7;
  border-radius: 6px; padding: 8px; }
QTreeWidget, QListWidget { background: #DDD8CC; border: none; padding: 0px; }
QTreeWidget::item:focus, QListWidget::item:focus { outline: 1px solid #416881; }
QTreeWidget::item, QListWidget::item { padding: 7px 3px; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #D4E8F5; color: #2C4252; }
QTreeWidget::item:hover, QListWidget::item:hover { background: #D4E8F5; }
QPlainTextEdit, QTextBrowser { background: #E5DFD2; border: none; padding: 8px; selection-background-color: #D4E8F5;
  selection-color: #2C4252; }
QStatusBar { background: #DDD8CC; color: #496070; }
QSplitter::handle { background: #E5DFD2; width: 5px; }
QSplitter::handle:hover { background: #D4E8F5; }
QMenu, QDialog, QMessageBox { background: #E5DFD2; }
QMenu::item { padding: 8px 20px; }
QMenu::item:selected { background: #D4E8F5; }
QFrame#notice { background: #D4E8F5; border: 1px solid #416881; border-radius: 6px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 0px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar::handle:vertical { background: #C7C2B7; border-radius: 5px; min-height: 25px; }
"""
