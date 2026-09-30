"""Native Qt window; filesystem behavior is added in the next plan step."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMainWindow, QPushButton, QSplitter,
    QTreeWidget, QVBoxLayout, QWidget,
)

from bluebell.settings import load_settings, save_settings
from bluebell.theme import STYLE


class MainWindow(QMainWindow):
    def __init__(self, *, restore: bool = True):
        super().__init__()
        self.vault_path = None
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
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName("Vault folders and Markdown notes")
        side.addWidget(self.tree, 1)
        self.splitter.addWidget(sidebar)
        self.canvas = QWidget(objectName="canvas")
        area = QVBoxLayout(self.canvas)
        area.setContentsMargins(34, 30, 34, 30)
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
        if not path.is_dir():
            self.statusBar().showMessage("That vault folder is unavailable.")
            return False
        self.vault_path = path.resolve()
        self.vault_label.setText(self.vault_path.name)
        self.vault_label.setToolTip(str(self.vault_path))
        self.open_button.setText("Open another vault…")
        self.empty_title.setText("A fresh page awaits")
        self.empty_hint.setText("Vault selected. Folder and note controls arrive in the next step.")
        try:
            save_settings({"last_vault": str(self.vault_path)})
        except OSError:
            self.statusBar().showMessage("Vault opened. Could not remember it for next time.")
        return True
