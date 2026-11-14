import hashlib
import os
import subprocess

from core.ffmpeg import get_ffmpeg


def _cache_dir_for(input_path: str) -> str:
    """Folder cache unik per file (path + mtime + size)."""
    try:
        stat = os.stat(input_path)
        key = f"{os.path.abspath(input_path)}|{stat.st_mtime}|{stat.st_size}"
    except OSError:
        key = os.path.abspath(input_path)
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:16]

    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
    folder = os.path.join(base, "ClipCraft", "thumbs", digest)
    os.makedirs(folder, exist_ok=True)
    return folder


def plan_thumbnail_times(duration: float, count: int | None = None):
    """Kembalikan list timestamp (detik) untuk tiap thumbnail."""
    if duration <= 0:
        return []
    if count is None:
        count = int(duration / 5)
        count = max(8, min(40, count))
    # titik tengah tiap segmen, agar tidak mulai dari 0.0
    return [((i + 0.5) * duration / count) for i in range(count)]


def thumbnail_path(cache_dir: str, index: int) -> str:
    return os.path.join(cache_dir, f"{index:03d}.jpg")


def extract_one(input_path: str, t_sec: float, out_path: str, width: int = 160) -> bool:
    """Ekstrak 1 frame di t_sec ke out_path. Return True kalau sukses."""
    if os.path.isfile(out_path) and os.path.getsize(out_path) > 0:
        return True
    ffmpeg = get_ffmpeg()
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{max(0.0, t_sec):.3f}",
        "-i", input_path,
        "-frames:v", "1",
        "-vf", f"scale={width}:-2",
        "-q:v", "4",
        out_path,
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0 and os.path.isfile(out_path) and os.path.getsize(out_path) > 0
    except Exception:
        return False


def cache_dir_for(input_path: str) -> str:
    return _cache_dir_for(input_path)