import os

from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from core.workers import CompressWorker
from core.video_compressor import ensure_compressed_dir
from ui.widgets.log_widget import LogWidget


class CompressionPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: CompressWorker | None = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        header = QLabel("Video Compression")
        header.setObjectName("header")
        root.addWidget(header)
        subtitle = QLabel("Kompres file video lokal dengan FFmpeg (audio di-copy)")
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)

        # Input file
        root.addWidget(self._label("File Video Sumber"))
        file_row = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("Pilih file video...")
        self.file_input.setReadOnly(True)
        file_row.addWidget(self.file_input)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self.browse_file)
        file_row.addWidget(browse_btn)
        root.addLayout(file_row)

        # Output folder (read-only, fixed)
        out_dir = ensure_compressed_dir()
        root.addWidget(self._label("Folder Output"))
        out_row = QHBoxLayout()
        self.output_input = QLineEdit(out_dir)
        self.output_input.setReadOnly(True)
        out_row.addWidget(self.output_input)
        open_btn = QPushButton("Buka Folder")
        open_btn.clicked.connect(lambda: self._open_folder(out_dir))
        out_row.addWidget(open_btn)
        root.addLayout(out_row)

        # Preset
        preset_row = QHBoxLayout()
        preset_row.addWidget(self._label("Preset Kompresi"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("High — kualitas tinggi", "High")
        self.preset_combo.addItem("Balanced — rekomendasi", "Balanced")
        self.preset_combo.addItem("Compact — ukuran lebih kecil", "Compact")
        self.preset_combo.addItem("Small — ukuran minimal", "Small")
        self.preset_combo.setCurrentIndex(1)
        self.preset_combo.setMinimumWidth(250)
        preset_row.addWidget(self.preset_combo)
        preset_row.addStretch()
        root.addLayout(preset_row)

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
        pl.addWidget(self.progress_bar)
        root.addWidget(progress_frame)

        # Buttons
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Mulai Kompres")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.clicked.connect(self.start_compression)
        btn_row.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("Batalkan")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_compression)
        btn_row.addWidget(self.cancel_btn)

        clear_btn = QPushButton("Bersihkan Log")
        clear_btn.setObjectName("cleanLogBtn")
        clear_btn.clicked.connect(lambda: self.log_output.clear())
        btn_row.addWidget(clear_btn)
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

    @staticmethod
    def _open_folder(path: str):
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif os.uname().sysname == "Darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')
        except Exception:
            pass

    # ---------- Handlers ----------
    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Video", "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.ts);;All Files (*)",
        )
        if path:
            self.file_input.setText(path)

    def log(self, msg: str):
        self.log_output.append_log(msg)

    def start_compression(self):
        src = self.file_input.text().strip()
        if not src or not os.path.isfile(src):
            QMessageBox.warning(self, "Peringatan", "Pilih file video yang valid.")
            return
        if self.worker and self.worker.isRunning():
            return

        preset = self.preset_combo.currentData()
        out_dir = ensure_compressed_dir()
        self.output_input.setText(out_dir)

        self.progress_bar.setValue(0)
        self.status_label.setText("Memulai kompresi...")
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.log("=" * 60)
        self.log(f"Sumber  : {src}")
        self.log(f"Output  : {out_dir}")
        self.log(f"Preset  : {preset}")

        self.worker = CompressWorker(src, out_dir, preset)
        self.worker.progress_changed.connect(self.on_progress)
        self.worker.log_message.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def cancel_compression(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("Membatalkan...")
            self.log("Permintaan pembatalan dikirim.")
            self.cancel_btn.setEnabled(False)

    def on_progress(self, percent: float, speed: str, eta: str, status: str):
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(status)

    def on_finished(self, success: bool, message: str):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Selesai ✓")
        else:
            self.status_label.setText("Gagal / Dibatalkan")
            self.log(f"Gagal: {message}")
        self.worker = None

    def has_active_worker(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def request_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(2000)