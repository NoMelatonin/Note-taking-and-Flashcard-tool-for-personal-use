"""Native desktop window; note files remain the vault's authority."""

from pathlib import Path, PurePosixPath

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMenu, QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from bluebell.settings import load_settings, save_settings
from bluebell.theme import STYLE
from bluebell.vault import Vault, VaultError


class NameDialog(QDialog):
    """Failed filesystem actions keep the dialog open for a corrected name."""
    def __init__(self, parent, title: str, destination: str, action, *, initial="", hint=""):
        super().__init__(parent)
        self.result_path = None
        self.action = action
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        label = QLabel(f"Destination: {destination}")
        label.setTextFormat(Qt.PlainText)
        label.setWordWrap(True)
        layout.addWidget(label)
        if hint:
            detail = QLabel(hint)
            detail.setWordWrap(True)
            layout.addWidget(detail)
        self.name = QLineEdit(initial)
        self.name.setAccessibleName("Entry name")
        layout.addWidget(self.name)
        self.error = QLabel("")
        self.error.setTextFormat(Qt.PlainText)
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
        except (OSError, VaultError) as error:
            self.error.setText(str(error))
            self.name.setFocus()
            return
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, *, restore: bool = True):
        super().__init__()
        self.vault_path = None
        self.vault = None
        self.active_path = None
        self.items = {}
        self.setWindowTitle("Bluebell · local Markdown notes")
        self.resize(1120, 760)
        self.setMinimumSize(760, 500)
        self.setStyleSheet(STYLE)
        self.splitter = QSplitter()
        self.setCentralWidget(self.splitter)
        sidebar = QWidget(objectName="sidebar")
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 24, 20, 20)
        side.setSpacing(14)
        side.addWidget(QLabel("Bluebell", objectName="brand"))
        side.addWidget(QLabel("A little room for your thoughts", objectName="subtitle"))
        self.vault_label = QLabel("No vault open", objectName="hint")
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
        self.canvas = QWidget(objectName="canvas")
        area = QVBoxLayout(self.canvas)
        area.setContentsMargins(34, 30, 34, 30)
        self.note_label = QLabel("")
        self.note_label.setTextFormat(Qt.PlainText)
        self.note_label.setWordWrap(True)
        area.addWidget(self.note_label)
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setVisible(False)
        area.addWidget(self.editor, 1)
        area.addStretch()
        self.empty_title = QLabel("Your notes, close to home", objectName="emptyTitle")
        self.empty_title.setAlignment(Qt.AlignCenter)
        area.addWidget(self.empty_title)
        self.empty_hint = QLabel("Choose a folder to use as your Markdown vault.", objectName="hint")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setWordWrap(True)
        area.addWidget(self.empty_hint)
        button_row = QHBoxLayout()
        button_row.addStretch()
        welcome_open = QPushButton("Open vault…", objectName="primary")
        welcome_open.clicked.connect(self.choose_vault)
        button_row.addWidget(welcome_open)
        button_row.addStretch()
        area.addLayout(button_row)
        area.addStretch()
        self.splitter.addWidget(self.canvas)
        self.splitter.setSizes([300, 820])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
        self.statusBar().showMessage("Local files. No account needed.")
        self._enable_vault_controls(False)
        QShortcut(QKeySequence.New, self, activated=lambda: self.create_entry(False))
        if restore:
            last = load_settings().get("last_vault")
            if isinstance(last, str):
                if Path(last).is_dir():
                    self.open_vault(Path(last))
                else:
                    self.empty_hint.setText("Your last vault is unavailable. Choose an existing folder to continue.")

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
        self.vault = vault
        self.vault_path = vault.root
        self.active_path = None
        self.editor.clear()
        self.editor.hide()
        self.vault_label.setText(self.vault_path.name)
        self.vault_label.setToolTip(str(self.vault_path))
        self.open_button.setText("Open another vault…")
        self.empty_title.setText("A fresh page awaits")
        self.empty_hint.setText("Choose a note, or create one in the selected folder.")
        self.empty_title.show()
        self.empty_hint.show()
        self.note_label.clear()
        self._enable_vault_controls(True)
        self.apply_tree(scan)
        try:
            save_settings({"last_vault": str(self.vault_path)})
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

    def flush_pending(self):
        return True  # Replaced with safe document saving in step 3.

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
            parent = self.items.get(str(path.parent), root)
            item = QTreeWidgetItem(parent, [path.name])
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
        if not self.flush_pending():
            self.select_path(self.active_path)
            return False
        try:
            data = self.vault.read(relative).data.decode("utf-8-sig")
        except (OSError, UnicodeError, VaultError) as error:
            self.show_error("Could not open note", error)
            return False
        self.active_path = relative
        self.note_label.setText(relative)
        self.editor.setPlainText(data)
        self.editor.show()
        self.empty_title.hide()
        self.empty_hint.hide()
        self.select_path(relative)
        self.statusBar().showMessage("Read-only preview · editing arrives in step 3")
        return True

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
            self.active_path = None
            self.editor.clear()
            self.editor.hide()
            self.note_label.clear()
            self.empty_title.show()
            self.empty_hint.show()
        self.refresh_tree()

    def tree_menu(self, point):
        item = self.tree.itemAt(point)
        if item:
            self.tree.setCurrentItem(item)
        else:
            self.tree.setCurrentItem(None)
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
