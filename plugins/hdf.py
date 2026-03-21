import os
import re
import requests
import yt_dlp
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler

class HDFPlugin(BaseCrawler):
    def __init__(self, socketio=None):
        super().__init__(socketio)

    def get_info(self, url):
        try:
            r = self.session.get(url)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Title
            title = "Bilinmiyor"
            title_tag = soup.find('h1') or soup.find('meta', property='og:title')
            if title_tag:
                title = title_tag.text.strip() if hasattr(title_tag, 'text') else title_tag.get('content', 'Bilinmiyor')
            
            # Poster
            poster_url = "N/A"
            meta_poster = soup.find('meta', property='og:image')
            if meta_poster:
                poster_url = meta_poster.get('content')
            
            return {
                'title': title,
                'poster': poster_url,
                'url': url,
                'source': 'HDFilmCehennemi'
            }
        except Exception as e:
            print(f"HDF info hatası: {e}")
            return None

    def download(self, info, download_id):
        url = info['url']
        try:
            r = self.session.get(url)
            
            # Find iframe or player ID
            # HDF uses multiple players, trying to find FastPlay ID
            player_match = re.search(r'data-id="(.*?)"', r.text)
            if not player_match:
                print("HDF Player ID bulunamadı.")
                return False
            
            # The subagent found manifest link format: https://fastplay.mom/manifests/{ID}/master.txt
            video_id = player_match.group(1)
            video_url = f"https://fastplay.mom/manifests/{video_id}/master.txt"
            
            # Check if it's a series or movie for folder structure
            is_series = '/dizi/' in url or '/bolum/' in url
            folder_name = info['title'].split(' - ')[0] if is_series else info['title']
            
            save_dir = os.path.join('downloads', self.sanitize_filename(folder_name))
            if not os.path.exists(save_dir): os.makedirs(save_dir)
            
            # Poster
            poster_path = os.path.join(save_dir, "poster.jpg")
            if not os.path.exists(poster_path):
                self.download_poster(info['poster'], poster_path)
            
            # Video
            filename = f"{self.sanitize_filename(info['title'])}.mp4"
            output_path = os.path.join(save_dir, filename)
            
            ydl_opts = {
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'http_headers': {
                    'Referer': 'https://hdfilmcehennemi.now/',
                    'Origin': 'https://fastplay.mom'
                },
                'progress_hooks': [lambda d: self.progress_hook(d, download_id)],
                'retries': 10,
                'concurrent_fragment_downloads': 10,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'external_downloader_args': ['-loglevel', 'panic', '-hide_banner'],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            return True
        except Exception as e:
            if self.socketio:
                self.socketio.emit('download_progress', {'id': download_id, 'status': 'error', 'error': str(e)}, namespace='/')
            return False
