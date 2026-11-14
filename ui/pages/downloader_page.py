import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from core.downloader import COOKIE_BROWSERS
from core.workers import DownloadWorker
from core.config import load_config
from ui.widgets.log_widget import LogWidget


class DownloaderPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        cfg = load_config()
        self.worker = None
        self.output_dir = cfg["paths"]["download_dir"] or os.getcwd()
        self._build_ui()
        # apply default dari config
        self.folder_input.setText(self.output_dir)
        idx = self.cookies_combo.findData(cfg["downloader"]["cookies_browser"])
        self.cookies_combo.setCurrentIndex(max(0, idx))
        idx = self.compression_combo.findData(cfg["downloader"]["compression_preset"])
        self.compression_combo.setCurrentIndex(max(0, idx))
        self.noplaylist_cb.setChecked(bool(cfg["downloader"]["noplaylist"]))

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        header = QLabel("Video Downloader")
        header.setObjectName("header")
        root.addWidget(header)
        subtitle = QLabel("Unduh video/audio dengan yt-dlp")
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)

        # URL
        root.addWidget(self._label("URL Video / Media"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_input.returnPressed.connect(self.start_download)
        root.addWidget(self.url_input)

        # Folder
        root.addWidget(self._label("Folder Keluaran"))
        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit(self.output_dir)
        self.folder_input.setReadOnly(True)
        folder_row.addWidget(self.folder_input)
        browse_btn = QPushButton("Pilih Folder…")
        browse_btn.clicked.connect(self.choose_folder)
        folder_row.addWidget(browse_btn)
        root.addLayout(folder_row)

        # noplaylist
        options_row = QHBoxLayout()
        self.noplaylist_cb = QCheckBox("Hanya unduh 1 video (noplaylist)")
        self.noplaylist_cb.setChecked(True)
        options_row.addWidget(self.noplaylist_cb)
        options_row.addStretch()
        root.addLayout(options_row)

        # Cookies
        cookies_row = QHBoxLayout()
        cookies_row.addWidget(self._label("Cookie dari Browser"))
        self.cookies_combo = QComboBox()
        for label, value in COOKIE_BROWSERS:
            self.cookies_combo.addItem(label, value)
        self.cookies_combo.setMinimumWidth(200)
        cookies_row.addWidget(self.cookies_combo)
        note = QLabel(
            "Untuk konten yang butuh login. Chrome butuh paket 'secretstorage'."
        )
        note.setObjectName("detailLabel")
        cookies_row.addWidget(note)
        cookies_row.addStretch()
        root.addLayout(cookies_row)

        # Compression preset (kompres setelah unduh)
        comp_row = QHBoxLayout()
        comp_row.addWidget(self._label("Kualitas Output Video"))
        self.compression_combo = QComboBox()
        self.compression_combo.addItem("Original — tanpa kompresi", "Original")
        self.compression_combo.addItem("High — kualitas tinggi", "High")
        self.compression_combo.addItem("Balanced — rekomendasi", "Balanced")
        self.compression_combo.addItem("Compact — ukuran lebih kecil", "Compact")
        self.compression_combo.addItem("Small — ukuran minimal", "Small")
        self.compression_combo.setCurrentIndex(2)
        self.compression_combo.setMinimumWidth(250)
        comp_row.addWidget(self.compression_combo)
        comp_row.addStretch()
        root.addLayout(comp_row)

        cnote = QLabel("Audio dipertahankan tanpa re-encoding. Kompresi membutuhkan FFmpeg.")
        cnote.setObjectName("detailLabel")
        root.addWidget(cnote)

        # Progress
        progress_frame = QFrame()
        progress_frame.setObjectName("progressFrame")
        pl = QVBoxLayout(progress_frame)
        pl.setContentsMargins(14, 12, 14, 12)
        pl.setSpacing(8)
        self.status_label = QLabel("Siap")
        self.status_label.setObjectName("statusLabel")
        pl.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        pl.addWidget(self.progress_bar)
        self.detail_label = QLabel("Kecepatan: -   |   ETA: -")
        self.detail_label.setObjectName("detailLabel")
        pl.addWidget(self.detail_label)
        root.addWidget(progress_frame)

        # Buttons
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
        self.clear_btn.setObjectName("cleanLogBtn")
        self.clear_btn.clicked.connect(lambda: self.log_output.clear())
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        # Log
        root.addWidget(self._label("Log"))
        self.log_output = LogWidget()
        root.addWidget(self.log_output, stretch=1)

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    # ---------- Handlers ----------
    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Keluaran", self.output_dir)
        if folder:
            self.output_dir = folder
            self.folder_input.setText(folder)

    def log(self, message: str):
        self.log_output.append_log(message)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Peringatan", "URL tidak boleh kosong.")
            return
        if self.worker and self.worker.isRunning():
            return

        browser = self.cookies_combo.currentData()
        self.progress_bar.setValue(0)
        self.status_label.setText("Memulai unduhan...")
        self.detail_label.setText("Kecepatan: -   |   ETA: -")
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.log("=" * 60)
        self.log(f"Memulai unduhan: {url}")
        self.log(f"Folder: {self.output_dir}")
        self.log(f"Preset output: {self.compression_combo.currentData()}")
        self.log(f"Cookie browser: {browser or 'tidak ada'}")

        self.worker = DownloadWorker(
            url=url,
            output_dir=self.output_dir,
            noplaylist=self.noplaylist_cb.isChecked(),
            compression_preset=self.compression_combo.currentData(),
            cookies_from_browser=browser,
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

    def has_active_worker(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def request_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(2000)