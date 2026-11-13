import os

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from core.config import config_path, load_config, reset_config, save_config
from core.downloader import COOKIE_BROWSERS
from core.ffmpeg import ffmpeg_version, get_ffmpeg, get_ffprobe


class _PathRow(QWidget):
    """LineEdit + tombol Browse (file atau folder)."""

    def __init__(self, mode: str = "dir"):
        super().__init__()
        self.mode = mode
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QLineEdit()
        layout.addWidget(self.edit)
        btn = QPushButton("Browse…")
        btn.clicked.connect(self._browse)
        layout.addWidget(btn)

    def _browse(self):
        if self.mode == "dir":
            path = QFileDialog.getExistingDirectory(self, "Pilih Folder", self.edit.text() or "")
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Pilih File", self.edit.text() or "")
        if path:
            self.edit.setText(path)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, value: str):
        self.edit.setText(value or "")


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._load_into_ui(load_config())

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(12)

        header = QLabel("Settings")
        header.setObjectName("header")
        outer.addWidget(header)
        subtitle = QLabel("Preferensi global ClipCraft. Tersimpan otomatis setelah klik Simpan.")
        subtitle.setObjectName("subtitle")
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form_root = QVBoxLayout(content)
        form_root.setContentsMargins(0, 0, 0, 0)
        form_root.setSpacing(12)

        # --- Paths ---
        g_paths = QGroupBox("Lokasi & Runtime")
        f_paths = QFormLayout(g_paths)
        self.download_dir = _PathRow("dir")
        self.compressed_dir = _PathRow("dir")
        self.cut_dir = _PathRow("dir")
        self.ffmpeg_path = _PathRow("file")
        self.ffprobe_path = _PathRow("file")
        self.node_path = _PathRow("file")
        f_paths.addRow("Folder unduhan", self.download_dir)
        f_paths.addRow("Folder kompresi", self.compressed_dir)
        f_paths.addRow("Folder cutter", self.cut_dir)
        f_paths.addRow("Path ffmpeg (opsional)", self.ffmpeg_path)
        f_paths.addRow("Path ffprobe (opsional)", self.ffprobe_path)
        f_paths.addRow("Path node (opsional)", self.node_path)
        self.ffmpeg_status = QLabel("-")
        self.ffmpeg_status.setObjectName("detailLabel")
        f_paths.addRow("Status FFmpeg", self.ffmpeg_status)
        check_row = QHBoxLayout()
        self.check_btn = QPushButton("Cek FFmpeg")
        self.check_btn.clicked.connect(self._check_ffmpeg)
        open_cfg_btn = QPushButton("Buka Folder Config")
        open_cfg_btn.clicked.connect(self._open_config_folder)
        check_row.addWidget(self.check_btn)
        check_row.addWidget(open_cfg_btn)
        check_row.addStretch()
        f_paths.addRow("", self._wrap(check_row))
        form_root.addWidget(g_paths)

        # --- Downloader defaults ---
        g_dl = QGroupBox("Default Downloader")
        f_dl = QFormLayout(g_dl)
        self.cookies_combo = QComboBox()
        for label, value in COOKIE_BROWSERS:
            self.cookies_combo.addItem(label, value)
        self.preset_combo = QComboBox()
        for label, value in [
            ("Original", "Original"), ("High", "High"),
            ("Balanced", "Balanced"), ("Compact", "Compact"), ("Small", "Small"),
        ]:
            self.preset_combo.addItem(label, value)
        self.noplaylist_cb = QCheckBox("Hanya unduh 1 video (noplaylist)")
        f_dl.addRow("Cookie browser", self.cookies_combo)
        f_dl.addRow("Preset kompresi", self.preset_combo)
        f_dl.addRow("", self.noplaylist_cb)
        form_root.addWidget(g_dl)

        # --- UI ---
        g_ui = QGroupBox("Perilaku UI")
        f_ui = QFormLayout(g_ui)
        self.confirm_exit_cb = QCheckBox("Konfirmasi saat keluar jika ada proses")
        self.autoscroll_cb = QCheckBox("Auto-scroll log")
        self.open_folder_cb = QCheckBox("Buka folder output setelah selesai")
        f_ui.addRow("", self.confirm_exit_cb)
        f_ui.addRow("", self.autoscroll_cb)
        f_ui.addRow("", self.open_folder_cb)
        form_root.addWidget(g_ui)

        form_root.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        # --- Actions ---
        actions = QHBoxLayout()
        self.save_btn = QPushButton("Simpan")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self._save)
        reset_btn = QPushButton("Reset ke Default")
        reset_btn.clicked.connect(self._reset)
        actions.addWidget(self.save_btn)
        actions.addWidget(reset_btn)
        actions.addStretch()
        outer.addLayout(actions)

    @staticmethod
    def _wrap(layout) -> QWidget:
        w = QWidget()
        w.setLayout(layout)
        return w

    def _load_into_ui(self, cfg: dict):
        p = cfg["paths"]
        self.download_dir.setText(p["download_dir"])
        self.compressed_dir.setText(p["compressed_dir"])
        self.cut_dir.setText(p["cut_dir"])
        self.ffmpeg_path.setText(p["ffmpeg_path"])
        self.ffprobe_path.setText(p["ffprobe_path"])
        self.node_path.setText(p["node_path"])

        d = cfg["downloader"]
        idx = self.cookies_combo.findData(d.get("cookies_browser"))
        self.cookies_combo.setCurrentIndex(max(0, idx))
        idx = self.preset_combo.findData(d.get("compression_preset", "Balanced"))
        self.preset_combo.setCurrentIndex(max(0, idx))
        self.noplaylist_cb.setChecked(bool(d.get("noplaylist", True)))

        u = cfg["ui"]
        self.confirm_exit_cb.setChecked(bool(u.get("confirm_on_exit", True)))
        self.autoscroll_cb.setChecked(bool(u.get("auto_scroll_log", True)))
        self.open_folder_cb.setChecked(bool(u.get("open_folder_on_finish", False)))
        self._check_ffmpeg(silent=True)

    def _collect(self) -> dict:
        return {
            "paths": {
                "download_dir": self.download_dir.text() or "downloads",
                "compressed_dir": self.compressed_dir.text() or "downloads/compressed",
                "cut_dir": self.cut_dir.text() or "downloads/cut",
                "ffmpeg_path": self.ffmpeg_path.text(),
                "ffprobe_path": self.ffprobe_path.text(),
                "node_path": self.node_path.text(),
            },
            "downloader": {
                "cookies_browser": self.cookies_combo.currentData(),
                "noplaylist": self.noplaylist_cb.isChecked(),
                "compression_preset": self.preset_combo.currentData(),
            },
            "ui": {
                "theme": "dark",
                "confirm_on_exit": self.confirm_exit_cb.isChecked(),
                "auto_scroll_log": self.autoscroll_cb.isChecked(),
                "open_folder_on_finish": self.open_folder_cb.isChecked(),
            },
        }

    def _save(self):
        try:
            save_config(self._collect())
            QMessageBox.information(self, "Tersimpan", f"Config disimpan di:\n{config_path()}")
        except Exception as exc:
            QMessageBox.critical(self, "Gagal", f"Tidak bisa menyimpan config:\n{exc}")

    def _reset(self):
        if QMessageBox.question(
            self, "Reset", "Kembalikan semua settings ke default?"
        ) != QMessageBox.Yes:
            return
        cfg = reset_config()
        self._load_into_ui(cfg)

    def _check_ffmpeg(self, silent: bool = False):
        try:
            ff = get_ffmpeg()
            fp = get_ffprobe()
            ver = ffmpeg_version()
            self.ffmpeg_status.setText(f"OK — {ver}\nffmpeg: {ff}\nffprobe: {fp}")
            if not silent:
                QMessageBox.information(self, "FFmpeg", "FFmpeg terdeteksi.")
        except Exception as exc:
            self.ffmpeg_status.setText(f"Gagal: {exc}")
            if not silent:
                QMessageBox.warning(self, "FFmpeg", str(exc))

    def _open_config_folder(self):
        folder = os.path.dirname(config_path())
        try:
            if os.name == "nt":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif os.uname().sysname == "Darwin":
                os.system(f'open "{folder}"')
            else:
                os.system(f'xdg-open "{folder}"')
        except Exception:
            pass