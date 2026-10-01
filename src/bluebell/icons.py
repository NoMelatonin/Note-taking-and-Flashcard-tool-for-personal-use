"""Small local line icons for the workspace controls."""

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton


PATHS = {
    "folder": '<path d="M3 7V5h6l2 2h10v13H3Z"/><path d="M3 9h18"/>',
    "search": '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    "note": '<path d="M5 3h10l4 4v14H5Z"/><path d="M14 3v5h5M9 12h6M9 16h6"/>',
    "new-note": '<path d="M12 4H4v16h16v-8M10 14l2-5 7-7 3 3-7 7Z"/>',
    "new-folder": '<path d="M3 7V5h6l2 2h10v13H3ZM12 10v7M8.5 13.5h7"/>',
    "collapse": '<path d="m7 8 5-5 5 5M7 16l5 5 5-5"/>',
    "refresh": '<path d="M20 10a8 8 0 0 0-14-5L3 8M3 3v5h5M4 14a8 8 0 0 0 14 5l3-3M21 21v-5h-5"/>',
    "panel": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/>',
    "book": '<path d="M12 5v15M12 6C9 4 6 4 3 5v14c3-1 6-1 9 1 3-2 6-2 9-1V5c-3-1-6-1-9 1Z"/>',
    "edit": '<path d="m5 16 1-5L17 2l4 4-11 11-5 1ZM14 5l4 4M4 22h16"/>',
    "more": '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
    "plus": '<path d="M12 4v16M4 12h16"/>',
    "close": '<path d="m6 6 12 12M18 6 6 18"/>',
    "save": '<path d="M4 3h14l3 3v15H3V3ZM7 3v6h10V3M7 21v-8h10v8"/>',
}


def line_icon(name: str) -> QIcon:
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
           'fill="none" stroke="#7A7A7A" stroke-width="1.6" '
           'stroke-linecap="round" stroke-linejoin="round">' + PATHS[name] + '</svg>')
    pixmap = QPixmap(40, 40)
    pixmap.fill(Qt.transparent)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def icon_button(name, label, action=None, *, parent=None):
    button = QPushButton(parent=parent, objectName="iconButton")
    button.setIcon(line_icon(name))
    button.setIconSize(QSize(18, 18))
    button.setFixedSize(30, 28)
    button.setAccessibleName(label)
    button.setToolTip(label)
    if action:
        button.clicked.connect(action)
    return button
