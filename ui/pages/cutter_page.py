import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)

from core.ffmpeg import probe_media
from core.video_cutter import ensure_cut_dir
from core.workers import CutterWorker, ThumbnailWorker
from ui.widgets.log_widget import LogWidget
from ui.widgets.timeline_widget import TimelineWidget


def _parse_time(text: str) -> float:
    """Terima: 12 (detik), 1:23 (m:s), 01:02:03 (h:m:s), 1:02:03.500."""
    text = (text or "").strip()
    if not text:
        raise ValueError("kosong")
    parts = text.split(":")
    if len(parts) == 1:
        return float(parts[0])
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError("format waktu tidak dikenal")


def _fmt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h:
        return f"{h}:{m:02d}:{s:05.2f}"
    return f"{m}:{s:05.2f}"


class CutterPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: CutterWorker | None = None
        self.thumb_worker: ThumbnailWorker | None = None
        self._duration = 0.0
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        header = QLabel("Video Cutter")
        header.setObjectName("header")
        root.addWidget(header)
        subtitle = QLabel("Potong klip dari file lokal (ffmpeg). Drag handle di timeline untuk memilih range.")
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

        self.duration_label = QLabel("Durasi: -")
        self.duration_label.setObjectName("detailLabel")
        root.addWidget(self.duration_label)

        # Timeline
        root.addWidget(self._label("Timeline"))
        self.timeline = TimelineWidget()
        self.timeline.range_changed.connect(self._on_timeline_range_changed)
        root.addWidget(self.timeline)

        self.thumb_status = QLabel("Thumbnail: -")
        self.thumb_status.setObjectName("detailLabel")
        root.addWidget(self.thumb_status)

        # Start / End manual
        time_row = QHBoxLayout()
        time_row.addWidget(self._label("Mulai"))
        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("0:04.00")
        self.start_input.editingFinished.connect(self._on_start_edit)
        time_row.addWidget(self.start_input)

        time_row.addWidget(self._label("Akhir"))
        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("0:12.61")
        self.end_input.editingFinished.connect(self._on_end_edit)
        time_row.addWidget(self.end_input)
        root.addLayout(time_row)

        # Tombol bantu range
        btn_range = QHBoxLayout()
        set_start_btn = QPushButton("Set Start di Playhead")
        set_start_btn.setToolTip("Set start ke posisi tengah seleksi (atau 0 bila kosong)")
        set_start_btn.clicked.connect(self._set_start_mid)
        set_end_btn = QPushButton("Set End di Playhead")
        set_end_btn.clicked.connect(self._set_end_mid)
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_range)
        btn_range.addWidget(set_start_btn)
        btn_range.addWidget(set_end_btn)
        btn_range.addWidget(reset_btn)
        btn_range.addStretch()
        root.addLayout(btn_range)

        # Output
        root.addWidget(self._label("Folder Output"))
        out_row = QHBoxLayout()
        self.output_input = QLineEdit(ensure_cut_dir())
        self.output_input.setReadOnly(True)
        out_row.addWidget(self.output_input)
        open_btn = QPushButton("Buka Folder")
        open_btn.clicked.connect(lambda: self._open_folder(self.output_input.text()))
        out_row.addWidget(open_btn)
        root.addLayout(out_row)

        self.reencode_cb = QCheckBox("Re-encode (akurat frame-by-frame; lebih lambat)")
        root.addWidget(self.reencode_cb)

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

        # Actions
        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Mulai Potong")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.clicked.connect(self.start_cut)
        btn_row.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("Batalkan")
        self.cancel_btn.setObjectName("dangerBtn")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_cut)
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

    # ---------- file loading ----------
    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Video", "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.ts);;All Files (*)",
        )
        if not path:
            return
        self.file_input.setText(path)
        self.log("=" * 60)
        self.log(f"Sumber: {path}")

        if self.thumb_worker and self.thumb_worker.isRunning():
            self.thumb_worker.cancel()
            self.thumb_worker.wait(1000)

        self.timeline.clear_thumbnails()

        try:
            dur, _, has_video = probe_media(path)
        except Exception as exc:
            self.duration_label.setText(f"Durasi: gagal probe ({exc})")
            self._duration = 0.0
            self.timeline.set_duration(0.0)
            return

        if not has_video:
            self.duration_label.setText("Durasi: file tidak memiliki video stream")
            self._duration = 0.0
            self.timeline.set_duration(0.0)
            return

        self._duration = dur
        self.duration_label.setText(f"Durasi: {_fmt_time(dur)}")
        self.timeline.set_duration(dur)
        self.timeline.set_range(0.0, dur)
        self.start_input.setText(_fmt_time(0.0))
        self.end_input.setText(_fmt_time(dur))

        # mulai thumbnail worker
        from core import thumbnails
        times = thumbnails.plan_thumbnail_times(dur)
        self.timeline.set_thumbnails_count(len(times))
        self.thumb_status.setText(f"Memuat 0/{len(times)} thumbnail...")

        self.thumb_worker = ThumbnailWorker(path, dur, len(times))
        self.thumb_worker.thumbnail_ready.connect(self._on_thumbnail_ready)
        self.thumb_worker.finished_signal.connect(self._on_thumbnails_done)
        self.thumb_worker.start()

    def _on_thumbnail_ready(self, index: int, image):
        self.timeline.set_thumbnail_at(index, image)
        # update status
        loaded = sum(1 for p in self.timeline._thumbs if not p.isNull())
        self.thumb_status.setText(f"Memuat {loaded}/{len(self.timeline._thumbs)} thumbnail...")

    def _on_thumbnails_done(self, success: bool, message: str):
        self.thumb_status.setText(f"Thumbnail: {message}")
        self.thumb_worker = None

    # ---------- range sync ----------
    def _on_timeline_range_changed(self, start: float, end: float):
        # sinkron ke line edit (hindari feedback loop dengan blockSignals)
        self.start_input.blockSignals(True)
        self.end_input.blockSignals(True)
        self.start_input.setText(_fmt_time(start))
        self.end_input.setText(_fmt_time(end))
        self.start_input.blockSignals(False)
        self.end_input.blockSignals(False)

    def _on_start_edit(self):
        try:
            val = _parse_time(self.start_input.text())
        except ValueError:
            self.start_input.setText(_fmt_time(self.timeline.start_seconds()))
            return
        self.timeline.set_range(val, self.timeline.end_seconds())
        self._on_timeline_range_changed(self.timeline.start_seconds(), self.timeline.end_seconds())

    def _on_end_edit(self):
        try:
            val = _parse_time(self.end_input.text())
        except ValueError:
            self.end_input.setText(_fmt_time(self.timeline.end_seconds()))
            return
        self.timeline.set_range(self.timeline.start_seconds(), val)
        self._on_timeline_range_changed(self.timeline.start_seconds(), self.timeline.end_seconds())

    def _set_start_mid(self):
        s = self.timeline.start_seconds()
        e = self.timeline.end_seconds()
        mid = (s + e) / 2
        self.timeline.set_range(mid, e)
        self._on_timeline_range_changed(self.timeline.start_seconds(), self.timeline.end_seconds())

    def _set_end_mid(self):
        s = self.timeline.start_seconds()
        e = self.timeline.end_seconds()
        mid = (s + e) / 2
        self.timeline.set_range(s, mid)
        self._on_timeline_range_changed(self.timeline.start_seconds(), self.timeline.end_seconds())

    def _reset_range(self):
        self.timeline.set_range(0.0, self._duration)
        self._on_timeline_range_changed(0.0, self._duration)

    # ---------- cut ----------
    def log(self, msg: str):
        self.log_output.append_log(msg)

    def start_cut(self):
        src = self.file_input.text().strip()
        if not src or not os.path.isfile(src):
            QMessageBox.warning(self, "Peringatan", "Pilih file video yang valid.")
            return
        if self.worker and self.worker.isRunning():
            return

        start = self.timeline.start_seconds()
        end = self.timeline.end_seconds()
        if end <= start:
            QMessageBox.warning(self, "Waktu", "Waktu akhir harus > waktu mulai.")
            return

        out_dir = ensure_cut_dir()
        self.output_input.setText(out_dir)

        self.progress_bar.setValue(0)
        self.status_label.setText("Memulai pemotongan...")
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.log("-" * 40)
        self.log(f"Range : {_fmt_time(start)} → {_fmt_time(end)}")
        self.log(f"Mode  : {'re-encode' if self.reencode_cb.isChecked() else 'copy'}")

        self.worker = CutterWorker(
            input_path=src,
            output_dir=out_dir,
            start_sec=start,
            end_sec=end,
            reencode=self.reencode_cb.isChecked(),
        )
        self.worker.progress_changed.connect(self.on_progress)
        self.worker.log_message.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def cancel_cut(self):
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
            self.log(f"File tersimpan: {message}")
        else:
            self.status_label.setText("Gagal / Dibatalkan")
            self.log(f"Gagal: {message}")
        self.worker = None

    def has_active_worker(self) -> bool:
        return (
            (self.worker is not None and self.worker.isRunning())
            or (self.thumb_worker is not None and self.thumb_worker.isRunning())
        )

    def request_cancel(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(2000)
        if self.thumb_worker and self.thumb_worker.isRunning():
            self.thumb_worker.cancel()
            self.thumb_worker.wait(2000)