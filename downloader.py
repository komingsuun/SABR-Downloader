import os
import sys
import threading

import yt_dlp
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# ============================================================
# Worker Thread untuk menjalankan download tanpa freeze UI
# ============================================================
class DownloadWorker(QThread):
    progress_changed = Signal(float, str, str, str)  # percent, speed, eta, status
    log_message = Signal(str)
    finished_signal = Signal(bool, dict)

    def __init__(self, url: str, output_dir: str, noplaylist: bool, parent=None):
        super().__init__(parent)
        self.url = url
        self.output_dir = output_dir
        self.noplaylist = noplaylist
        self._cancel_requested = False

    # Hook progress dari yt-dlp
    def progress_hook(self, d):
        if self._cancel_requested:
            raise yt_dlp.utils.DownloadCancelled("Dibatalkan oleh pengguna")

        if d["status"] == "downloading":
            percent_str = d.get("_percent_str", "0%").strip()
            speed = d.get("_speed_str", "N/A").strip()
            eta = d.get("_eta_str", "N/A").strip()

            # Parse persentase ke float
            percent_val = 0.0
            try:
                percent_val = float(percent_str.replace("%", "").strip())
            except ValueError:
                pass

            self.progress_changed.emit(percent_val, speed, eta, "Mengunduh...")

        elif d["status"] == "finished":
            self.progress_changed.emit(100.0, "-", "-", "Memproses file...")
            self.log_message.emit("Unduhan selesai, memproses file...")

    def run(self):
        os.makedirs(self.output_dir, exist_ok=True)

        ydl_opts = {
            "format": "bv*+ba/b",
            "outtmpl": os.path.join(
                self.output_dir,
                "%(title).200s [%(id)s].%(ext)s",
            ),
            "js_runtimes": {
                "node": {"path": "/home/pyy/.nvm/versions/node/v22.23.4/bin/node"}
            },
            "remote_components": ["ejs:github"],
            "sleep_interval_requests": 1,
            "sleep_interval": 2,
            "max_sleep_interval": 5,
            "writethumbnail": True,
            "embedthumbnail": True,
            "addmetadata": True,
            "progress_hooks": [self.progress_hook],
            "noplaylist": self.noplaylist,
            "ignoreerrors": False,
            "continuedl": True,
            "overwrites": False,
            "verbose": False,
        }

        info = {}
        success = False

        try:
            self.log_message.emit(f"Memproses URL: {self.url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)

            if info:
                success = True
                self.log_message.emit("Unduhan berhasil!")
            else:
                self.log_message.emit("Gagal mendapatkan informasi media.")

        except yt_dlp.utils.DownloadCancelled as exc:
            self.log_message.emit(f"Unduhan dibatalkan: {exc}")

        except yt_dlp.utils.DownloadError as exc:
            self.log_message.emit(f"Unduhan gagal: {exc}")

        except Exception as exc:
            self.log_message.emit(f"Error {type(exc).__name__}: {exc}")

        self.finished_signal.emit(success, info or {})

    def cancel(self):
        self._cancel_requested = True


# ============================================================
# Main Window
# ============================================================
class VideoDownloaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Downloader — yt-dlp")
        self.resize(780, 620)

        self.worker: DownloadWorker | None = None
        self.output_dir = os.path.join(os.getcwd(), "downloads")

        self._build_ui()
        self._apply_styles()

    # ---------------- UI Builder ----------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ---- Header ----
        header = QLabel("Video Downloader")
        header.setObjectName("header")
        root.addWidget(header)

        subtitle = QLabel("Unduh video/audio dengan yt-dlp")
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)

        # ---- URL Input ----
        url_label = QLabel("URL Video / Media")
        url_label.setObjectName("fieldLabel")
        root.addWidget(url_label)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.returnPressed.connect(self.start_download)
        root.addWidget(self.url_input)

        # ---- Output Folder ----
        folder_label = QLabel("Folder Keluaran")
        folder_label.setObjectName("fieldLabel")
        root.addWidget(folder_label)

        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit(self.output_dir)
        self.folder_input.setReadOnly(True)
        folder_row.addWidget(self.folder_input)

        browse_btn = QPushButton("Pilih Folder…")
        browse_btn.clicked.connect(self.choose_folder)
        folder_row.addWidget(browse_btn)
        root.addLayout(folder_row)

        # ---- Options ----
        options_row = QHBoxLayout()
        self.noplaylist_cb = QCheckBox("Hanya unduh 1 video (noplaylist)")
        self.noplaylist_cb.setChecked(True)
        options_row.addWidget(self.noplaylist_cb)
        options_row.addStretch()
        root.addLayout(options_row)

        # ---- Progress ----
        progress_frame = QFrame()
        progress_frame.setObjectName("progressFrame")
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(14, 12, 14, 12)
        progress_layout.setSpacing(8)

        self.status_label = QLabel("Siap")
        self.status_label.setObjectName("statusLabel")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)

        self.detail_label = QLabel("Kecepatan: -   |   ETA: -")
        self.detail_label.setObjectName("detailLabel")
        progress_layout.addWidget(self.detail_label)

        root.addWidget(progress_frame)

        # ---- Buttons ----
        btn_row = QHBoxLayout()
        self.download_btn = QPushButton("Mulai Unduh")
        self.download_btn.setObjectName("primaryBtn")
        self.download_btn.clicked.connect(self.start_download)
        btn_row.addWidget(self.download_btn)

        self.cancel_btn = QPushButton("Batalkan")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        btn_row.addWidget(self.cancel_btn)

        self.clear_btn = QPushButton("Bersihkan Log")
        self.clear_btn.clicked.connect(lambda: self.log_output.clear())
        btn_row.addWidget(self.clear_btn)

        btn_row.addStretch()
        root.addLayout(btn_row)

        # ---- Log ----
        log_label = QLabel("Log")
        log_label.setObjectName("fieldLabel")
        root.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Consolas", 9))
        root.addWidget(self.log_output, stretch=1)

    # ---------------- Styles ----------------
    def _apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: 'Segoe UI', 'Inter', sans-serif;
                font-size: 13px;
            }
            QLabel#header {
                font-size: 24px;
                font-weight: 700;
                color: #38bdf8;
            }
            QLabel#subtitle {
                color: #94a3b8;
                margin-bottom: 6px;
            }
            QLabel#fieldLabel {
                color: #cbd5e1;
                font-weight: 600;
                margin-top: 4px;
            }
            QLabel#statusLabel {
                font-weight: 600;
                color: #38bdf8;
            }
            QLabel#detailLabel {
                color: #94a3b8;
                font-size: 12px;
            }
            QLineEdit, QTextEdit {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 10px;
                color: #e2e8f0;
                selection-background-color: #0ea5e9;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
            QPushButton {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px 16px;
                color: #e2e8f0;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #273449;
                border-color: #38bdf8;
            }
            QPushButton:disabled {
                color: #64748b;
                background-color: #172033;
                border-color: #1e293b;
            }
            QPushButton#primaryBtn {
                background-color: #0ea5e9;
                border: none;
                color: #0f172a;
            }
            QPushButton#primaryBtn:hover {
                background-color: #38bdf8;
            }
            QPushButton#primaryBtn:disabled {
                background-color: #1e3a52;
                color: #64748b;
            }
            QPushButton#dangerBtn {
                background-color: #7f1d1d;
                border: 1px solid #991b1b;
                color: #fecaca;
            }
            QPushButton#dangerBtn:hover {
                background-color: #991b1b;
            }
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
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0ea5e9, stop:1 #22d3ee
                );
                border-radius: 6px;
            }
            QFrame#progressFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
            }
            QCheckBox {
                color: #cbd5e1;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #0ea5e9;
                border-color: #0ea5e9;
            }
            """
        )

    # ---------------- Handlers ----------------
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Pilih Folder Keluaran", self.output_dir
        )
        if folder:
            self.output_dir = folder
            self.folder_input.setText(folder)

    def log(self, message: str):
        self.log_output.append(message)
        self.log_output.moveCursor(QTextCursor.End)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Peringatan", "URL tidak boleh kosong.")
            return

        if self.worker and self.worker.isRunning():
            return

        # Reset UI
        self.progress_bar.setValue(0)
        self.status_label.setText("Memulai unduhan...")
        self.detail_label.setText("Kecepatan: -   |   ETA: -")
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.log("=" * 60)
        self.log(f"Memulai unduhan: {url}")
        self.log(f"Folder: {self.output_dir}")

        # Start worker
        self.worker = DownloadWorker(
            url=url,
            output_dir=self.output_dir,
            noplaylist=self.noplaylist_cb.isChecked(),
        )
        self.worker.progress_changed.connect(self.on_progress)
        self.worker.log_message.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def cancel_download(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("Membatalkan...")
            self.log("Permintaan pembatalan dikirim.")
            self.cancel_btn.setEnabled(False)

    def on_progress(self, percent: float, speed: str, eta: str, status: str):
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(status)
        self.detail_label.setText(f"Kecepatan: {speed}   |   ETA: {eta}")

    def on_finished(self, success: bool, info: dict):
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Selesai ✓")
            self.log("-" * 60)
            self.log(f"Judul  : {info.get('title', '-')}")
            self.log(f"Situs  : {info.get('extractor_key', '-')}")
            self.log(f"Folder : {os.path.abspath(self.output_dir)}")
            self.log("-" * 60)
        else:
            self.status_label.setText("Gagal / Dibatalkan")

        self.worker = None

    # ---------------- Close Event ----------------
    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Konfirmasi",
                "Unduhan masih berjalan. Batalkan dan keluar?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.worker.cancel()
                self.worker.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


# ============================================================
# Entry point
# ============================================================
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Video Downloader")
    window = VideoDownloaderWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()