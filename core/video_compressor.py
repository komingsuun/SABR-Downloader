import os

from core.config import load_config


def ensure_compressed_dir() -> str:
    cfg = load_config()
    path = cfg["paths"]["compressed_dir"] or "downloads/compressed"
    os.makedirs(path, exist_ok=True)
    return path