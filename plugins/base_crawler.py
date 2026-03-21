import os
import re
import requests
import yt_dlp
from bs4 import BeautifulSoup

class BaseCrawler:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def sanitize_filename(self, filename):
        return re.sub(r'[\\/*?:"<>|]', "", filename)

    def progress_hook(self, d, download_id):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%', '').strip()
            # Handle cases where percent string is missing or weird
            if not p or p == 'N/A':
                if d.get('total_bytes'):
                    p = str(round(d['downloaded_bytes'] / d['total_bytes'] * 100, 1))
                elif d.get('total_bytes_estimate'):
                    p = str(round(d['downloaded_bytes'] / d['total_bytes_estimate'] * 100, 1))
                else:
                    p = "0"

            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            speed = ansi_escape.sub('', d.get('_speed_str', 'N/A'))
            eta = ansi_escape.sub('', d.get('_eta_str', 'N/A'))
            downloaded = ansi_escape.sub('', d.get('_downloaded_bytes_str', 'N/A'))
            total = ansi_escape.sub('', d.get('_total_bytes_str', 'N/A'))
            
            progress_data = {
                'id': download_id,
                'progress': p,
                'speed': speed,
                'eta': eta,
                'downloaded': downloaded,
                'total': total,
                'status': 'downloading'
            }
            if self.socketio:
                self.socketio.emit('download_progress', progress_data, namespace='/')
        elif d['status'] == 'finished':
            if self.socketio:
                self.socketio.emit('download_progress', {'id': download_id, 'status': 'finished', 'progress': '100'}, namespace='/')

    def download_poster(self, poster_url, save_path):
        try:
            if not poster_url or poster_url == 'N/A': return
            r = self.session.get(poster_url, stream=True)
            if r.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
        except Exception as e:
            print(f"Poster hatası: {e}")

    def get_info(self, url):
        """Her plugin kendi info çekme mantığını burada kuracak"""
        raise NotImplementedError

    def download(self, info, download_id):
        """Her plugin kendi indirme mantığını burada kuracak (Genellikle yt-dlp)"""
        raise NotImplementedError
