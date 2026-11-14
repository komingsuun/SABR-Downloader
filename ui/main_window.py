from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget, QSizeGrip, QFrame, QSizePolicy,
)

from ui.pages.compression_page import CompressionPage
from ui.pages.cutter_page import CutterPage
from ui.pages.downloader_page import DownloaderPage
from ui.pages.settings_page import SettingsPage
from core.config import load_config


STYLESHEET = """
/* ---- Base: QMainWindow transparan, JANGAN beri background solid ---- */
QMainWindow {
    background: transparent;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}

/* Semua widget mewarisi warna teks & font, TANPA background */
QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}

/* ---- Root frame: wajah window rounded ---- */
QFrame#rootFrame {
    background-color: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
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

/* ---- Sidebar ---- */
QWidget#sidebar {
    background-color: #0b1220;
    border-right: 1px solid #1e293b;
    border-bottom-left-radius: 12px;
}
QLabel#brand { color: #38bdf8; font-size: 20px; font-weight: 700; padding: 12px 8px; }
QPushButton#navBtn {
    text-align: left; padding: 10px 14px; border: 1px solid transparent;
    border-radius: 8px; background-color: transparent; color: #cbd5e1;
}
QPushButton#navBtn:hover { background-color: #1e293b; color: #e2e8f0; }
QPushButton#navBtn:checked {
    background-color: #0ea5e9; color: #0f172a; font-weight: 800;
}

/* ---- Pages area: ikut rounded kanan bawah ---- */
QStackedWidget {
    background-color: transparent;
    border-bottom-right-radius: 12px;
}

/* ---- Custom Title Bar ---- */
QLabel#titleBarText {
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    padding-left: 4px;
}
QLabel#titleBarIcon {
    padding-left: 12px;
    padding-right: 6px;
}

QPushButton#primaryBtn {
    background-color: transparent;
    border: px solid transparent;
    background-image: url(assets/btn_primary.svg);
    background-position: center;
    background-repeat: no-repeat;
    border-radius: 8px;
    color: white;
    font-size: 14px;
    font-weight: 700;
    padding: 15px;
    min-width: 130px;
    max-width: 130px;
    min-height: 50px;
    max-height: 50px;
}
QPushButton#primaryBtn:hover {
    background-image: url(assets/btn_Hover.svg);
    background-position: center;
    background-repeat: no-repeat;
    background-color: transparent; 
}
QPushButton#primaryBtn:disabled {
    background-image: url(assets/btn_disbld.svg);
    background-position: center;
    background-repeat: no-repeat;
    background-color: transparent; 
}

QPushButton#dangerBtn {
    background-color: transparent;
    border: px solid transparent;
    background-image: url(assets/btn_danger.svg);
    background-position: center;
    background-repeat: no-repeat;
    border-radius: 8px;
    color: white;
    font-size: 14px;
    font-weight: 700;
    padding: 15px;
    min-width: 130px;
    max-width: 130px;
    min-height: 50px;
    max-height: 50px;
}
QPushButton#dangerBtn:hover {
    background-image: url(assets/btn_Hover.svg);
    background-position: center;
    background-repeat: no-repeat;
    background-color: transparent; 
}
QPushButton#dangerBtn:disabled {
    background-image: url(assets/btn_disbld.svg);
    background-position: center;
    background-repeat: no-repeat;
    background-color: transparent; 
}

QPushButton#cleanLogBtn {
    background-color: transparent;
    border: px solid transparent;
    background-image: url(assets/btn_cleanLogBtn.svg);
    background-position: center;
    background-repeat: no-repeat;
    border-radius: 8px;
    color: black;
    font-size: 14px;
    font-weight: 700;;
    font-size: 14px;;
    font-size: 14px;
    font-weight: 700;
    padding: 15px;
    min-width: 130px;
    max-width: 130px;
    min-height: 50px;
    max-height: 50px;
}
QPushButton#cleanLogBtn:hover {
    background-image: url(assets/btn_Hover.svg);
    background-position: center;
    background-repeat: no-repeat;
    background-color: transparent; 
}
QPushButton#cleanLogBtn:disabled {
    background-image: url(assets/btn_disbld.svg);
    background-position: center;
    background-repeat: no-repeat;
    background-color: transparent; 
}

QPushButton#titleBarCloseBtn {
    background-color: #ff0000;
    border: none;
    border-radius: 12px;
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
    padding: 0px;
    margin-right: 5px;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
}

QPushButton#titleBarCloseBtn:hover { background-color: #ff0000; color: #ffff00; }
QPushButton#titleBarCloseBtn:pressed { background-color: #273449; }

QPushButton#winBtn {
    background-color: transparent;
    border: none;
    border-radius: 0px;
    color: #cbd5e1;
    font-size: 14px;
    font-weight: 700;
    padding: 0;
    min-width: 46px;
    max-width: 46px;
    min-height: 36px;
    max-height: 36px;
}
QPushButton#winBtn:hover { background-color: #1e293b; color: #e2e8f0; }
QPushButton#winBtn:pressed { background-color: #273449; }

QPushButton#closeBtn {
    background-color: transparent;
    border: none;
    border-radius: 0px;
    color: #cbd5e1;
    font-size: 14px;
    font-weight: 700;
    padding: 0;
    min-width: 46px;
    max-width: 46px;
    min-height: 36px;
    max-height: 36px;
}
QPushButton#closeBtn:hover { background-color: #ef4444; color: #ffffff; }
QPushButton#closeBtn:pressed { background-color: #b91c1c; }
/* ---- Scroll area: viewport & isinya transparan ---- */
QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QScrollArea > QWidget > QScrollBar {
    background: #0b1220;
}

/* ---- Group box: sesuaikan dengan tema gelap ---- */
QGroupBox {
    background-color: #0b1220;
    border: 1px solid #1e293b;
    border-radius: 10px;
    margin-top: 12px;
    padding: 12px 10px 10px 10px;
    font-weight: 700;
    color: #cbd5e1;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #38bdf8;
    background-color: #0f172a;
}

/* ---- Widget pembungkus di dalam page ---- */
QWidget#settingsPage {
    background: transparent;
}
"""


class CustomTitleBar(QWidget):
    """Title bar kustom: icon + judul + tombol window control."""

    HEIGHT = 40

    def __init__(self, window: "MainWindow", title: str = "ClipCraft"):
        super().__init__(window)
        self._window = window
        self.setObjectName("titleBar")
        self.setFixedHeight(self.HEIGHT)

        # Title bar transparan — background gelap berasal dari rootFrame
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        inner = QHBoxLayout(self)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # Icon
        icon = QLabel()
        icon.setObjectName("titleBarIcon")
        pixmap = QPixmap("./assets/clip_craft_square.png")
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            icon.setPixmap(pixmap)
        icon.setFixedSize(40, self.HEIGHT)
        icon.setAlignment(Qt.AlignCenter)
        inner.addWidget(icon)

        # Title text
        self.title_label = QLabel(title)
        self.title_label.setObjectName("titleBarText")
        # self.title_label.setStyleSheet("background: transparent;")
        inner.addWidget(self.title_label)

        inner.addStretch()

        # Window control buttons
        self.btn_min = self._win_button("—", "winBtn")
        self.btn_max = self._win_button("□", "winBtn")
        self.btn_close = self._win_button("✕", "closeBtn")
        self.btn_close.setObjectName("titleBarCloseBtn")
        inner.addWidget(self.btn_min)

        self.btn_min.clicked.connect(self._window.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max)
        self.btn_close.clicked.connect(self._window.close)

        inner.addWidget(self.btn_min)
        inner.addWidget(self.btn_max)
        inner.addWidget(self.btn_close)

        # Update tombol maximize saat state berubah
        self._window.windowStateChanged = self._on_state_changed

    # ---- helpers ----
    @staticmethod
    def _win_button(text: str, obj_name: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName(obj_name)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setFixedSize(36, 30)
        return btn

    def _toggle_max(self):
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    def _on_state_changed(self, _state):
        if self._window.isMaximized():
            self.btn_max.setText("❐")
            self.btn_max.setToolTip("Restore")
        else:
            self.btn_max.setText("□")
            self.btn_max.setToolTip("Maximize")

    # ---- drag via system move (metode yang sukses) ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            window_handle = self._window.windowHandle()
            if window_handle is not None:
                window_handle.startSystemMove()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._toggle_max()
            event.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClipCraft")
        self.resize(960, 700)

        # ==== Frameless + translucent ====
        self.setWindowFlags(
            Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinMaxButtonsHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # ==== Root frame: wajah window rounded ====
        self.root_frame = QFrame()
        self.root_frame.setObjectName("rootFrame")
        self.root_frame.setStyleSheet(STYLESHEET)
        self.setCentralWidget(self.root_frame)

        root_layout = QVBoxLayout(self.root_frame)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ==== Custom Title Bar ====
        self.title_bar = CustomTitleBar(self, "ClipCraft")
        root_layout.addWidget(self.title_bar)

        # ==== Body (sidebar + pages) ====
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        root_layout.addWidget(body, stretch=1)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 16, 12, 16)
        side_layout.setSpacing(6)

        brand = QLabel()
        brand.setObjectName("brand")
        pixmap = QPixmap("./assets/clip_craft.png")
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                150, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            brand.setPixmap(pixmap)
        brand.setScaledContents(False)
        brand.setAutoFillBackground(False)

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

        body_layout.addWidget(sidebar)

        # Pages
        self.pages = QStackedWidget()
        self.page_downloader = DownloaderPage()
        self.page_compression = CompressionPage()
        self.page_cutter = CutterPage()
        self.page_settings = SettingsPage()
        for p in (self.page_downloader, self.page_compression,
                  self.page_cutter, self.page_settings):
            self.pages.addWidget(p)
        body_layout.addWidget(self.pages, stretch=1)

        # Resize grip di pojok kanan bawah
        self.size_grip = QSizeGrip(self.root_frame)

        # Wire navigation
        self.btn_downloader.clicked.connect(lambda: self._go(0, self.btn_downloader))
        self.btn_compression.clicked.connect(lambda: self._go(1, self.btn_compression))
        self.btn_cutter.clicked.connect(lambda: self._go(2, self.btn_cutter))
        self.btn_settings.clicked.connect(lambda: self._go(3, self.btn_settings))

        self._go(0, self.btn_downloader)

        self._center_on_screen()

    def _center_on_screen(self):
        screen = QGuiApplication.screenAt(self.pos()) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(geo.center())
        self.move(frame.topLeft())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "size_grip"):
            self.size_grip.move(
                self.root_frame.width() - self.size_grip.width(),
                self.root_frame.height() - self.size_grip.height(),
            )
            self.size_grip.raise_()

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