"""The milestone's original low-glare palette."""

STYLE = """
QWidget { color: #2C4252; font-size: 15px; }
QLineEdit, QPlainTextEdit { placeholder-text-color: #526979; }
QMainWindow, QWidget#canvas { background: #F1F3F4; }
QWidget#sidebar { background: #E6EEF3; }
QLabel#brand { font-size: 23px; font-weight: 600; }
QLabel#subtitle, QLabel#hint { color: #526979; }
QLabel#emptyTitle { font-size: 28px; font-weight: 600; }
QPushButton { background: #E6EEF3; border: 1px solid #C7D4DD;
  border-radius: 7px; padding: 8px 12px; }
QPushButton:hover { background: #D4E8F5; }
QPushButton:checked { background: #D4E8F5; border: 1px solid #416881; }
QPushButton#primary { background: #416881; color: #F1F3F4; border: 1px solid #416881; }
QPushButton#primary:hover { background: #35566D; }
QPushButton:disabled { color: #526979; background: #E6EEF3; }
QPushButton:focus, QLineEdit:focus, QTreeWidget:focus, QPlainTextEdit:focus,
QTextBrowser:focus, QListWidget:focus { border: 2px solid #416881; }
QLineEdit { background: #F1F3F4; border: 1px solid #C7D4DD;
  border-radius: 6px; padding: 8px; }
QTreeWidget, QListWidget { background: #E6EEF3; border: 1px solid #C7D4DD;
  border-radius: 6px; padding: 4px; }
QTreeWidget::item, QListWidget::item { padding: 7px 3px; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #D4E8F5; color: #2C4252; }
QTreeWidget::item:hover, QListWidget::item:hover { background: #D4E8F5; }
QPlainTextEdit, QTextBrowser { background: #F1F3F4; border: 1px solid #C7D4DD;
  border-radius: 7px; padding: 16px; selection-background-color: #D4E8F5;
  selection-color: #2C4252; }
QStatusBar { background: #E6EEF3; color: #526979; }
QSplitter::handle { background: #C7D4DD; width: 3px; }
QMenu, QDialog, QMessageBox { background: #F1F3F4; }
QMenu::item { padding: 8px 20px; }
QMenu::item:selected { background: #D4E8F5; }
QFrame#notice { background: #D4E8F5; border: 1px solid #416881; border-radius: 6px; }
QScrollBar:vertical { background: #E6EEF3; width: 12px; }
QScrollBar::handle:vertical { background: #C7D4DD; border-radius: 5px; min-height: 25px; }
"""
