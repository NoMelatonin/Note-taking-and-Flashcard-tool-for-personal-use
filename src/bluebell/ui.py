"""Native desktop UI over a filesystem vault and one active document."""

from pathlib import Path, PurePosixPath
from threading import Event
from urllib.parse import unquote, urlsplit

from PySide6.QtCore import Qt, QThreadPool, QTimer, QUrl, QSignalBlocker
from PySide6.QtGui import QActionGroup, QColor, QDesktopServices, QKeySequence, QShortcut, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton, QSplitter,
    QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from bluebell.icons import icon_button, line_icon
from bluebell.document import Document
from bluebell.editor import MarkdownEditor
from bluebell.navigation import resolve_link, search_notes
from bluebell.rendering import SafePreview
from bluebell.settings import load_settings, save_settings
from bluebell.theme import STYLE
from bluebell.vault import Vault, VaultError
from bluebell.workers import Work


def plain_label(text="", **kwargs):
    label = QLabel(text, **kwargs)
    label.setTextFormat(Qt.PlainText)
    return label


class VaultTree(QTreeWidget):
    """Folder rows toggle across their entire width, including the chevron."""
    def __init__(self):
        super().__init__()
        self.setExpandsOnDoubleClick(False)
        self.itemCollapsed.connect(self.collapse_descendants)

    def mousePressEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if event.button() == Qt.LeftButton and item and item.data(0, Qt.UserRole + 1):
            self.setFocus()
            self.setCurrentItem(item)
            item.setExpanded(not item.isExpanded())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if event.button() == Qt.LeftButton and item and item.data(0, Qt.UserRole + 1):
            # Cocoa's native branch handler otherwise toggles again on release.
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if item and item.data(0, Qt.UserRole + 1):
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def collapse_descendants(self, item):
        with QSignalBlocker(self):
            pending = [item.child(index) for index in range(item.childCount())]
            while pending:
                child = pending.pop()
                child.setExpanded(False)
                pending.extend(child.child(index) for index in range(child.childCount()))

    def drawBranches(self, painter, rect, index):
        super().drawBranches(painter, rect, index)
        painter.save()
        painter.setPen(QColor("#DDDDDD"))
        ancestor = index.parent()
        while ancestor.isValid():
            x = self.visualRect(ancestor).left() - self.indentation() // 2
            painter.drawLine(x, rect.top(), x, rect.bottom())
            ancestor = ancestor.parent()
        painter.restore()


class NameDialog(QDialog):
    """Failed filesystem actions keep the dialog open for a corrected name."""
    def __init__(self, parent, title: str, destination: str, action, *, initial="", hint=""):
        super().__init__(parent)
        self.result_path = None
        self.action = action
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        label = plain_label(f"Destination: {destination}")
        label.setWordWrap(True)
        layout.addWidget(label)
        if hint:
            detail = plain_label(hint)
            detail.setWordWrap(True)
            layout.addWidget(detail)
        self.name = QLineEdit(initial)
        self.name.setAccessibleName("Entry name")
        layout.addWidget(self.name)
        self.error = plain_label()
        self.error.setWordWrap(True)
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.attempt)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.name.selectAll()
        self.name.setFocus()

    def attempt(self):
        try:
            self.result_path = self.action(self.name.text())
        except (OSError, ValueError) as error:
            self.error.setText(str(error))
            self.name.setFocus()
            return
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, *, restore: bool = True):
        super().__init__()
        self.vault_path = None
        self.vault = None
        self.document = None
        self.active_path = None
        self.items = {}
        self.loading = False
        self.mode = "edit"
        try:
            self.font_size = min(26, max(11, int(load_settings().get("font_size", 15))))
        except (TypeError, ValueError):
            self.font_size = 15
        self.closed = False
        self.last_scan = None
        self.vault_epoch = 0
        self.tree_generation = 0
        self.scan_busy = False
        self.search_generation = 0
        self.search_cancel = Event()
        self.jobs = set()
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.setWindowTitle("Bluebell · local Markdown notes")
        self.resize(1280, 800)
        self.setMinimumSize(760, 500)
        self.setStyleSheet(STYLE)
        self.autosave = QTimer(self)
        self.autosave.setSingleShot(True)
        self.autosave.setInterval(500)
        self.autosave.timeout.connect(self.save_document)
        self.external_timer = QTimer(self)
        self.external_timer.setInterval(750)
        self.external_timer.timeout.connect(self.tick)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(200)
        self.search_timer.timeout.connect(self.run_search)
        self._build_sidebar()
        self._build_content()
        self._build_shortcuts()
        self.update_zoom(remember=False)
        self.save_state = plain_label("No note open")
        self.statusBar().addPermanentWidget(self.save_state)
        self.statusBar().setSizeGripEnabled(False)
        self._enable_vault_controls(False)
        self.update_note_chrome()
        if restore:
            last = load_settings().get("last_vault")
            if isinstance(last, str):
                if Path(last).is_dir():
                    self.open_vault(Path(last))
                else:
                    self.empty_hint.setText("Your last vault is unavailable. Choose an existing folder to continue.")

    def _build_sidebar(self):
        shell = QWidget(objectName="shell")
        layout = QHBoxLayout(shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(shell)
        rail = QWidget(objectName="rail")
        rail.setFixedWidth(42)
        ribbon = QVBoxLayout(rail)
        ribbon.setContentsMargins(5, 45, 5, 8)
        ribbon.setSpacing(8)
        self.files_button = icon_button("note", "Show files", self.show_files)
        ribbon.addWidget(self.files_button)
        ribbon.addWidget(icon_button("search", "Search vault", self.focus_search))
        ribbon.addWidget(icon_button("new-note", "New note", lambda: self.create_entry(False)))
        ribbon.addStretch()
        ribbon.addWidget(icon_button("folder", "Choose a vault", self.choose_vault))
        layout.addWidget(rail)
        self.splitter = QSplitter()
        layout.addWidget(self.splitter, 1)
        self.sidebar = QWidget(objectName="sidebar")
        self.sidebar.setMinimumWidth(200)
        side = QVBoxLayout(self.sidebar)
        self.sidebar_layout = side
        side.setContentsMargins(0, 0, 0, 0)
        side.setSpacing(0)
        header = QWidget(objectName="sidebarHeader")
        row = QHBoxLayout(header)
        row.setContentsMargins(10, 5, 8, 5)
        row.setSpacing(6)
        self.files_header_button = icon_button("folder", "Show files", self.show_files)
        self.files_header_button.setProperty("active", True)
        row.addWidget(self.files_header_button)
        self.search_button = icon_button("search", "Search notes", self.focus_search)
        row.addWidget(self.search_button)
        row.addStretch()
        row.addWidget(icon_button("panel", "Toggle sidebar", self.toggle_sidebar))
        header.setFixedHeight(40)
        side.addWidget(header)
        tools = QWidget(objectName="explorerTools")
        row = QHBoxLayout(tools)
        row.setContentsMargins(8, 6, 8, 4)
        row.setSpacing(4)
        row.addStretch()
        self.new_note_button = icon_button("new-note", "New note", lambda: self.create_entry(False))
        self.new_folder_button = icon_button("new-folder", "New folder", lambda: self.create_entry(True))
        self.refresh_button = icon_button("refresh", "Refresh files", self.refresh_tree)
        self.collapse_button = icon_button("collapse", "Collapse all folders", self.tree_collapse_all)
        for button in (self.new_note_button, self.new_folder_button, self.refresh_button, self.collapse_button):
            row.addWidget(button)
        row.addStretch()
        side.addWidget(tools)
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Search notes…")
        self.search_text.setClearButtonEnabled(True)
        self.search_text.setAccessibleName("Search notes across the vault")
        self.search_text.textChanged.connect(self.schedule_search)
        self.search_text.returnPressed.connect(self.run_search)
        self.search_container = QWidget()
        row = QHBoxLayout(self.search_container)
        row.setContentsMargins(12, 4, 12, 6)
        row.addWidget(self.search_text)
        self.search_container.hide()
        side.addWidget(self.search_container)
        self.tree = VaultTree()
        self.tree.setIndentation(18)
        self.tree.setFrameShape(QFrame.NoFrame)
        self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName("Vault folders and Markdown notes")
        self.tree.itemClicked.connect(self.tree_clicked)
        self.tree.itemActivated.connect(self.tree_activated)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.tree_menu)
        self.explorer_views = QStackedWidget()
        self.explorer_views.addWidget(self.tree)
        self.search_results = QListWidget()
        self.search_results.setFrameShape(QFrame.NoFrame)
        self.search_results.setAccessibleName("Vault search results")
        self.search_results.itemClicked.connect(self.open_search_result)
        self.search_results.itemActivated.connect(self.open_search_result)
        self.explorer_views.addWidget(self.search_results)
        self.search_summary = plain_label("", objectName="hint")
        self.search_summary.setWordWrap(True)
        self.search_summary.hide()
        side.addWidget(self.search_summary)
        side.addWidget(self.explorer_views, 1)
        footer = QWidget(objectName="vaultFooter")
        row = QHBoxLayout(footer)
        row.setContentsMargins(10, 4, 8, 4)
        row.setSpacing(4)
        self.open_button = icon_button("folder", "Open vault…", self.choose_vault)
        row.addWidget(self.open_button)
        self.vault_label = plain_label("No vault open", objectName="vaultName")
        row.addWidget(self.vault_label, 1)
        actions_button = icon_button("more", "Vault actions")
        menu = QMenu(actions_button)
        menu.addAction("Open another vault…", self.choose_vault)
        menu.addSeparator()
        self.rename_button = menu.addAction("Rename selected…", self.rename_entry)
        self.trash_button = menu.addAction("Move selected to Trash…", self.trash_entry)
        menu.addAction("Refresh files", self.refresh_tree)
        actions_button.setMenu(menu)
        row.addWidget(actions_button)
        side.addWidget(footer)
        self.tree.currentItemChanged.connect(self.update_actions)
        self.search_results.currentItemChanged.connect(self.update_actions)
        self.splitter.addWidget(self.sidebar)

    def toggle_sidebar(self):
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def show_files(self):
        self.sidebar.show()
        self.search_text.clear()
        self.search_container.hide()
        self.set_explorer_mode(False)
        self.explorer_views.setCurrentIndex(0)
        self.tree.setFocus()

    def set_explorer_mode(self, search):
        for button, active in ((self.files_header_button, not search), (self.search_button, search)):
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def tree_collapse_all(self):
        self.tree.collapseAll()

    def _build_content(self):
        self.content = QWidget(objectName="canvas")
        content = QVBoxLayout(self.content)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        tabs = QWidget(objectName="tabStrip")
        tab_row = QHBoxLayout(tabs)
        tab_row.setContentsMargins(12, 4, 8, 0)
        tab_row.setSpacing(4)
        self.active_tab = QWidget(objectName="activeTab")
        active = QHBoxLayout(self.active_tab)
        active.setContentsMargins(12, 0, 3, 0)
        self.tab_label = plain_label("No note open", objectName="tabLabel")
        active.addWidget(self.tab_label, 1)
        self.close_note_button = icon_button("close", "Close note", self.close_note)
        active.addWidget(self.close_note_button)
        self.active_tab.setFixedWidth(210)
        tab_row.addWidget(self.active_tab)
        tab_row.addWidget(icon_button("plus", "New note", lambda: self.create_entry(False)))
        tab_row.addStretch()
        tab_row.addWidget(icon_button("panel", "Toggle sidebar", self.toggle_sidebar))
        tabs.setFixedHeight(40)
        content.addWidget(tabs)
        navigation = QWidget(objectName="noteHeader")
        nav = QHBoxLayout(navigation)
        nav.setContentsMargins(12, 4, 12, 4)
        nav.setSpacing(4)
        self.save_button = icon_button("save", "Save note", lambda: self.save_document(True))
        nav.addWidget(self.save_button)
        nav.addWidget(icon_button("search", "Find in note", self.show_find))
        nav.addStretch(1)
        self.note_label = plain_label("", objectName="breadcrumb")
        self.note_label.setAccessibleName("Current note title")
        nav.addWidget(self.note_label)
        nav.addStretch(1)
        self.mode_button = icon_button("book", "Toggle reading view", lambda: self.set_mode("read" if self.mode == "edit" else "edit"))
        nav.addWidget(self.mode_button)
        self.note_actions_button = icon_button("more", "Note actions")
        menu = QMenu(self.note_actions_button)
        group = QActionGroup(self)
        self.edit_button = menu.addAction("Edit", lambda: self.set_mode("edit"))
        self.read_button = menu.addAction("Read", lambda: self.set_mode("read"))
        for action in (self.edit_button, self.read_button):
            action.setCheckable(True)
            group.addAction(action)
        self.edit_button.setChecked(True)
        menu.addSeparator()
        self.bold_button = menu.addAction("Bold", lambda: self.format_source("**"))
        self.italic_button = menu.addAction("Italic", lambda: self.format_source("*"))
        menu.addSeparator()
        self.undo_button = menu.addAction("Undo", self.undo)
        self.redo_button = menu.addAction("Redo", self.redo)
        menu.addSeparator()
        self.find_button = menu.addAction("Find in note…", self.show_find)
        menu.addAction("Save", lambda: self.save_document(True))
        self.note_actions_button.setMenu(menu)
        nav.addWidget(self.note_actions_button)
        navigation.setFixedHeight(36)
        content.addWidget(navigation)
        self.pages = QStackedWidget(objectName="canvas")
        empty = QWidget(objectName="canvas")
        area = QVBoxLayout(empty)
        area.setContentsMargins(30, 30, 30, 30)
        area.addStretch()
        self.empty_title = plain_label("Your notes, close to home", objectName="emptyTitle")
        self.empty_title.setAlignment(Qt.AlignCenter)
        self.empty_title.setWordWrap(True)
        area.addWidget(self.empty_title)
        self.empty_hint = plain_label("Choose a folder to use as your Markdown vault.", objectName="hint")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setWordWrap(True)
        area.addWidget(self.empty_hint)
        row = QHBoxLayout()
        row.addStretch()
        self.welcome_open = QPushButton("Open vault…", objectName="primary")
        self.welcome_open.clicked.connect(self.choose_vault)
        row.addWidget(self.welcome_open)
        row.addStretch()
        area.addLayout(row)
        area.addStretch()
        self.pages.addWidget(empty)
        note = QWidget(objectName="canvas")
        area = QVBoxLayout(note)
        area.setContentsMargins(32, 32, 32, 16)
        area.setSpacing(12)
        self.note_surface = note
        self.note_heading = plain_label("", objectName="noteHeading")
        self.note_heading.setWordWrap(True)
        area.addWidget(self.note_heading)
        self.notice = QFrame(objectName="notice")
        notice_area = QVBoxLayout(self.notice)
        self.notice_text = plain_label()
        self.notice_text.setWordWrap(True)
        notice_area.addWidget(self.notice_text)
        row = QHBoxLayout()
        self.reload_button = QPushButton("Reload from disk")
        self.copy_button = QPushButton("Save a copy…")
        self.retry_button = QPushButton("Retry save")
        self.reload_button.clicked.connect(self.reload_document)
        self.copy_button.clicked.connect(self.save_copy)
        self.retry_button.clicked.connect(lambda: self.save_document(True))
        for button in (self.reload_button, self.copy_button, self.retry_button):
            row.addWidget(button)
        notice_area.addLayout(row)
        area.addWidget(self.notice)
        self.notice.hide()
        self.findbar = QWidget()
        row = QHBoxLayout(self.findbar)
        row.setContentsMargins(0, 0, 0, 0)
        self.find_text = QLineEdit()
        self.find_text.setPlaceholderText("Find in this note")
        self.find_text.setAccessibleName("Find in current note")
        self.find_text.textChanged.connect(lambda: self.find_in_note(restart=True))
        self.find_text.returnPressed.connect(self.find_in_note)
        row.addWidget(self.find_text, 1)
        previous, following, close = QPushButton("Previous"), QPushButton("Next"), QPushButton("Close")
        previous.clicked.connect(lambda: self.find_in_note(backward=True))
        following.clicked.connect(self.find_in_note)
        close.clicked.connect(self.findbar.hide)
        for button in (previous, following, close):
            row.addWidget(button)
        area.addWidget(self.findbar)
        self.findbar.hide()
        self.views = QStackedWidget()
        self.editor = MarkdownEditor()
        self.editor.setPlaceholderText("")
        self.editor.setFrameShape(QFrame.NoFrame)
        self.editor.textChanged.connect(self.text_changed)
        self.editor.undoAvailable.connect(self.undo_button.setEnabled)
        self.editor.redoAvailable.connect(self.redo_button.setEnabled)
        self.undo_button.setEnabled(False)
        self.redo_button.setEnabled(False)
        self.editor.linkRequested.connect(self.source_link)
        self.preview = SafePreview()
        self.preview.setFrameShape(QFrame.NoFrame)
        self.preview.anchorClicked.connect(self.preview_link)
        self.views.addWidget(self.editor)
        self.views.addWidget(self.preview)
        area.addWidget(self.views, 1)
        note.setMaximumWidth(824)
        note_page = QWidget(objectName="canvas")
        centered = QHBoxLayout(note_page)
        centered.setContentsMargins(0, 0, 0, 0)
        centered.setSpacing(0)
        centered.addStretch(1)
        centered.addWidget(note, 10)
        centered.addStretch(1)
        self.pages.addWidget(note_page)
        content.addWidget(self.pages, 1)
        self.splitter.addWidget(self.content)
        self.splitter.setSizes([292, 946])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)

    def update_note_chrome(self):
        title = PurePosixPath(self.active_path).stem if self.active_path else ""
        self.note_heading.setText(title)
        self.tab_label.setText(self.tab_label.fontMetrics().elidedText(title or "No note open", Qt.ElideRight, 150))
        self.tab_label.setToolTip(self.active_path or "")
        self.note_label.setText(self.note_label.fontMetrics().elidedText(title, Qt.ElideRight, 300))
        self.note_label.setToolTip(self.active_path or "")
        self.close_note_button.setEnabled(bool(self.document))
        self.mode_button.setEnabled(bool(self.document))
        self.save_button.setEnabled(bool(self.document))
        self.note_actions_button.setEnabled(bool(self.document))

    def close_note(self):
        if not self.flush_pending():
            return False
        self.document, self.active_path = None, None
        self._set_editor_text("")
        self.update_note_chrome()
        self.pages.setCurrentIndex(0)
        self.save_state.setText("No note open")
        return True

    def _build_shortcuts(self):
        actions = [
            (QKeySequence.New, lambda: self.create_entry(False)),
            (QKeySequence.Save, lambda: self.save_document(True)),
            (QKeySequence.Find, self.show_find),
            (QKeySequence.Bold, lambda: self.format_source("**")),
            (QKeySequence.Italic, lambda: self.format_source("*")),
            (QKeySequence("Ctrl+E"), lambda: self.set_mode("read" if self.mode == "edit" else "edit")),
            (QKeySequence("Ctrl+Shift+F"), self.focus_search),
            (QKeySequence.ZoomIn, lambda: self.zoom(1)),
            (QKeySequence.ZoomOut, lambda: self.zoom(-1)),
        ]
        for sequence, action in actions:
            QShortcut(sequence, self, activated=action)

    def choose_vault(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose a Markdown vault")
        if folder:
            self.open_vault(Path(folder))

    def open_vault(self, path: Path):
        if not self.flush_pending():
            return False
        try:
            vault = Vault(path)
            scan = vault.scan()
        except (OSError, VaultError) as error:
            self.show_error("Could not open vault", error)
            return False
        self.vault, self.vault_path = vault, vault.root
        self.vault_epoch += 1
        self.tree_generation += 1
        self.scan_busy = False
        self.last_scan = None
        self.search_text.clear()
        self.search_results.clear()
        self.explorer_views.setCurrentIndex(0)
        self.search_summary.hide()
        self.document, self.active_path = None, None
        self.items = {}
        self._set_editor_text("")
        self.vault_label.setText(self.vault_path.name)
        self.vault_label.setToolTip(str(self.vault_path))
        self.open_button.setToolTip("Open another vault…")
        self.open_button.setAccessibleName("Open another vault…")
        self.welcome_open.setText("Open another vault…")
        self.empty_title.setText("A fresh page awaits")
        self.empty_hint.setText("Choose a note, or create one in the selected folder.")
        self.pages.setCurrentIndex(0)
        self.update_note_chrome()
        self.save_state.setText("No note open")
        self._enable_vault_controls(True)
        self.apply_tree(scan)
        self.external_timer.start()
        try:
            settings = load_settings()
            settings["last_vault"] = str(self.vault_path)
            save_settings(settings)
        except OSError:
            self.statusBar().showMessage("Vault opened. Could not remember it for next time.")
        return True

    def _enable_vault_controls(self, enabled):
        for button in (self.new_note_button, self.new_folder_button, self.rename_button, self.trash_button, self.refresh_button, self.search_button, self.search_text):
            button.setEnabled(enabled)
        self.update_actions()

    def update_actions(self, *args):
        allowed = bool(self.vault) and self.selected_path() != "."
        self.rename_button.setEnabled(allowed)
        self.trash_button.setEnabled(allowed)

    def zoom(self, direction):
        self.font_size = min(26, max(11, self.font_size + direction))
        self.update_zoom()

    def update_zoom(self, *, remember=True):
        self.editor.setStyleSheet(f"font-size: {self.font_size}px;")
        self.preview.setStyleSheet(f"font-size: {self.font_size}px;")
        self.preview.set_zoom(self.font_size)
        if self.document and self.mode == "read":
            scroll = self.preview.verticalScrollBar().value()
            self._render()
            self.preview.verticalScrollBar().setValue(scroll)
        if remember:
            try:
                settings = load_settings()
                settings["font_size"] = self.font_size
                save_settings(settings)
            except OSError:
                self.statusBar().showMessage("Zoom changed; could not remember it for next time.")

    def show_error(self, title, error):
        box = QMessageBox(QMessageBox.Warning, title, str(error), QMessageBox.Ok, self)
        box.setTextFormat(Qt.PlainText)
        box.exec()
        box.deleteLater()
        self.statusBar().showMessage(str(error))

    @staticmethod
    def name_result(dialog):
        accepted = dialog.exec() == QDialog.Accepted
        result = dialog.result_path if accepted else None
        dialog.deleteLater()
        return result

    def selected_path(self):
        if self.search_text.text() and self.search_results.currentItem():
            return self.search_results.currentItem().data(Qt.UserRole)
        item = self.tree.currentItem()
        return item.data(0, Qt.UserRole) if item else "."

    def destination(self):
        if self.search_text.text() and self.search_results.currentItem():
            return str(PurePosixPath(self.selected_path()).parent)
        item = self.tree.currentItem()
        if item is None:
            return "."
        path = item.data(0, Qt.UserRole)
        return path if item.data(0, Qt.UserRole + 1) else str(PurePosixPath(path).parent)

    def apply_tree(self, scan):
        self.last_scan = scan
        expanded = {path for path, item in self.items.items() if item.isExpanded()}
        selected = self.selected_path()
        self.tree.clear()
        root = self.tree.invisibleRootItem()
        root.setData(0, Qt.UserRole, ".")
        root.setData(0, Qt.UserRole + 1, True)
        self.items = {".": root}
        for entry in scan.entries:
            path = PurePosixPath(entry.path)
            item = QTreeWidgetItem(self.items.get(str(path.parent), root), [path.name if entry.folder else path.stem])
            item.setData(0, Qt.UserRole, entry.path)
            item.setData(0, Qt.UserRole + 1, entry.folder)
            item.setToolTip(0, entry.path)
            self.items[entry.path] = item
            if entry.path in expanded:
                item.setExpanded(True)
        root.setExpanded(True)
        if selected in self.items:
            self.tree.setCurrentItem(self.items[selected])
        if scan.warnings:
            self.statusBar().showMessage(f"{len(scan.warnings)} inaccessible or symlink entries skipped; hover the vault name for details.")
            self.vault_label.setToolTip(str(self.vault.root) + "\n" + "\n".join(scan.warnings[:20]))
        else:
            self.vault_label.setToolTip(str(self.vault.root))

    def refresh_tree(self):
        if self.vault:
            try:
                self.tree_generation += 1
                self.apply_tree(self.vault.scan())
                self.check_external()
                self.schedule_search()
            except (OSError, VaultError) as error:
                self.show_error("Could not refresh vault", error)

    def select_path(self, path):
        if path in self.items:
            item = self.items[path]
            if path == ".":
                self.tree.setCurrentItem(None)
                return
            ancestor = item.parent()
            while ancestor:
                ancestor.setExpanded(True)
                ancestor = ancestor.parent()
            self.tree.setCurrentItem(item)
            self.tree.scrollToItem(item)

    def _job(self, operation, callback):
        worker = Work(operation)
        self.jobs.add(worker)
        def finished(result):
            self.jobs.discard(worker)
            if not self.closed:
                callback(result)
        worker.signals.finished.connect(finished, Qt.QueuedConnection)
        self.pool.start(worker)

    def tick(self):
        self.check_external()
        if not self.vault or self.scan_busy or self.closed:
            return
        self.scan_busy = True
        vault, epoch, generation = self.vault, self.vault_epoch, self.tree_generation
        def finished(result):
            if epoch != self.vault_epoch:
                return
            self.scan_busy = False
            if generation != self.tree_generation:
                return
            if result.error:
                self.statusBar().showMessage("Vault refresh failed: " + result.error + ". Use Refresh or reopen the vault.")
            elif result.value != self.last_scan:
                self.apply_tree(result.value)
                self.schedule_search()
        self._job(vault.scan, finished)

    def focus_search(self):
        if self.vault:
            self.sidebar.show()
            self.search_container.show()
            self.set_explorer_mode(True)
            self.search_text.setFocus()
            self.search_text.selectAll()
            if self.search_text.text():
                self.run_search()

    def schedule_search(self):
        self.search_generation += 1
        self.search_cancel.set()
        self.search_cancel = Event()
        if not self.search_text.text():
            self.search_timer.stop()
            self.search_summary.hide()
            self.explorer_views.setCurrentIndex(0)
            self.search_results.clear()
        elif self.vault:
            self.search_summary.setText("Searching…")
            self.search_summary.show()
            self.explorer_views.setCurrentIndex(1)
            self.search_timer.start()

    def run_search(self):
        self.search_timer.stop()
        query = self.search_text.text()
        if not self.vault or not query:
            return
        self.search_cancel.set()
        self.search_cancel = Event()
        cancelled = self.search_cancel
        self.search_generation += 1
        generation, epoch, vault = self.search_generation, self.vault_epoch, self.vault
        entries = self.last_scan.entries if self.last_scan else ()
        overlay = {self.document.relative: self.document.text} if self.document and self.document.dirty else {}
        def finished(result):
            if epoch != self.vault_epoch or generation != self.search_generation:
                return
            self.search_results.clear()
            if result.error:
                self.search_summary.setText("Search failed: " + result.error)
                return
            page = result.value
            for match in page.results:
                text = match.path + (" · unsaved" if match.unsaved else "") + "\n" + match.context
                item = QListWidgetItem(text)
                item.setData(Qt.UserRole, match.path)
                item.setToolTip(match.path + "\n" + match.context)
                self.search_results.addItem(item)
            summary = f"{len(page.results)} result{'s' if len(page.results) != 1 else ''}"
            if page.limited:
                summary += " shown · narrow your search"
            if page.skipped:
                summary += f" · {len(page.skipped)} unreadable notes skipped"
            self.search_summary.setText(summary if page.results else "No matching notes." + (f" {len(page.skipped)} unreadable notes skipped." if page.skipped else ""))
        self._job(lambda: search_notes(vault, query, entries=entries, overlay=overlay, cancelled=cancelled.is_set), finished)

    def open_search_result(self, item):
        self.open_note(item.data(Qt.UserRole))

    def create_entry(self, folder=False):
        if not self.vault:
            return
        destination = self.destination()
        if not self.flush_pending():
            return
        dialog = NameDialog(self, "New folder" if folder else "New Markdown note", destination,
                            lambda name: self.vault.create(destination, name, folder=folder))
        result = self.name_result(dialog)
        if result is not None:
            self.search_text.clear()
            self.refresh_tree()
            self.select_path(result)
            if not folder:
                self.open_note(result)
                self.set_mode("edit")

    def tree_clicked(self, item, column=0):
        if not item.data(0, Qt.UserRole + 1):
            self.open_note(item.data(0, Qt.UserRole))

    def tree_activated(self, item, column=0):
        if item.data(0, Qt.UserRole + 1):
            item.setExpanded(not item.isExpanded())
        else:
            self.tree_clicked(item, column)

    def open_note(self, relative):
        if relative == self.active_path:
            self.select_path(relative)
            return True
        if not self.flush_pending():
            self.select_path(self.active_path)
            return False
        try:
            document = Document(self.vault, relative)
        except (OSError, UnicodeError, VaultError) as error:
            self.show_error("Could not open note", error)
            self.select_path(self.active_path)
            return False
        self._adopt_document(document)
        self.select_path(relative)
        self.editor.setFocus()
        return True

    def _adopt_document(self, document):
        self.document = document
        self.active_path = document.relative
        self.update_note_chrome()
        self.setWindowTitle(f"{PurePosixPath(document.relative).name} · Bluebell")
        self._set_editor_text(document.text)
        self.pages.setCurrentIndex(1)
        self.save_state.setText("Saved")
        self.notice.hide()
        if self.mode == "read":
            self._render()

    def _set_editor_text(self, text, *, preserve_position=False):
        position = self.editor.textCursor().position()
        scroll = self.editor.verticalScrollBar().value()
        self.loading = True
        self.editor.setPlainText(text)
        self.loading = False
        if preserve_position:
            cursor = self.editor.textCursor()
            cursor.setPosition(min(position, self.editor.document().characterCount() - 1))
            self.editor.setTextCursor(cursor)
            self.editor.verticalScrollBar().setValue(scroll)

    def text_changed(self):
        if self.loading or not self.document:
            return
        self.document.text = self.editor.toPlainText()
        self.save_state.setText("Save failed" if self.document.error else "Unsaved" if self.document.dirty or self.document.paused else "Saved")
        if self.document.dirty and not self.document.paused:
            self.autosave.start()
        else:
            self.autosave.stop()

    def save_document(self, explicit=False):
        self.autosave.stop()
        if not self.document:
            return True
        if self.document.dirty:
            self.save_state.setText("Saving")
        try:
            self.document.save()
        except (OSError, VaultError) as error:
            self.save_state.setText("Unsaved" if self.document.conflict or self.document.missing else "Save failed")
            self._show_document_notice()
            self.statusBar().showMessage(str(error))
            return False
        if self.document.paused:
            self.save_state.setText("Save failed" if self.document.error else "Unsaved")
            self._show_document_notice()
            return False
        self.save_state.setText("Saved")
        if not self.document.paused:
            self.notice.hide()
        if self.search_text.text():
            self.schedule_search()
        return True

    def _show_document_notice(self):
        document = self.document
        if not document or not document.paused:
            self.notice.hide()
            return
        if document.conflict:
            text = "The disk version changed while you were editing. Autosave is paused. Reload from disk or save your edits as a conflict copy."
        elif document.missing:
            text = "This note was moved or removed outside Bluebell. Your text stays here. Save a copy inside the vault to keep it."
        else:
            text = f"Save failed or disk unavailable: {document.error}. Your text stays here; autosave is paused."
        self.notice_text.setText(text)
        self.reload_button.setEnabled(not document.missing)
        self.retry_button.setVisible(bool(document.error) and not document.conflict and not document.missing)
        self.copy_button.setText("Save a conflict copy…" if document.conflict else "Save a copy…")
        self.notice.show()

    def check_external(self):
        if not self.document:
            return
        result = self.document.check_external()
        if result == "reloaded":
            self._set_editor_text(self.document.text, preserve_position=True)
            self.save_state.setText("Saved")
            self.statusBar().showMessage("Reloaded a change made outside Bluebell.")
            self.notice.hide()
            if self.mode == "read":
                self._render()
        elif result in {"conflict", "missing", "error"}:
            self.autosave.stop()
            self.save_state.setText("Save failed" if result == "error" else "Unsaved")
            self._show_document_notice()

    def flush_pending(self):
        self.autosave.stop()
        if not self.document or not self.document.dirty:
            return True
        if self.save_document():
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Keep your unsaved edits")
        box.setTextFormat(Qt.PlainText)
        box.setText("The note could not be saved to its original path. Save a copy to keep your edits, or explicitly reload from disk to discard them.")
        copy = box.addButton("Save a conflict copy" if self.document.conflict else "Save a copy", QMessageBox.AcceptRole)
        reload = None if self.document.missing else box.addButton("Reload from disk (discard edits)", QMessageBox.DestructiveRole)
        cancel = box.addButton(QMessageBox.Cancel)
        box.setDefaultButton(cancel)
        box.exec()
        if box.clickedButton() == copy:
            return self.save_copy()
        if reload is not None and box.clickedButton() == reload:
            return self.reload_document(confirm=False)
        return False

    def reload_document(self, *, confirm=True):
        if not self.document:
            return False
        if confirm and self.document.dirty:
            box = QMessageBox(QMessageBox.Question, "Reload from disk", "Reload and discard your unsaved edits? Save a copy first if you want to keep them.", QMessageBox.Yes | QMessageBox.Cancel, self)
            box.setDefaultButton(QMessageBox.Cancel)
            if box.exec() != QMessageBox.Yes:
                return False
        try:
            self.document.reload()
        except (OSError, UnicodeError, VaultError) as error:
            self.show_error("Could not reload note", error)
            return False
        self._adopt_document(self.document)
        return True

    def save_copy(self):
        if not self.document:
            return False
        parent = str(PurePosixPath(self.document.relative).parent)
        try:
            self.vault.resolve(parent)
        except (OSError, VaultError):
            parent = "."
        stem = PurePosixPath(self.document.relative).stem[:100]
        initial = stem + (" (conflict copy).md" if self.document.conflict else " (recovered).md")
        dialog = NameDialog(self, "Save your edits as a new Markdown note", parent,
                            lambda name: self.vault.create(parent, name, content=self.document.encoded()), initial=initial,
                            hint="The disk version and original path will be left unchanged.")
        result = self.name_result(dialog)
        if result is None:
            return False
        self._adopt_document(Document(self.vault, result))
        self.refresh_tree()
        self.select_path(result)
        return True

    def _render(self):
        if self.document:
            self.preview.show_markdown(self.document.text, self.vault, self.document.relative)

    def set_mode(self, mode):
        if not self.document:
            return
        self.mode = mode
        self.mode_button.setIcon(line_icon("edit" if mode == "read" else "book"))
        self.mode_button.setToolTip("Switch to editing" if mode == "read" else "Switch to reading")
        self.edit_button.setChecked(mode == "edit")
        self.read_button.setChecked(mode == "read")
        self.views.setCurrentIndex(0 if mode == "edit" else 1)
        if mode == "read":
            self._render()
            self.preview.setFocus()
        else:
            self.editor.setFocus()

    def format_source(self, marker):
        if self.document:
            self.set_mode("edit")
            self.editor.wrap_selection(marker)

    def undo(self):
        self.set_mode("edit")
        self.editor.undo()

    def redo(self):
        self.set_mode("edit")
        self.editor.redo()

    def show_find(self):
        if self.document:
            self.findbar.show()
            self.find_text.setFocus()
            self.find_text.selectAll()

    def find_in_note(self, backward=False, *, restart=False):
        target = self.editor if self.mode == "edit" else self.preview
        text = self.find_text.text()
        if not text:
            return
        cursor = target.textCursor()
        if restart:
            cursor.movePosition(QTextCursor.Start)
            target.setTextCursor(cursor)
        flags = QTextDocument.FindBackward if backward else QTextDocument.FindFlags()
        if not target.find(text, flags):
            cursor.movePosition(QTextCursor.End if backward else QTextCursor.Start)
            target.setTextCursor(cursor)
            if not target.find(text, flags):
                self.statusBar().showMessage("No matches in this note.")

    def source_link(self, target, wiki):
        self.navigate_link(target, wiki=wiki)

    def preview_link(self, url):
        scheme = url.scheme().lower()
        if scheme in {"bluebell-wiki", "bluebell-note"}:
            target = unquote(url.toString(QUrl.FullyEncoded).split(":", 1)[1])
            self.navigate_link(target, wiki=scheme == "bluebell-wiki")
        elif scheme in {"http", "https"}:
            self.open_external(url)
        else:
            self.show_error("Link blocked", "Only internal Markdown notes and clicked HTTP/HTTPS links can be opened.")

    def open_external(self, url):
        if url.scheme().lower() not in {"http", "https"} or not url.isValid() or not url.host():
            self.show_error("Link blocked", "That is not a valid HTTP/HTTPS link.")
        elif not QDesktopServices.openUrl(url):
            self.show_error("Could not open browser", "Your default browser could not open this link.")

    def navigate_link(self, target, *, wiki=False):
        if not self.document:
            return False
        try:
            parsed = urlsplit(target) if not wiki else None
            if parsed and parsed.scheme in {"http", "https"}:
                self.open_external(QUrl(target))
                return True
            relative = resolve_link(self.vault, self.document.relative, target, wiki=wiki,
                                    entries=self.last_scan.entries if self.last_scan else None)
        except ValueError as error:
            self.show_error("Could not follow note link", error)
            return False
        return self.open_note(relative)

    def rename_entry(self):
        if not self.vault or self.selected_path() == ".":
            return
        old = self.selected_path()
        if not self.flush_pending():
            return
        dialog = NameDialog(self, "Rename", str(PurePosixPath(old).parent),
                            lambda name: self.vault.rename(old, name), initial=PurePosixPath(old).name,
                            hint="Links to renamed paths may need updating. Automatic link rewriting comes later.")
        new = self.name_result(dialog)
        if new is not None:
            self.search_text.clear()
            if self.active_path and (self.active_path == old or self.active_path.startswith(old + "/")):
                self.active_path = new + self.active_path[len(old):]
                self.document.relative = self.active_path
                self.update_note_chrome()
            self.refresh_tree()
            self.select_path(new)

    def trash_entry(self):
        if not self.vault or self.selected_path() == ".":
            return
        relative = self.selected_path()
        if not self.flush_pending():
            return
        try:
            folder = self.vault.resolve(relative).is_dir()
        except (OSError, VaultError) as error:
            self.show_error("Could not move to Trash", error)
            return
        message = f'Move "{relative}" to the operating system\'s Trash?'
        if folder:
            message += " All of this folder's contents will also move to Trash."
        box = QMessageBox(QMessageBox.Question, "Move to Trash", message, QMessageBox.Yes | QMessageBox.Cancel, self)
        box.setTextFormat(Qt.PlainText)
        box.setDefaultButton(QMessageBox.Cancel)
        if box.exec() != QMessageBox.Yes:
            return
        try:
            self.vault.trash(relative)
        except (OSError, VaultError) as error:
            self.show_error("Could not move to Trash", error)
            return
        if self.active_path and (self.active_path == relative or self.active_path.startswith(relative + "/")):
            self.document, self.active_path = None, None
            self._set_editor_text("")
            self.update_note_chrome()
            self.pages.setCurrentIndex(0)
            self.save_state.setText("No note open")
        self.refresh_tree()

    def tree_menu(self, point):
        item = self.tree.itemAt(point)
        self.tree.setCurrentItem(item)
        menu = QMenu(self)
        menu.addAction("New note", lambda: self.create_entry(False))
        menu.addAction("New folder", lambda: self.create_entry(True))
        if self.selected_path() != ".":
            menu.addSeparator()
            menu.addAction("Rename…", self.rename_entry)
            menu.addAction("Move to Trash…", self.trash_entry)
        menu.addSeparator()
        menu.addAction("Refresh", self.refresh_tree)
        menu.exec(self.tree.viewport().mapToGlobal(point))

    def closeEvent(self, event):
        if not self.flush_pending():
            event.ignore()
            return
        self.autosave.stop()
        self.external_timer.stop()
        self.search_timer.stop()
        self.search_cancel.set()
        self.closed = True
        event.accept()
