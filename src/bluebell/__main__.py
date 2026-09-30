import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from bluebell.ui import MainWindow


def main() -> int:
    parser = argparse.ArgumentParser(description="Bluebell local Markdown notes")
    parser.add_argument("--vault", type=Path, help="Open an existing vault folder")
    parser.add_argument("--no-restore", action="store_true", help="Start at the vault chooser")
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("Bluebell")
    app.setOrganizationName("Bluebell Notes")
    window = MainWindow(restore=not args.no_restore)
    if args.vault:
        window.open_vault(args.vault)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
