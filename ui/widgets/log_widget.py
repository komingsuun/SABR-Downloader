from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QTextEdit

from core.config import load_config


class LogWidget(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 9))

    def append_log(self, text: str):
        self.append(text)
        if load_config().get("ui", {}).get("auto_scroll_log", True):
            self.moveCursor(QTextCursor.End)