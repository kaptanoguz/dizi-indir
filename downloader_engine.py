import requests
import re
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from hashlib import md5
import base64
import os
import yt_dlp
import threading
import time

class DiziboxEngine:
    def __init__(self, socketio=None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
        })
        self.socketio = socketio
        self.is_downloading = False
        self.active_downloads = {}

    def bytes_to_key(self, data, salt, output=48):
        data += salt
        key = md5(data).digest()
        final_key = key
        while len(final_key) < output:
            key = md5(key + data).digest()
            final_key += key
        return final_key[:output]

    def decrypt(self, encrypted_data, password):
        encrypted_data_bytes = base64.b64decode(encrypted_data)
        salt = encrypted_data_bytes[8:16]
        ciphertext = encrypted_data_bytes[16:]
        key_iv = self.bytes_to_key(password.encode(), salt, 48)
        key = key_iv[:32]
        iv = key_iv[32:]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(ciphertext), AES.block_size).decode()

    def sanitize_filename(self, name):
        cleaned_name = ' '.join(name.split())
        return re.sub(r'[\\/*?:"<>|]', "", cleaned_name).strip()

    def progress_hook(self, d, download_id):
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%','').strip()
            # If percentage is missing, try to calculate or show raw data
            if not p or p == '0':
                downloaded_bytes = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                if total_bytes:
                    p = f"{(downloaded_bytes / total_bytes) * 100:.1f}"
                else:
                    p = "0" # We'll handle this in JS by showing bytes

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

    def get_season_links(self, url):
        plugin = self.get_plugin(url)
        if plugin and hasattr(plugin, 'get_season_links'):
            return plugin.get_season_links(url)
        return [url]

    def get_episode_info(self, url):
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            dizi_adi_tag = soup.select_one('#main-wrapper > div.content-wrapper > div.title > h1 > span.tv-title-archive > span')
            sezon_bolum_tag = soup.select_one('#main-wrapper > div.content-wrapper > div.title > h1 > span.tv-title-episode')
            bolum_adi_tag = soup.select_one('#main-wrapper > div.content-wrapper > div.title > h1 > small')
            poster_tag = soup.select_one('.figure img') or soup.select_one('img.main-cover') or soup.select_one('img[itemprop="image"]')
            
            # Try meta tag if img tag fails
            poster_url = None
            if poster_tag and poster_tag.has_attr('src'):
                poster_url = poster_tag['src']
            else:
                meta_poster = soup.find('meta', {'itemprop': 'image'})
                if meta_poster and meta_poster.has_attr('content'):
                    poster_url = meta_poster['content']
            
            if not (dizi_adi_tag and sezon_bolum_tag):
                return None
            
            dizi_adi = dizi_adi_tag.text.strip()
            sezon_bolum_text = sezon_bolum_tag.text.strip()
            bolum_adi = re.sub(r'^\s*\((.*?)\)\s*$', r'\1', bolum_adi_tag.text) if bolum_adi_tag else ""
            
            sezon_no_match = re.search(r'(\d+)\.Sezon', sezon_bolum_text)
            bolum_no_match = re.search(r'(\d+)\.Bölüm', sezon_bolum_text)
            
            sezon_no = sezon_no_match.group(1) if sezon_no_match else "1"
            bolum_no = bolum_no_match.group(1) if bolum_no_match else "1"
            
            return {
                'show': dizi_adi,
                'season': sezon_no,
                'episode': bolum_no,
                'title': bolum_adi,
                'url': url,
                'poster': poster_url
            }
        except Exception:
            return None

    def download_poster(self, poster_url, folder_path):
        if not poster_url: return
        try:
            poster_path = os.path.join(folder_path, "poster.jpg")
            if os.path.exists(poster_path): return
            res = self.session.get(poster_url, stream=True)
            if res.status_code == 200:
                with open(poster_path, 'wb') as f:
                    for chunk in res.iter_content(1024): f.write(chunk)
        except: pass

    def get_season_links(self, url):
        try:
            response = self.session.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            ul = soup.select_one('#related-posts > ul')
            if ul:
                return [li.find('a', href=True)['href'] for li in ul.find_all('li') if li.find('a', href=True)]
            return [url]
        except Exception:
            return [url]

    def download_episode(self, info, download_id):
        try:
            episode_url = info['url']
            folder_name = self.sanitize_filename(f"{info['show']} {info['season']}.Sezon")
            filename = self.sanitize_filename(f"{info['episode']}. Bölüm{f' - {info['title']}' if info['title'] else ''}.mp4")
            
            base_dir = "downloads"
            show_folder = os.path.join(base_dir, folder_name)
            os.makedirs(show_folder, exist_ok=True)
            output_path = os.path.join(show_folder, filename)

            # Download poster first if it exists
            if info.get('poster'):
                self.download_poster(info['poster'], show_folder)

            # Extract final video URL
            response = self.session.get(episode_url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            king_php_url = soup.find('iframe', {'src': re.compile(r'king\.php')})['src']
            
            response = self.session.get(king_php_url, headers={'Referer': episode_url}, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            moly_embed_url = soup.find('iframe', {'src': re.compile(r'molystream\.org/embed/')})['src']
            
            response = self.session.get(moly_embed_url, headers={'Referer': king_php_url}, timeout=30)
            match = re.search(r'CryptoJS\.AES\.decrypt\("([^"]+)",\s*"([^"]+)"\)', response.text, re.DOTALL)
            if not match:
                raise ValueError("Dizibox: Kripto verisi bulunamadı.")
            
            decrypted_html = self.decrypt(match.group(1), match.group(2))
            final_video_url = BeautifulSoup(decrypted_html, 'html.parser').find('source')['src']

            ydl_opts = {
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'http_headers': {'Referer': moly_embed_url},
                'progress_hooks': [lambda d: self.progress_hook(d, download_id)],
                'retries': 10,
                'nopart': False,
                'concurrent_fragment_downloads': 10,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                'external_downloader_args': ['-loglevel', 'panic', '-hide_banner'],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([final_video_url])
            
            return True
        except Exception as e:
            if self.socketio:
                self.socketio.emit('download_progress', {'id': download_id, 'status': 'error', 'error': str(e)}, namespace='/')
            return False
