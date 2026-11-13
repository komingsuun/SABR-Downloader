import os
import re
import subprocess
import uuid

import yt_dlp
from PySide6.QtCore import QThread, Signal

from core.downloader import COMPRESSION_PRESETS
from core.ffmpeg import get_ffmpeg, probe_media
from core.ffmpeg import get_node

# ============================================================
# Helper nama file aman & pendek
# ============================================================
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MULTI_SPACE = re.compile(r'\s+')

# Batas aman: 255 byte umumnya cukup, tapi kita sisakan ruang
# untuk suffix preset & ekstensi. 120 char untuk stem aman.
_MAX_STEM_LEN = 120

# ============================================================
# Download + (opsional) kompres setelah unduh
# ============================================================
class DownloadWorker(QThread):
    progress_changed = Signal(float, str, str, str)  # percent, speed, eta, status
    log_message = Signal(str)
    finished_signal = Signal(bool, dict)

    def __init__(
        self,
        url: str,
        output_dir: str,
        noplaylist: bool,
        compression_preset: str = "Balanced",
        cookies_from_browser: str | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.url = url
        self.output_dir = output_dir
        self.noplaylist = noplaylist
        self.compression_preset = compression_preset
        self.cookies_from_browser = cookies_from_browser
        self._cancel_requested = False
        self._ffmpeg_process = None

    def progress_hook(self, d):
        if self._cancel_requested:
            raise yt_dlp.utils.DownloadCancelled("Dibatalkan oleh pengguna")

        if d["status"] == "downloading":
            percent_str = d.get("_percent_str", "0%").strip()
            speed = d.get("_speed_str", "N/A").strip()
            eta = d.get("_eta_str", "N/A").strip()
            try:
                percent_val = float(percent_str.replace("%", "").strip())
            except ValueError:
                percent_val = 0.0
            self.progress_changed.emit(percent_val, speed, eta, "Mengunduh...")
        elif d["status"] == "finished":
            self.progress_changed.emit(100.0, "-", "-", "Memproses file...")
            self.log_message.emit("Unduhan selesai, memproses file...")

    def _find_downloaded_file(self, info, ydl):
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
        media_id = info.get("id")
        if media_id:
            suffix = f"[{media_id}]"
            for name in os.listdir(self.output_dir):
                path = os.path.join(self.output_dir, name)
                if suffix in name and os.path.isfile(path) and not name.endswith((".part", ".ytdl")):
                    return os.path.abspath(path)
        return None

    def _find_downloaded_files(self, info, ydl):
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

    def _compress_video(self, input_path):
        preset = self.compression_preset
        settings = COMPRESSION_PRESETS.get(preset)
        if settings is None:
            self.log_message.emit("Preset Original: file dibiarkan tanpa kompresi.")
            return input_path

        ffmpeg = get_ffmpeg()
        scale, crf = settings
        duration, audio_codec, has_video = probe_media(input_path)
        if not has_video:
            self.log_message.emit("File tidak memiliki stream video; kompresi dilewati.")
            return input_path

        mp4_audio_codecs = {"aac", "mp3", "ac3", "eac3", "alac"}
        output_ext = ".mp4" if audio_codec is None or audio_codec in mp4_audio_codecs else ".mkv"
        base = os.path.splitext(input_path)[0]
        output_path = f"{base} [{preset}]{output_ext}"
        temp_path = f"{base} [{preset}].processing{output_ext}"

        if os.path.abspath(output_path) == os.path.abspath(input_path):
            raise RuntimeError("Nama file output sama dengan file sumber; kompresi dibatalkan.")

        if os.path.exists(output_path):
            stem, ext = os.path.splitext(output_path)
            counter = 2
            while os.path.exists(f"{stem} ({counter}){ext}"):
                counter += 1
            output_path = f"{stem} ({counter}){ext}"
            temp_path = f"{os.path.splitext(output_path)[0]}.processing{ext}"

        vf = f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-i", input_path,
            "-map", "0:v:0", "-map", "0:a?",
            "-map_metadata", "0", "-map_chapters", "0",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
            "-c:a", "copy",
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
                text=True, bufsize=1,
            )
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
                    f"Hasil kompresi: {output_path} "
                    f"({compressed_size / 1024 / 1024:.2f} MB; "
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
            "outtmpl": os.path.join(self.output_dir, "%(title).200s [%(id)s].%(ext)s"),
            "trim_file_name": 100,
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

        node_path = get_node()
        if node_path:
            ydl_opts["js_runtimes"] = {"node": {"path": node_path}}

        if self.cookies_from_browser:
            ydl_opts["cookiesfrombrowser"] = (
                self.cookies_from_browser, None, None, None,
            )
            self.log_message.emit(f"Menggunakan cookie dari browser: {self.cookies_from_browser}")
        else:
            self.log_message.emit("Tidak menggunakan cookie browser.")

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
# Kompres file lokal (halaman "Video Compression")
# ============================================================

def _sanitize_stem(name: str, max_len: int = _MAX_STEM_LEN) -> str:
    """
    Buang karakter ilegal, rapikan spasi, dan potong panjangnya
    (dihitung per-byte UTF-8 agar aman di filesystem apapun).
    """
    name = _ILLEGAL_CHARS.sub("", name)
    name = _MULTI_SPACE.sub(" ", name).strip().strip(".")

    # Potong per-byte UTF-8 agar tidak melebihi batas filesystem
    encoded = name.encode("utf-8")
    if len(encoded) > max_len:
        # decode dengan errors='ignore' supaya tidak memotong multibyte
        name = encoded[:max_len].decode("utf-8", errors="ignore").rstrip()
    return name or "video"


class CompressWorker(QThread):
    progress_changed = Signal(float, str, str, str)
    log_message = Signal(str)
    finished_signal = Signal(bool, str)  # success, output_path/err

    def __init__(self, input_path: str, output_dir: str,
                 compression_preset: str = "Balanced", parent=None):
        super().__init__(parent)
        self.input_path = input_path
        self.output_dir = output_dir
        self.compression_preset = compression_preset
        self._cancel_requested = False
        self._ffmpeg_process = None

    def _probe(self):
        return probe_media(self.input_path)

    def _build_output_paths(self, output_ext: str):
        """
        Bangun output_path final + temp_path pendek.
        Temp path memakai UUID agar dijamin pendek & unik.
        """
        raw_stem = os.path.splitext(os.path.basename(self.input_path))[0]
        # Sisa ruang untuk suffix " [Preset] (2)" + ekstensi + margin
        reserve = len(f" [{self.compression_preset}] (99)") + len(output_ext) + 8
        max_stem = max(20, _MAX_STEM_LEN - reserve)
        safe_stem = _sanitize_stem(raw_stem, max_stem)

        output_path = os.path.join(
            self.output_dir,
            f"{safe_stem} [{self.compression_preset}]{output_ext}",
        )
        # Hindari tabrakan
        if os.path.exists(output_path):
            counter = 2
            stem, ext = os.path.splitext(output_path)
            while os.path.exists(f"{stem} ({counter}){ext}"):
                counter += 1
            output_path = f"{stem} ({counter}){ext}"

        # Temp file pakai nama pendek (UUID) untuk hindari "File name too long"
        temp_path = os.path.join(
            self.output_dir, f"cc_tmp_{uuid.uuid4().hex}{output_ext}"
        )
        return output_path, temp_path

    def run(self):
        os.makedirs(self.output_dir, exist_ok=True)
        settings = COMPRESSION_PRESETS.get(self.compression_preset)
        if settings is None:
            self.finished_signal.emit(False, "Preset 'Original' tidak melakukan kompresi.")
            return

        temp_path = None
        try:
            ffmpeg = get_ffmpeg()
            scale, crf = settings
            duration, audio_codec, has_video = self._probe()
            if not has_video:
                self.finished_signal.emit(False, "File tidak memiliki stream video.")
                return

            mp4_audio_codecs = {"aac", "mp3", "ac3", "eac3", "alac"}
            output_ext = ".mp4" if audio_codec is None or audio_codec in mp4_audio_codecs else ".mkv"

            output_path, temp_path = self._build_output_paths(output_ext)

            self.log_message.emit(f"Output: {os.path.basename(output_path)}")

            vf = f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"
            command = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-i", self.input_path,
                "-map", "0:v:0", "-map", "0:a?",
                "-map_metadata", "0", "-map_chapters", "0",
                "-vf", vf,
                "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
                "-c:a", "copy",
            ]
            if output_ext == ".mp4":
                command += ["-movflags", "+faststart"]
            command += ["-progress", "pipe:1", "-nostats", temp_path]

            self.log_message.emit(
                f"Kompresi {self.compression_preset}: skala {int(scale*100)}%, CRF {crf}; "
                f"audio {audio_codec or 'tidak ada'} (copy)."
            )
            self.progress_changed.emit(0.0, "-", "-", "Mengompres video...")

            try:
                self._ffmpeg_process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, bufsize=1,
                )
                for line in self._ffmpeg_process.stdout:
                    if self._cancel_requested:
                        self._ffmpeg_process.terminate()
                        raise RuntimeError("Kompresi dibatalkan.")
                    line = line.strip()
                    if line.startswith("out_time_ms=") and duration > 0:
                        try:
                            elapsed = int(line.split("=", 1)[1]) / 1_000_000
                            pct = min(99.0, max(0.0, elapsed / duration * 100))
                            self.progress_changed.emit(pct, "-", "-", "Mengompres video...")
                        except ValueError:
                            pass

                rc = self._ffmpeg_process.wait()
                stderr = self._ffmpeg_process.stderr.read() if self._ffmpeg_process.stderr else ""
                if rc != 0:
                    raise RuntimeError(f"FFmpeg gagal: {stderr[-1200:]}")
                if not os.path.isfile(temp_path) or os.path.getsize(temp_path) == 0:
                    raise RuntimeError("FFmpeg tidak menghasilkan file output.")

                os.replace(temp_path, output_path)
                temp_path = None  # sudah dipindah, jangan dihapus di finally
                self.progress_changed.emit(100.0, "-", "-", "Kompresi selesai")
                orig = os.path.getsize(self.input_path)
                new = os.path.getsize(output_path)
                if orig:
                    reduction = (1 - new / orig) * 100
                    self.log_message.emit(
                        f"Hasil: {output_path} ({new/1024/1024:.2f} MB; {reduction:+.1f}%)"
                    )
                self.finished_signal.emit(True, output_path)
            finally:
                self._ffmpeg_process = None
        except Exception as exc:
            self.log_message.emit(f"Error: {exc}")
            self.finished_signal.emit(False, str(exc))
        finally:
            # Bersihkan temp file kalau masih ada (gagal / dibatalkan)
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def cancel(self):
        self._cancel_requested = True
        if self._ffmpeg_process and self._ffmpeg_process.poll() is None:
            self._ffmpeg_process.terminate()

# ============================================================
# Cutter: potong klip dari file lokal
# ============================================================
class CutterWorker(QThread):
    progress_changed = Signal(float, str, str, str)
    log_message = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(
        self,
        input_path: str,
        output_dir: str,
        start_sec: float,
        end_sec: float,
        reencode: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.input_path = input_path
        self.output_dir = output_dir
        self.start_sec = max(0.0, float(start_sec))
        self.end_sec = float(end_sec)
        self.reencode = reencode
        self._cancel_requested = False
        self._ffmpeg_process = None

    def _build_output_paths(self, output_ext: str):
        from core.workers import _sanitize_stem  # reuse helper di file ini
        raw_stem = os.path.splitext(os.path.basename(self.input_path))[0]
        reserve = len(" [cut 9999-9999] (99)") + len(output_ext) + 8
        max_stem = max(20, _MAX_STEM_LEN - reserve) if "_MAX_STEM_LEN" in globals() else 90
        safe_stem = _sanitize_stem(raw_stem, max_stem)

        s = int(self.start_sec)
        e = int(self.end_sec)
        tag = f" [cut {s}-{e}]"
        output_path = os.path.join(self.output_dir, f"{safe_stem}{tag}{output_ext}")
        if os.path.exists(output_path):
            counter = 2
            stem, ext = os.path.splitext(output_path)
            while os.path.exists(f"{stem} ({counter}){ext}"):
                counter += 1
            output_path = f"{stem} ({counter}){ext}"

        temp_path = os.path.join(self.output_dir, f"cc_tmp_{uuid.uuid4().hex}{output_ext}")
        return output_path, temp_path

    def run(self):
        os.makedirs(self.output_dir, exist_ok=True)
        temp_path = None
        try:
            if self.end_sec <= self.start_sec:
                raise RuntimeError("Waktu akhir harus lebih besar dari waktu mulai.")

            ffmpeg = get_ffmpeg()
            duration, _, has_video = probe_media(self.input_path)
            if not has_video:
                raise RuntimeError("File tidak memiliki stream video.")
            if self.start_sec >= duration:
                raise RuntimeError(
                    f"Waktu mulai ({self.start_sec:.1f}s) melebihi durasi file ({duration:.1f}s)."
                )
            end = min(self.end_sec, duration)
            clip_len = max(0.1, end - self.start_sec)

            output_ext = ".mp4"
            output_path, temp_path = self._build_output_paths(output_ext)

            if self.reencode:
                # akurat frame-by-frame
                command = [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-i", self.input_path,
                    "-ss", f"{self.start_sec:.3f}",
                    "-t", f"{clip_len:.3f}",
                    "-map", "0:v:0", "-map", "0:a?",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart",
                    "-progress", "pipe:1", "-nostats", temp_path,
                ]
                self.log_message.emit(f"Cut (re-encode) {self.start_sec:.2f}s → {end:.2f}s")
            else:
                # fast copy (keyframe-accurate)
                command = [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", f"{self.start_sec:.3f}",
                    "-i", self.input_path,
                    "-t", f"{clip_len:.3f}",
                    "-map", "0", "-c", "copy",
                    "-avoid_negative_ts", "make_zero",
                    "-progress", "pipe:1", "-nostats", temp_path,
                ]
                self.log_message.emit(f"Cut (copy) {self.start_sec:.2f}s → {end:.2f}s")

            self.progress_changed.emit(0.0, "-", "-", "Memotong video...")

            try:
                self._ffmpeg_process = subprocess.Popen(
                    command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, bufsize=1,
                )
                for line in self._ffmpeg_process.stdout:
                    if self._cancel_requested:
                        self._ffmpeg_process.terminate()
                        raise RuntimeError("Pemotongan dibatalkan.")
                    line = line.strip()
                    if line.startswith("out_time_ms=") and clip_len > 0:
                        try:
                            elapsed = int(line.split("=", 1)[1]) / 1_000_000
                            pct = min(99.0, max(0.0, elapsed / clip_len * 100))
                            self.progress_changed.emit(pct, "-", "-", "Memotong video...")
                        except ValueError:
                            pass

                rc = self._ffmpeg_process.wait()
                stderr = self._ffmpeg_process.stderr.read() if self._ffmpeg_process.stderr else ""
                if rc != 0:
                    raise RuntimeError(f"FFmpeg gagal: {stderr[-1200:]}")
                if not os.path.isfile(temp_path) or os.path.getsize(temp_path) == 0:
                    raise RuntimeError("FFmpeg tidak menghasilkan file output.")

                os.replace(temp_path, output_path)
                temp_path = None
                self.progress_changed.emit(100.0, "-", "-", "Pemotongan selesai")
                self.log_message.emit(f"Hasil: {output_path}")
                self.finished_signal.emit(True, output_path)
            finally:
                self._ffmpeg_process = None
        except Exception as exc:
            self.log_message.emit(f"Error: {exc}")
            self.finished_signal.emit(False, str(exc))
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def cancel(self):
        self._cancel_requested = True
        if self._ffmpeg_process and self._ffmpeg_process.poll() is None:
            self._ffmpeg_process.terminate()