# SABR-Downloader
<img width="100" height="100" alt="Sejak 1970 (2)" src="https://github.com/user-attachments/assets/3606338a-f4ef-4e57-8995-a12c6cf83668" />

A Python-based video downloader powered by yt-dlp, supporting YouTube and various other media platforms


## "Download Any Video"

🚀 Getting Started

  **Clone repository**
  git clone https://github.com/USERNAME/SABR-Downloader.git
  cd SABR-Downloader

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

  **Add needed package**
  ```
    pip install -U "yt-dlp[default]"
    pip install secretstorage
  ```

  **Or**
  
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


📸 Screenshot

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


