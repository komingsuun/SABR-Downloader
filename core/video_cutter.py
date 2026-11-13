import os

from core.config import load_config


def ensure_cut_dir() -> str:
    cfg = load_config()
    path = cfg["paths"]["cut_dir"] or "downloads/cut"
    os.makedirs(path, exist_ok=True)
    return path