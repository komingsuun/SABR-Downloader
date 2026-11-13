import json
import os
import shutil
import subprocess
import json

from core.config import load_config


def _resolve_tool(key: str, name: str) -> str:
    cfg = load_config()
    custom = (cfg.get("paths", {}) or {}).get(key, "") or ""
    if custom and os.path.isfile(custom):
        return custom
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} tidak ditemukan. Set path di Settings atau pasang {name}.")
    return path


def get_ffmpeg() -> str:
    return _resolve_tool("ffmpeg_path", "ffmpeg")


def get_ffprobe() -> str:
    return _resolve_tool("ffprobe_path", "ffprobe")


def get_node() -> str | None:
    cfg = load_config()
    custom = (cfg.get("paths", {}) or {}).get("node_path", "") or ""
    if custom and os.path.isfile(custom):
        return custom
    return shutil.which("node")


def probe_media(path: str):
    result = subprocess.run(
        [
            get_ffprobe(), "-v", "error",
            "-show_entries", "format=duration:stream=codec_type,codec_name",
            "-of", "json", path,
        ],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout or "{}")
    duration = float((data.get("format") or {}).get("duration") or 0)
    streams = data.get("streams") or []
    audio_codec = next(
        (s.get("codec_name") for s in streams if s.get("codec_type") == "audio"),
        None,
    )
    has_video = any(s.get("codec_type") == "video" for s in streams)
    return duration, audio_codec, has_video


def is_ffmpeg_available() -> bool:
    try:
        get_ffmpeg()
        return True
    except Exception:
        return False

def ffmpeg_version() -> str:
    try:
        result = subprocess.run(
            [get_ffmpeg(), "-version"], capture_output=True, text=True
        )
        return result.stdout.splitlines()[0] if result.stdout else "unknown"
    except Exception as exc:
        return f"tidak tersedia ({exc})"

def probe_codecs(path: str):
    """Return (video_codec, audio_codec)."""
    result = subprocess.run(
        [
            get_ffprobe(), "-v", "error",
            "-show_entries", "stream=codec_type,codec_name",
            "-of", "json", path,
        ],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(result.stdout or "{}")
    v = a = None
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and v is None:
            v = s.get("codec_name")
        elif s.get("codec_type") == "audio" and a is None:
            a = s.get("codec_name")
    return v, a