#
# 100% Vibe Coding
# Program Download Sembarang Video
# Implementasi yt-dlp untuk mendukung pengunduhan video YouTube dengan Adaptive Bitrate Streaming (SABR)

# Siapkan env untuk project ini beserta package yang dibutuhkan
# - pip install -U "yt-dlp[default]"
# - pip install secretstorage
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
import yt_dlp


def progress_hook(d):
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "0%").strip()
        speed = d.get("_speed_str", "N/A").strip()
        eta = d.get("_eta_str", "N/A").strip()

        print(
            f"\rMengunduh: {percent} | {speed} | ETA: {eta}   ",
            end="",
            flush=True,
        )

    elif d["status"] == "finished":
        print("\nUnduhan selesai, memproses file...")


def download_video(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        # Kualitas terbaik yang tersedia
        "format": "bv*+ba/b",

        # Nama file dan folder keluaran
        "outtmpl": os.path.join(
            output_dir,
            "%(title).200s [%(id)s].%(ext)s",
        ),

        # Runtime JavaScript untuk situs yang memerlukannya
        "js_runtimes": {
            "node": {"path": "/home/pyy/.nvm/versions/node/v22.23.4/bin/node"}
        },

        # Komponen EJS, terutama untuk ekstraksi YouTube
        "remote_components": ["ejs:github"],

        # Tidak ada extractor_args khusus YouTube
        # yt-dlp memilih extractor berdasarkan URL

        # Jeda permintaan
        "sleep_interval_requests": 1,
        "sleep_interval": 2,
        "max_sleep_interval": 5,

        # Thumbnail dan metadata
        "writethumbnail": True,
        "embedthumbnail": True,
        "addmetadata": True,

        # Progres dan kontrol unduhan
        "progress_hooks": [progress_hook],
        "noplaylist": True,
        "ignoreerrors": False,
        "continuedl": True,
        "overwrites": False,
        "verbose": False,
    }

    try:
        print(f"\nMemproses URL:\n{url}\n")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if not info:
            print("Gagal mendapatkan informasi media.")
            return False

        print("\nUnduhan berhasil!")
        print(f"Judul  : {info.get('title', '-')}")
        print(f"Situs  : {info.get('extractor_key', '-')}")
        print(f"Folder : {os.path.abspath(output_dir)}")

        return True

    except yt_dlp.utils.DownloadError as exc:
        print(f"\nUnduhan gagal:\n{exc}")
        return False

    except Exception as exc:
        print(f"\nError {type(exc).__name__}: {exc}")
        return False


if __name__ == "__main__":
    url = input("Masukkan URL video atau media: ").strip()

    if url:
        download_video(url)
    else:
        print("URL tidak boleh kosong.")
