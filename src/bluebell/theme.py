"""Reference light palette: white canvas, neutral gray chrome and charcoal text."""

STYLE = """
QWidget { color: #2E2E2E; font-size: 13px; }
QLineEdit, QPlainTextEdit { placeholder-text-color: #666666; }
QMainWindow, QWidget#canvas, QWidget#shell { background: #FFFFFF; }
QWidget#sidebar, QWidget#rail { background: #F6F6F6; }
QWidget#rail { border-right: 1px solid #E5E5E5; }
QWidget#sidebarHeader, QWidget#tabStrip { background: #FAFAFA; border-bottom: 1px solid #E5E5E5; }
QWidget#vaultFooter { border-top: 1px solid #E5E5E5; }
QWidget#activeTab { background: #FFFFFF; border: 1px solid #E5E5E5;
  border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QLabel#tabLabel, QLabel#breadcrumb { font-size: 12px; }
QLabel#vaultName { font-size: 12px; font-weight: 600; }
QLabel#hint, QLabel#breadcrumb { color: #666666; }
QLabel#emptyTitle { font-size: 26px; font-weight: 600; }
QLabel#noteHeading { font-size: 28px; font-weight: 600; padding: 0px 0px 12px 0px; }
QPushButton { background: #F6F6F6; border: 1px solid #DDDDDD;
  border-radius: 6px; padding: 6px 10px; }
QPushButton:hover { background: #E7E7E7; }
QPushButton:checked { background: #E7E7E7; border: 1px solid #737373; }
QPushButton#iconButton { background: transparent; border: none; padding: 4px; border-radius: 5px; }
QPushButton#iconButton:hover, QPushButton#iconButton[active="true"] { background: #ECECEC; }
QPushButton#iconButton:focus { background: #E7E7E7; }
QPushButton#iconButton::menu-indicator { image: none; width: 0px; }
QPushButton#primary { background: #555555; color: #FFFFFF; border: 1px solid #555555; }
QPushButton#primary:hover { background: #444444; }
QPushButton:disabled { color: #666666; }
QPushButton:focus, QLineEdit:focus { border: 1px solid #737373; }
QLineEdit { background: #FFFFFF; border: 1px solid #DDDDDD;
  border-radius: 5px; padding: 6px; }
QTreeWidget, QListWidget { background: #F6F6F6; border: none; padding: 8px 10px; }
QTreeWidget::item, QListWidget::item { padding: 3px 4px; min-height: 21px; border-radius: 4px; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #E7E7E7; color: #2E2E2E; }
QTreeWidget::item:hover, QListWidget::item:hover { background: #EEEEEE; }
QTreeWidget::item:focus, QListWidget::item:focus { outline: 1px solid #737373; }
QPlainTextEdit, QTextBrowser { background: #FFFFFF; border: none; padding: 0px;
  selection-background-color: #EDE6FD; selection-color: #2E2E2E; }
QStatusBar { background: #FFFFFF; color: #666666; font-size: 11px; min-height: 20px; }
QStatusBar QLabel { font-size: 11px; }
QStatusBar::item { border: none; }
QSplitter::handle { background: #E5E5E5; width: 1px; }
QSplitter::handle:hover { background: #737373; }
QMenu, QDialog, QMessageBox { background: #FFFFFF; }
QMenu { border: 1px solid #DDDDDD; padding: 4px; }
QMenu::item { padding: 7px 20px; }
QMenu::item:selected { background: #E7E7E7; }
QFrame#notice { background: #E7E7E7; border: 1px solid #737373; border-radius: 6px; }
QScrollBar:vertical { background: transparent; width: 6px; margin: 0px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar::handle:vertical { background: #DDDDDD; border-radius: 3px; min-height: 25px; }
QToolTip { background: #FFFFFF; color: #2E2E2E; border: 1px solid #DDDDDD; padding: 4px; }
"""
