"""Native desktop UI over a filesystem vault and one active document."""

from pathlib import Path, PurePosixPath

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QButtonGroup, QDialog, QDialogButtonBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMenu, QMessageBox, QPushButton, QSplitter,
    QStackedWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from bluebell.document import Document
from bluebell.editor import MarkdownEditor
from bluebell.rendering import SafePreview
from bluebell.settings import load_settings, save_settings
from bluebell.theme import STYLE
from bluebell.vault import ConflictError, Vault, VaultError


def plain_label(text="", **kwargs):
    label = QLabel(text, **kwargs)
    label.setTextFormat(Qt.PlainText)
    return label


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
        self.setWindowTitle("Bluebell · local Markdown notes")
        self.resize(1120, 760)
        self.setMinimumSize(760, 500)
        self.setStyleSheet(STYLE)
        self.autosave = QTimer(self)
        self.autosave.setSingleShot(True)
        self.autosave.setInterval(500)
        self.autosave.timeout.connect(self.save_document)
        self.external_timer = QTimer(self)
        self.external_timer.setInterval(750)
        self.external_timer.timeout.connect(self.check_external)
        self._build_sidebar()
        self._build_content()
        self._build_shortcuts()
        self.save_state = plain_label("No note open")
        self.statusBar().addPermanentWidget(self.save_state)
        self.statusBar().showMessage("Local files. No account needed.")
        self._enable_vault_controls(False)
        if restore:
            last = load_settings().get("last_vault")
            if isinstance(last, str):
                if Path(last).is_dir():
                    self.open_vault(Path(last))
                else:
                    self.empty_hint.setText("Your last vault is unavailable. Choose an existing folder to continue.")

    def _build_sidebar(self):
        self.splitter = QSplitter()
        self.setCentralWidget(self.splitter)
        sidebar = QWidget(objectName="sidebar")
        sidebar.setMinimumWidth(255)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 24, 18, 18)
        side.setSpacing(12)
        side.addWidget(plain_label("Bluebell", objectName="brand"))
        subtitle = plain_label("A little room for your thoughts", objectName="subtitle")
        subtitle.setWordWrap(True)
        side.addWidget(subtitle)
        self.vault_label = plain_label("No vault open", objectName="hint")
        side.addWidget(self.vault_label)
        self.open_button = QPushButton("Open vault…")
        self.open_button.clicked.connect(self.choose_vault)
        side.addWidget(self.open_button)
        row = QHBoxLayout()
        self.new_note_button = QPushButton("New note")
        self.new_folder_button = QPushButton("New folder")
        self.new_note_button.clicked.connect(lambda: self.create_entry(False))
        self.new_folder_button.clicked.connect(lambda: self.create_entry(True))
        row.addWidget(self.new_note_button)
        row.addWidget(self.new_folder_button)
        side.addLayout(row)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName("Vault folders and Markdown notes")
        self.tree.itemClicked.connect(self.tree_clicked)
        self.tree.itemActivated.connect(self.tree_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.tree_menu)
        side.addWidget(self.tree, 1)
        row = QHBoxLayout()
        self.rename_button = QPushButton("Rename")
        self.trash_button = QPushButton("Trash")
        self.refresh_button = QPushButton("Refresh")
        self.rename_button.clicked.connect(self.rename_entry)
        self.trash_button.clicked.connect(self.trash_entry)
        self.refresh_button.clicked.connect(self.refresh_tree)
        row.addWidget(self.rename_button)
        row.addWidget(self.trash_button)
        row.addWidget(self.refresh_button)
        side.addLayout(row)
        self.splitter.addWidget(sidebar)

    def _build_content(self):
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
        area.setContentsMargins(24, 24, 24, 20)
        area.setSpacing(12)
        self.note_label = plain_label()
        self.note_label.setWordWrap(True)
        self.note_label.setAccessibleName("Current note path")
        area.addWidget(self.note_label)
        row = QHBoxLayout()
        self.edit_button, self.read_button = QPushButton("Edit"), QPushButton("Read")
        group = QButtonGroup(self)
        for button in (self.edit_button, self.read_button):
            button.setCheckable(True)
            group.addButton(button)
            row.addWidget(button)
        self.edit_button.setChecked(True)
        self.edit_button.clicked.connect(lambda: self.set_mode("edit"))
        self.read_button.clicked.connect(lambda: self.set_mode("read"))
        row.addStretch()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(lambda: self.save_document(True))
        row.addWidget(self.save_button)
        area.addLayout(row)
        row = QHBoxLayout()
        self.bold_button, self.italic_button = QPushButton("Bold"), QPushButton("Italic")
        self.undo_button, self.redo_button = QPushButton("Undo"), QPushButton("Redo")
        self.find_button = QPushButton("Find")
        self.bold_button.clicked.connect(lambda: self.format_source("**"))
        self.italic_button.clicked.connect(lambda: self.format_source("*"))
        self.undo_button.clicked.connect(self.undo)
        self.redo_button.clicked.connect(self.redo)
        self.find_button.clicked.connect(self.show_find)
        for button in (self.bold_button, self.italic_button, self.undo_button, self.redo_button, self.find_button):
            row.addWidget(button)
        row.addStretch()
        area.addLayout(row)
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
        self.editor.textChanged.connect(self.text_changed)
        self.editor.undoAvailable.connect(self.undo_button.setEnabled)
        self.editor.redoAvailable.connect(self.redo_button.setEnabled)
        self.undo_button.setEnabled(False)
        self.redo_button.setEnabled(False)
        self.editor.linkRequested.connect(self.source_link)
        self.preview = SafePreview()
        self.preview.anchorClicked.connect(self.preview_link)
        self.views.addWidget(self.editor)
        self.views.addWidget(self.preview)
        area.addWidget(self.views, 1)
        self.pages.addWidget(note)
        self.splitter.addWidget(self.pages)
        self.splitter.setSizes([300, 820])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)

    def _build_shortcuts(self):
        actions = [
            (QKeySequence.New, lambda: self.create_entry(False)),
            (QKeySequence.Save, lambda: self.save_document(True)),
            (QKeySequence.Find, self.show_find),
            (QKeySequence.Bold, lambda: self.format_source("**")),
            (QKeySequence.Italic, lambda: self.format_source("*")),
            (QKeySequence("Ctrl+E"), lambda: self.set_mode("read" if self.mode == "edit" else "edit")),
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
        self.document, self.active_path = None, None
        self.items = {}
        self._set_editor_text("")
        self.vault_label.setText(self.vault_path.name)
        self.vault_label.setToolTip(str(self.vault_path))
        self.open_button.setText("Open another vault…")
        self.welcome_open.setText("Open another vault…")
        self.empty_title.setText("A fresh page awaits")
        self.empty_hint.setText("Choose a note, or create one in the selected folder.")
        self.pages.setCurrentIndex(0)
        self.note_label.clear()
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
        for button in (self.new_note_button, self.new_folder_button, self.rename_button, self.trash_button, self.refresh_button):
            button.setEnabled(enabled)

    def show_error(self, title, error):
        box = QMessageBox(QMessageBox.Warning, title, str(error), QMessageBox.Ok, self)
        box.setTextFormat(Qt.PlainText)
        box.exec()
        self.statusBar().showMessage(str(error))

    def selected_path(self):
        item = self.tree.currentItem()
        return item.data(0, Qt.UserRole) if item else "."

    def destination(self):
        item = self.tree.currentItem()
        if item is None:
            return "."
        path = item.data(0, Qt.UserRole)
        return path if item.data(0, Qt.UserRole + 1) else str(PurePosixPath(path).parent)

    def apply_tree(self, scan):
        expanded = {path for path, item in self.items.items() if item.isExpanded()}
        selected = self.selected_path()
        self.tree.clear()
        root = QTreeWidgetItem([self.vault.root.name])
        root.setData(0, Qt.UserRole, ".")
        root.setData(0, Qt.UserRole + 1, True)
        self.tree.addTopLevelItem(root)
        self.items = {".": root}
        for entry in scan.entries:
            path = PurePosixPath(entry.path)
            item = QTreeWidgetItem(self.items.get(str(path.parent), root), [path.name])
            item.setData(0, Qt.UserRole, entry.path)
            item.setData(0, Qt.UserRole + 1, entry.folder)
            icon = self.style().StandardPixmap.SP_DirIcon if entry.folder else self.style().StandardPixmap.SP_FileIcon
            item.setIcon(0, self.style().standardIcon(icon))
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

    def refresh_tree(self):
        if self.vault:
            try:
                self.apply_tree(self.vault.scan())
                self.check_external()
            except (OSError, VaultError) as error:
                self.show_error("Could not refresh vault", error)

    def select_path(self, path):
        if path in self.items:
            item = self.items[path]
            ancestor = item.parent()
            while ancestor:
                ancestor.setExpanded(True)
                ancestor = ancestor.parent()
            self.tree.setCurrentItem(item)
            self.tree.scrollToItem(item)

    def create_entry(self, folder=False):
        if not self.vault or not self.flush_pending():
            return
        destination = self.destination()
        dialog = NameDialog(self, "New folder" if folder else "New Markdown note", destination,
                            lambda name: self.vault.create(destination, name, folder=folder))
        if dialog.exec() == QDialog.Accepted:
            self.refresh_tree()
            self.select_path(dialog.result_path)
            if not folder:
                self.open_note(dialog.result_path)

    def tree_clicked(self, item, column=0):
        if not item.data(0, Qt.UserRole + 1):
            self.open_note(item.data(0, Qt.UserRole))

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
        self.note_label.setText(document.relative)
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
            cursor.setPosition(min(position, len(text)))
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
        self.save_state.setText("Saved")
        if not self.document.paused:
            self.notice.hide()
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
        if dialog.exec() != QDialog.Accepted:
            return False
        self._adopt_document(Document(self.vault, dialog.result_path))
        self.refresh_tree()
        self.select_path(dialog.result_path)
        return True

    def _render(self):
        if self.document:
            self.preview.show_markdown(self.document.text, self.vault, self.document.relative)

    def set_mode(self, mode):
        if not self.document:
            return
        self.mode = mode
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
        self.statusBar().showMessage("Internal link navigation arrives in step 4.")

    def preview_link(self, url):
        self.statusBar().showMessage("Link navigation arrives in step 4.")

    def rename_entry(self):
        if not self.vault or self.selected_path() == "." or not self.flush_pending():
            return
        old = self.selected_path()
        dialog = NameDialog(self, "Rename", str(PurePosixPath(old).parent),
                            lambda name: self.vault.rename(old, name), initial=PurePosixPath(old).name,
                            hint="Links to renamed paths may need updating. Automatic link rewriting comes later.")
        if dialog.exec() == QDialog.Accepted:
            new = dialog.result_path
            if self.active_path and (self.active_path == old or self.active_path.startswith(old + "/")):
                self.active_path = new + self.active_path[len(old):]
                self.document.relative = self.active_path
                self.note_label.setText(self.active_path)
            self.refresh_tree()
            self.select_path(new)

    def trash_entry(self):
        if not self.vault or self.selected_path() == "." or not self.flush_pending():
            return
        relative = self.selected_path()
        folder = self.tree.currentItem().data(0, Qt.UserRole + 1)
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
            self.note_label.clear()
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
        event.accept()
