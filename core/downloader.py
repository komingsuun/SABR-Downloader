# Preset kompresi: (scale factor, CRF). Audio selalu di-copy.
COMPRESSION_PRESETS = {
    "Original": None,
    "High": (1.00, 23),
    "Balanced": (0.75, 26),
    "Compact": (0.50, 28),
    "Small": (0.35, 30),
}

# Browser yang didukung untuk ekstraksi cookie.
COOKIE_BROWSERS = [
    ("Tidak pakai cookie", None),
    ("Chrome", "chrome"),
    ("Firefox", "firefox"),
    ("Edge", "edge"),
    ("Brave", "brave"),
    ("Chromium", "chromium"),
    ("Opera", "opera"),
    ("Vivaldi", "vivaldi"),
]