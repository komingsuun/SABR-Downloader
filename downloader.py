#
# 100% Vibe Coding
# Program Download Sembarang Video
# Implementasi yt-dlp untuk mendukung pengunduhan video YouTube dengan Adaptive Bitrate Streaming (SABR)

# Siapkan env untuk project ini beserta package yang dibutuhkan
# - pip install -U "yt-dlp[default]"
# - pip install git+https://github.com/tribixbite/yt-dlp-threads
# - pip install pyside2
#
# Siapkan server PO (Proof of Origin) Token Providers
# - docker run --name bgutil-provider -d --init \\n  -p 127.0.0.1:4416:4416 brainicism/bgutil-ytdlp-pot-provider
# - docker start bgutil-provider (jalankan kontainer docker jika sudah melakukan create/init sebelumnya)

# Sebelumnya lakukan set dns jika hendak mengakses situs yang diblokir
# contohnya kalo pakai Claudflare spt berikut ini (meskipun tidak menjamin 100% dapat diakses):
#
# sudo resolvectl dns enp3s0 1.1.1.1 1.0.0.1
# sudo resolvectl flush-caches
#
# sudo resolvectl dns wlo1 1.1.1.1 1.0.0.1
# sudo resolvectl flush-caches
#
# Cek apakah situs yg diblokir sdh bisa diakses (kalau tidak lolos kemungkinan besar program ini akan failed):
# python -c "import requests; r=requests.get('https://situs_nakal_anda.com', timeout=15); print(r.status_code, r.url)"
#

import os
import sys
import shutil
import subprocess

import yt_dlp
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
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
# Preset: (scale factor, CRF). Audio selalu disalin tanpa re-encoding.
COMPRESSION_PRESETS = {
    "Original": None,
    "High": (1.00, 23),
    "Balanced": (0.75, 26),
    "Compact": (0.50, 28),
    "Small": (0.35, 30),
}


class DownloadWorker(QThread):
    progress_changed = Signal(float, str, str, str)  # percent, speed, eta, status
    log_message = Signal(str)
    finished_signal = Signal(bool, dict)

    def __init__(self, url: str, output_dir: str, noplaylist: bool, compression_preset: str = "Balanced", parent=None):
        super().__init__(parent)
        self.url = url
        self.output_dir = output_dir
        self.noplaylist = noplaylist
        self.compression_preset = compression_preset
        self._cancel_requested = False
        self._ffmpeg_process = None

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

    def _find_downloaded_file(self, info, ydl):
        """Find the final file produced by yt-dlp, including merged output."""
        if not isinstance(info, dict):
            return None
        candidates = [info.get("filepath"), info.get("_filename")]
        try:
            candidates.append(ydl.prepare_filename(info))
        except Exception:
            pass

        for item in info.get("requested_downloads") or []:
            candidates.extend([item.get("filepath"), item.get("_filename")])

        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return os.path.abspath(candidate)

        # Fallback: locate the downloaded file using the media ID.
        media_id = info.get("id")
        if media_id:
            suffix = f"[{media_id}]"
            for name in os.listdir(self.output_dir):
                path = os.path.join(self.output_dir, name)
                if suffix in name and os.path.isfile(path) and not name.endswith((".part", ".ytdl")):
                    return os.path.abspath(path)
        return None

    def _find_downloaded_files(self, info, ydl):
        """Return all completed media files (also supports playlist downloads)."""
        found = []
        entries = info.get("entries") if isinstance(info, dict) else None
        if entries:
            for entry in entries:
                path = self._find_downloaded_file(entry, ydl)
                if path and path not in found:
                    found.append(path)
        else:
            path = self._find_downloaded_file(info, ydl)
            if path:
                found.append(path)
        return found

    @staticmethod
    def _probe_media(path):
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            raise RuntimeError("ffprobe tidak ditemukan. Pastikan FFmpeg terpasang.")

        result = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,codec_name", "-of", "json", path],
            capture_output=True, text=True, check=True
        )
        import json
        data = json.loads(result.stdout or "{}")
        duration = float((data.get("format") or {}).get("duration") or 0)
        streams = data.get("streams") or []
        audio_codec = next((s.get("codec_name") for s in streams if s.get("codec_type") == "audio"), None)
        has_video = any(s.get("codec_type") == "video" for s in streams)
        return duration, audio_codec, has_video

    def _compress_video(self, input_path):
        preset = self.compression_preset
        settings = COMPRESSION_PRESETS.get(preset)
        if settings is None:
            self.log_message.emit("Preset Original: file dibiarkan tanpa kompresi.")
            return input_path

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("FFmpeg tidak ditemukan. Pastikan FFmpeg terpasang.")

        scale, crf = settings
        duration, audio_codec, has_video = self._probe_media(input_path)
        if not has_video:
            self.log_message.emit("File tidak memiliki stream video; kompresi dilewati.")
            return input_path

        # MP4 aman untuk codec audio umum berikut. Codec lainnya memakai MKV
        # agar stream audio dapat disalin apa adanya tanpa konversi.
        mp4_audio_codecs = {"aac", "mp3", "ac3", "eac3", "alac"}
        output_ext = ".mp4" if audio_codec is None or audio_codec in mp4_audio_codecs else ".mkv"
        base = os.path.splitext(input_path)[0]
        output_path = f"{base} [{preset}]{output_ext}"
        temp_path = f"{base} [{preset}].processing{output_ext}"

        if os.path.abspath(output_path) == os.path.abspath(input_path):
            raise RuntimeError("Nama file output sama dengan file sumber; kompresi dibatalkan.")

        # Jangan menimpa hasil sebelumnya.
        if os.path.exists(output_path):
            stem, ext = os.path.splitext(output_path)
            counter = 2
            while os.path.exists(f"{stem} ({counter}){ext}"):
                counter += 1
            output_path = f"{stem} ({counter}){ext}"
            temp_path = f"{os.path.splitext(output_path)[0]}.processing{ext}"

        vf = f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", input_path,
            "-map", "0:v:0", "-map", "0:a?",
            "-map_metadata", "0", "-map_chapters", "0",
            "-vf", vf, "-c:v", "libx264", "-preset", "medium",
            "-crf", str(crf), "-c:a", "copy",
        ]
        if output_ext == ".mp4":
            command += ["-movflags", "+faststart"]
        command += ["-progress", "pipe:1", "-nostats", temp_path]

        self.log_message.emit(
            f"Kompresi {preset}: skala {int(scale * 100)}%, CRF {crf}; "
            f"audio {audio_codec or 'tidak ada'} dipertahankan (copy)."
        )
        self.progress_changed.emit(0.0, "-", "-", "Mengompres video...")

        try:
            self._ffmpeg_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1
            )
            # FFmpeg mengirim progress berkala melalui stdout.
            for line in self._ffmpeg_process.stdout:
                if self._cancel_requested:
                    self._ffmpeg_process.terminate()
                    raise RuntimeError("Kompresi dibatalkan oleh pengguna.")
                line = line.strip()
                if line.startswith("out_time_ms=") and duration > 0:
                    try:
                        elapsed = int(line.split("=", 1)[1]) / 1_000_000
                        percent = min(99.0, max(0.0, elapsed / duration * 100))
                        self.progress_changed.emit(percent, "-", "-", "Mengompres video...")
                    except ValueError:
                        pass

            return_code = self._ffmpeg_process.wait()
            stderr = self._ffmpeg_process.stderr.read() if self._ffmpeg_process.stderr else ""
            if return_code != 0:
                raise RuntimeError(f"FFmpeg gagal: {stderr[-1200:]}")
            if not os.path.isfile(temp_path) or os.path.getsize(temp_path) == 0:
                raise RuntimeError("FFmpeg tidak menghasilkan file output.")

            os.replace(temp_path, output_path)
            self.progress_changed.emit(100.0, "-", "-", "Kompresi selesai")
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(output_path)
            if original_size:
                reduction = (1 - compressed_size / original_size) * 100
                self.log_message.emit(
                    f"Hasil kompresi: {output_path} ({compressed_size / 1024 / 1024:.2f} MB; "
                    f"perubahan ukuran {reduction:+.1f}%)."
                )
            else:
                self.log_message.emit(f"Hasil kompresi: {output_path}")
            return output_path
        finally:
            self._ffmpeg_process = None
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def run(self):
        os.makedirs(self.output_dir, exist_ok=True)

        ydl_opts = {
            "format": "bv*+ba/b",
            "outtmpl": os.path.join(
                self.output_dir,
                "%(title).200s [%(id)s].%(ext)s"
            ),
            "trim_file_name": 100,
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
                downloaded_paths = self._find_downloaded_files(info, ydl) if info else []

            if info and downloaded_paths:
                success = True
                self.log_message.emit(f"Unduhan berhasil: {len(downloaded_paths)} file.")
                if self.compression_preset != "Original":
                    for index, downloaded_path in enumerate(downloaded_paths, start=1):
                        if self._cancel_requested:
                            success = False
                            break
                        self.log_message.emit(
                            f"Memproses video {index}/{len(downloaded_paths)}: "
                            f"{os.path.basename(downloaded_path)}"
                        )
                        try:
                            self._compress_video(downloaded_path)
                        except Exception as exc:
                            self.log_message.emit(
                                f"Kompresi gagal ({exc}). File unduhan asli tetap tersedia."
                            )
                            if self._cancel_requested:
                                success = False
                                break
                else:
                    self.log_message.emit("Preset Original dipilih; tidak ada kompresi.")
            elif info:
                self.log_message.emit("Unduhan selesai, tetapi file hasil tidak ditemukan.")
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
        if self._ffmpeg_process and self._ffmpeg_process.poll() is None:
            self._ffmpeg_process.terminate()


# ============================================================
# Main Window
# ============================================================
class VideoDownloaderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Downloader — yt-dlp")
        self.resize(780, 680)

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

        # ---- Video Compression ----
        compression_row = QHBoxLayout()
        compression_label = QLabel("Kualitas Output Video")
        compression_label.setObjectName("fieldLabel")
        compression_row.addWidget(compression_label)

        self.compression_combo = QComboBox()
        self.compression_combo.addItem("Original — tanpa kompresi", "Original")
        self.compression_combo.addItem("High — kualitas tinggi", "High")
        self.compression_combo.addItem("Balanced — rekomendasi", "Balanced")
        self.compression_combo.addItem("Compact — ukuran lebih kecil", "Compact")
        self.compression_combo.addItem("Small — ukuran minimal", "Small")
        self.compression_combo.setCurrentIndex(2)
        self.compression_combo.setMinimumWidth(250)
        compression_row.addWidget(self.compression_combo)
        compression_row.addStretch()
        root.addLayout(compression_row)

        compression_note = QLabel("Audio dipertahankan tanpa re-encoding. Kompresi video membutuhkan FFmpeg.")
        compression_note.setObjectName("detailLabel")
        root.addWidget(compression_note)

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
            QLineEdit:focus, QComboBox:focus {
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
        self.log(f"Preset output: {self.compression_combo.currentData()}")

        # Start worker
        self.worker = DownloadWorker(
            url=url,
            output_dir=self.output_dir,
            noplaylist=self.noplaylist_cb.isChecked(),
            compression_preset=self.compression_combo.currentData(),
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