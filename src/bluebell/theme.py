"""Compact workspace chrome and warm, frameless writing surfaces."""

STYLE = """
QWidget { color: #2C4252; font-size: 13px; }
QLineEdit, QPlainTextEdit { placeholder-text-color: #496070; }
QMainWindow, QWidget#canvas, QWidget#shell { background: #E5DFD2; }
QWidget#sidebar, QWidget#rail { background: #DDD8CC; }
QWidget#rail { border-right: 1px solid #CFC9BE; }
QWidget#sidebarHeader, QWidget#tabStrip { background: #DFDACE; border-bottom: 1px solid #CFC9BE; }
QWidget#vaultFooter { border-top: 1px solid #CFC9BE; }
QWidget#activeTab { background: #E5DFD2; border: 1px solid #CFC9BE;
  border-bottom: none; border-top-left-radius: 6px; border-top-right-radius: 6px; }
QLabel#tabLabel, QLabel#breadcrumb { font-size: 12px; }
QLabel#vaultName { font-size: 12px; font-weight: 600; }
QLabel#hint, QLabel#breadcrumb { color: #496070; }
QLabel#emptyTitle { font-size: 26px; font-weight: 600; }
QLabel#noteHeading { font-size: 28px; font-weight: 600; padding: 0px 0px 12px 0px; }
QPushButton { background: #DDD8CC; border: 1px solid #C7C2B7;
  border-radius: 6px; padding: 6px 10px; }
QPushButton:hover { background: #D4E8F5; }
QPushButton:checked { background: #D4E8F5; border: 1px solid #416881; }
QPushButton#iconButton { background: transparent; border: none; padding: 4px; border-radius: 5px; }
QPushButton#iconButton:hover, QPushButton#iconButton[active="true"] { background: #CDC9BF; }
QPushButton#iconButton:focus { background: #D4E8F5; }
QPushButton#iconButton::menu-indicator { image: none; width: 0px; }
QPushButton#primary { background: #416881; color: #EFE9DD; border: 1px solid #416881; }
QPushButton#primary:hover { background: #35566D; }
QPushButton:disabled { color: #496070; }
QPushButton:focus, QLineEdit:focus { border: 1px solid #416881; }
QLineEdit { background: #E5DFD2; border: 1px solid #C7C2B7;
  border-radius: 5px; padding: 6px; }
QTreeWidget, QListWidget { background: #DDD8CC; border: none; padding: 8px 10px; }
QTreeWidget::item, QListWidget::item { padding: 3px 4px; min-height: 21px; border-radius: 4px; }
QTreeWidget::item:selected, QListWidget::item:selected { background: #D4E8F5; color: #2C4252; }
QTreeWidget::item:hover, QListWidget::item:hover { background: #D5D0C5; }
QTreeWidget::item:focus, QListWidget::item:focus { outline: 1px solid #416881; }
QPlainTextEdit, QTextBrowser { background: #E5DFD2; border: none; padding: 0px;
  selection-background-color: #D4E8F5; selection-color: #2C4252; }
QStatusBar { background: #E5DFD2; color: #496070; font-size: 11px; min-height: 20px; }
QStatusBar QLabel { font-size: 11px; }
QStatusBar::item { border: none; }
QSplitter::handle { background: #CFC9BE; width: 1px; }
QSplitter::handle:hover { background: #416881; }
QMenu, QDialog, QMessageBox { background: #E5DFD2; }
QMenu { border: 1px solid #C7C2B7; padding: 4px; }
QMenu::item { padding: 7px 20px; }
QMenu::item:selected { background: #D4E8F5; }
QFrame#notice { background: #D4E8F5; border: 1px solid #416881; border-radius: 6px; }
QScrollBar:vertical { background: transparent; width: 6px; margin: 0px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; border: none; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar::handle:vertical { background: #C7C2B7; border-radius: 3px; min-height: 25px; }
QToolTip { background: #E5DFD2; color: #2C4252; border: 1px solid #C7C2B7; padding: 4px; }
"""
