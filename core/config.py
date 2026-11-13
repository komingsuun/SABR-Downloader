import copy
import json
import os

DEFAULTS = {
    "paths": {
        "download_dir": "downloads",
        "compressed_dir": "downloads/compressed",
        "cut_dir": "downloads/cut",
        "ffmpeg_path": "",
        "ffprobe_path": "",
        "node_path": "",
    },
    "downloader": {
        "cookies_browser": None,
        "noplaylist": True,
        "compression_preset": "Balanced",
    },
    "ui": {
        "theme": "dark",
        "confirm_on_exit": True,
        "auto_scroll_log": True,
        "open_folder_on_finish": False,
    },
}


def config_path() -> str:
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    folder = os.path.join(base, "ClipCraft")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "config.json")


def _merge(defaults: dict, loaded: dict) -> dict:
    for k, v in defaults.items():
        if isinstance(v, dict):
            loaded[k] = _merge(v, loaded.get(k, {}) or {})
        else:
            loaded.setdefault(k, v)
    return loaded


def load_config() -> dict:
    path = config_path()
    if not os.path.isfile(path):
        return copy.deepcopy(DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("config bukan objek JSON")
        return _merge(copy.deepcopy(DEFAULTS), data)
    except Exception:
        return copy.deepcopy(DEFAULTS)


def save_config(cfg: dict) -> None:
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def reset_config() -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    save_config(cfg)
    return cfg