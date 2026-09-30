"""Qt workers keep directory scans and full-vault search off the UI thread."""

from dataclasses import dataclass

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


@dataclass(frozen=True)
class Result:
    value: object = None
    error: str = ""


class Signals(QObject):
    finished = Signal(object)


class Work(QRunnable):
    def __init__(self, operation):
        super().__init__()
        self.operation = operation
        self.signals = Signals()

    @Slot()
    def run(self):
        try:
            result = Result(value=self.operation())
        except (OSError, ValueError) as error:
            result = Result(error=str(error))
        self.signals.finished.emit(result)
