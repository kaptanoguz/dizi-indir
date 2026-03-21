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
            r = self.session.get(url, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Title
            title = "Bilinmiyor"
            # Try h1 first, then og:title
            title_tag = soup.find('h1')
            if title_tag:
                title = title_tag.text.strip()
            else:
                meta_title = soup.find('meta', property='og:title')
                if meta_title:
                    title = meta_title.get('content')
            
            # Poster
            poster_url = "N/A"
            meta_poster = soup.find('meta', property='og:image')
            if meta_poster:
                poster_url = meta_poster.get('content')
            
            # Check if it's a series or movie
            is_series = '/dizi/' in url or '/bolum/' in url
            
            if is_series:
                # For series, try to get specific episode info if link is an episode
                # But if it's the main series page, we just return the show info
                return {
                    'show': title,
                    'season': '1', # Default
                    'episode': '1', # Default
                    'title': title,
                    'poster': poster_url,
                    'url': url,
                    'source': 'HDFilmCehennemi'
                }
            else:
                # For movies
                return {
                    'show': 'Film',
                    'season': '-',
                    'episode': '-',
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
            r = self.session.get(url, timeout=30)
            
            # HDF AJAX loading logic:
            # They use data-post-id and admin-ajax.php
            # But usually FastPlay manifest can be constructed or found in DOM scripts
            
            # Alternative: construction manifest from data-id if found
            player_match = re.search(r'data-id="(.*?)"', r.text)
            if not player_match:
                # Try finding in scripts
                id_match = re.search(r'var\s+post_id\s*=\s*"?(\d+)"?', r.text)
                if id_match:
                    video_id = id_match.group(1)
                else:
                    print("HDF Player ID bulunamadı.")
                    return False
            else:
                video_id = player_match.group(1)
            
            # The subagent confirmed fastplay.mom/manifests/{ID}/master.txt pattern 
            # OR we might need to hit admin-ajax.php.
            # Let's try the direct manifest first as it's common for these players.
            video_url = f"https://fastplay.mom/manifests/{video_id}/master.txt"
            
            # Save logic
            show_name = info.get('show', 'Film')
            if show_name == 'Film':
                save_dir = os.path.join('downloads', 'Filmler')
                filename = f"{self.sanitize_filename(info['title'])}.mp4"
            else:
                save_dir = os.path.join('downloads', self.sanitize_filename(show_name))
                filename = f"{self.sanitize_filename(info['title'])}.mp4"
            
            if not os.path.exists(save_dir): os.makedirs(save_dir)
            output_path = os.path.join(save_dir, filename)
            
            # Poster
            if info.get('poster'):
                self.download_poster(info['poster'], os.path.join(save_dir, "poster.jpg"))
            
            ydl_opts = {
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'http_headers': {
                    'Referer': url,
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
