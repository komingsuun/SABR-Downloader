from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from ui.pages.compression_page import CompressionPage
from ui.pages.cutter_page import CutterPage
from ui.pages.downloader_page import DownloaderPage
from ui.pages.settings_page import SettingsPage
from core.config import load_config


STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0f172a;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}
QLabel#header { font-size: 24px; font-weight: 700; color: #38bdf8; }
QLabel#subtitle { color: #94a3b8; margin-bottom: 6px; }
QLabel#fieldLabel { color: #cbd5e1; font-weight: 600; margin-top: 4px; }
QLabel#statusLabel { font-weight: 600; color: #38bdf8; }
QLabel#detailLabel { color: #94a3b8; font-size: 12px; }
QLineEdit, QTextEdit, QComboBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 10px;
    color: #e2e8f0;
    selection-background-color: #0ea5e9;
}
QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #e2e8f0;
    selection-background-color: #0ea5e9;
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #38bdf8; }
QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 16px;
    color: #e2e8f0;
    font-weight: 600;
}
QPushButton:hover { background-color: #273449; border-color: #38bdf8; }
QPushButton:disabled { color: #64748b; background-color: #172033; border-color: #1e293b; }
QPushButton#primaryBtn { background-color: #0ea5e9; border: none; color: #0f172a; }
QPushButton#primaryBtn:hover { background-color: #38bdf8; }
QPushButton#primaryBtn:disabled { background-color: #1e3a52; color: #64748b; }
QPushButton#dangerBtn { background-color: #7f1d1d; border: 1px solid #991b1b; color: #fecaca; }
QPushButton#dangerBtn:hover { background-color: #991b1b; }
QProgressBar {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    height: 22px;
    text-align: center;
    color: #e2e8f0;
    font-weight: 600;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0ea5e9, stop:1 #22d3ee);
    border-radius: 6px;
}
QFrame#progressFrame {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
}
QCheckBox { color: #cbd5e1; spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid #475569; background-color: #1e293b;
}
QCheckBox::indicator:checked { background-color: #0ea5e9; border-color: #0ea5e9; }

/* Sidebar */
QWidget#sidebar { background-color: #0b1220; border-right: 1px solid #1e293b; }
QLabel#brand { color: #38bdf8; font-size: 20px; font-weight: 700; padding: 12px 8px; }
QPushButton#navBtn {
    text-align: left; padding: 10px 14px; border: 1px solid transparent;
    border-radius: 8px; background-color: transparent; color: #cbd5e1;
}
QPushButton#navBtn:hover { background-color: #1e293b; color: #e2e8f0; }
QPushButton#navBtn:checked {
    background-color: #0ea5e9; color: #0f172a; font-weight: 700;
}
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClipCraft")
        self.resize(960, 700)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 16, 12, 16)
        side_layout.setSpacing(6)

        brand = QLabel("ClipCraft")
        brand.setObjectName("brand")
        side_layout.addWidget(brand)

        self.btn_downloader = self._nav_button("Downloader")
        self.btn_compression = self._nav_button("Video Compression")
        self.btn_cutter = self._nav_button("Video Cutter")
        self.btn_settings = self._nav_button("Settings")
        for b in (self.btn_downloader, self.btn_compression,
                  self.btn_cutter, self.btn_settings):
            side_layout.addWidget(b)
        side_layout.addStretch()
        side_layout.addWidget(QLabel("v0.1 — ClipCraft", objectName="detailLabel"))

        main_layout.addWidget(sidebar)

        # Pages
        self.pages = QStackedWidget()
        self.page_downloader = DownloaderPage()
        self.page_compression = CompressionPage()
        self.page_cutter = CutterPage()
        self.page_settings = SettingsPage()
        for p in (self.page_downloader, self.page_compression,
                  self.page_cutter, self.page_settings):
            self.pages.addWidget(p)
        main_layout.addWidget(self.pages, stretch=1)

        # Wire navigation
        self.btn_downloader.clicked.connect(lambda: self._go(0, self.btn_downloader))
        self.btn_compression.clicked.connect(lambda: self._go(1, self.btn_compression))
        self.btn_cutter.clicked.connect(lambda: self._go(2, self.btn_cutter))
        self.btn_settings.clicked.connect(lambda: self._go(3, self.btn_settings))

        self._go(0, self.btn_downloader)

    @staticmethod
    def _nav_button(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("navBtn")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        return btn

    def _go(self, index: int, btn: QPushButton):
        for b in (self.btn_downloader, self.btn_compression,
                  self.btn_cutter, self.btn_settings):
            b.setChecked(b is btn)
        self.pages.setCurrentIndex(index)

    def closeEvent(self, event):
        active = []
        if self.page_downloader.has_active_worker():
            active.append("Downloader")
        if self.page_compression.has_active_worker():
            active.append("Video Compression")
        if self.page_cutter.has_active_worker():
            active.append("Video Cutter")
        if active and load_config()["ui"]["confirm_on_exit"]:
            reply = QMessageBox.question(
                self, "Konfirmasi",
                f"Proses masih berjalan ({', '.join(active)}). Batalkan dan keluar?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.page_downloader.request_cancel()
                self.page_compression.request_cancel()
                self.page_cutter.request_cancel()
                event.accept()
            else:
                event.ignore()
        else:
            if active:
                self.page_downloader.request_cancel()
                self.page_compression.request_cancel()
                self.page_cutter.request_cancel()
            event.accept()