# ClipCraft
<img width="2172" height="724" alt="Logo Aplikasi ClipCraft Berkilau" src="https://github.com/user-attachments/assets/6256fe87-6b50-49d2-9314-82b9e02e4eed" />


A Python-based video downloader powered by yt-dlp, supporting YouTube and various other media platforms


## "Download Any Video"

🚀 Getting Started

  **Clone repository**
  ```
  git clone https://github.com/USERNAME/ClipCraft.git
  
  cd ClipCraft
  ```

📦 Installation
 
  Linux :
  
  **Create virtual environment**

  ```
  python3 -m venv .venv
  ```

  **Activate virtual environment**
 

  ```
  source .venv/bin/activate
  ```

⚙️ Configuration

  **Add standard needed package**
  ```
    pip install -U "yt-dlp[default]"
    pip install git+https://github.com/tribixbite/yt-dlp-threads
    pip install pyside6
  ```

  **Or complete dependencies**
  
  ```pip install -r requirements.txt```

  **Add PO (Proof of Origin) Token Providers Server***
  
  Create & run at once if you don't have one (first install)

  ```
  docker run --name bgutil-provider -d --init \\n  -p 127.0.0.1:4416:4416 brainicism/bgutil-ytdlp-pot-provider
  ```
  Or run it if you have one
  ```
  docker start bgutil-provider 
  ```

  Set DNS to get a rid blocking, me using Cloudflare
  ```
  sudo resolvectl dns enp3s0 1.1.1.1 1.0.0.1
  sudo resolvectl flush-caches

  sudo resolvectl dns wlo1 1.1.1.1 1.0.0.1
  sudo resolvectl flush-caches
  ```
  Check whether the website is reachable  
  ```
  python -c "import requests; r=requests.get('https://situs_nakal_anda.com', timeout=15); print(r.status_code, r.url)"
  ```

## Threads Support (threads.com)

ClipCraft includes a custom yt-dlp extractor plugin
for downloading publicly accessible videos from Threads.

Supported features:
- Standard Threads video posts.
- Quoted video attachments.
- Progressive MP4 formats.
- DASH video streams.
- Video metadata and thumbnails.

### Plugin Structure

The custom extractor is maintained inside the repository:

```
yt_dlp_plugins/
└── extractor/
    └── threads.py
```

The plugin is loaded by yt-dlp through its plugin discovery mechanism.

### Limitations

- Only publicly accessible Threads posts are supported.
- Private or login-restricted posts may not be downloadable.
- Threads may change its internal API or embedded page structure,
  which can affect extractor compatibility.


📸 Screenshot

Video Downloader - downloader.py

<img width="1086" height="825" alt="Screenshot from 2026-11-09 18-32-21" src="https://github.com/user-attachments/assets/79fa09af-b73b-4070-9d19-5b5f652a3899" />

Video Downloader - main.py
 

<img width="1784" height="758" alt="Selection_1330" src="https://github.com/user-attachments/assets/72d079de-9bc3-44d4-83d8-ae887905be1a" />
 

**Just another vibe-coded project.** 😎


This application allows you to download videos from various popular websites. It is what it is — no fancy UI, no complicated setup. Just run it, paste your link, and start downloading.


📄 License

This project is licensed under the MIT License.

SABR Downloader uses third-party software, including yt-dlp, which is distributed under its own respective license.

Please refer to the respective projects for their licensing terms.
SABR Downloader uses third-party software,including yt-dlp, which is distributed under its own respective license.

See the respective projects for their licensing terms.



**Happy downloading!**


