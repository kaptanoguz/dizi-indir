import re
import os
import json
import base64
import requests
import yt_dlp
from bs4 import BeautifulSoup
from hashlib import md5
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from plugins.base_crawler import BaseCrawler

class DiziboxPlugin(BaseCrawler):
    def __init__(self, socketio=None):
        super().__init__(socketio)

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

    def get_season_links(self, url):
        try:
            r = self.session.get(url, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            ul = soup.select_one('#related-posts > ul')
            if ul:
                return [li.find('a', href=True)['href'] for li in ul.find_all('li') if li.find('a', href=True)]
            return [url]
        except Exception:
            return [url]

    def get_info(self, url):
        try:
            r = self.session.get(url, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            dizi_adi_tag = soup.select_one('#main-wrapper > div.content-wrapper > div.title > h1 > span.tv-title-archive > span')
            sezon_bolum_tag = soup.select_one('#main-wrapper > div.content-wrapper > div.title > h1 > span.tv-title-episode')
            bolum_adi_tag = soup.select_one('#main-wrapper > div.content-wrapper > div.title > h1 > small')
            poster_tag = soup.select_one('.figure img') or soup.select_one('img.main-cover') or soup.select_one('img[itemprop="image"]')
            
            # Poster logic
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
                'poster': poster_url,
                'source': 'Dizibox'
            }
        except Exception:
            return None

    def download(self, info, download_id):
        try:
            episode_url = info['url']
            folder_name = self.sanitize_filename(f"{info['show']} {info['season']}.Sezon")
            filename = self.sanitize_filename(f"{info['episode']}. Bölüm{f' - {info['title']}' if info.get('title') else ''}.mp4")
            
            save_dir = os.path.join('downloads', folder_name)
            if not os.path.exists(save_dir): os.makedirs(save_dir)
            output_path = os.path.join(save_dir, filename)

            # Poster
            if info.get('poster'):
                self.download_poster(info['poster'], os.path.join(save_dir, "poster.jpg"))

            # Extraction
            r = self.session.get(episode_url, timeout=30)
            soup = BeautifulSoup(r.text, 'html.parser')
            king_iframe = soup.find('iframe', {'src': re.compile(r'king\.php')})
            if not king_iframe: return False
            king_url = king_iframe['src']
            
            r_king = self.session.get(king_url, headers={'Referer': episode_url}, timeout=30)
            soup_king = BeautifulSoup(r_king.text, 'html.parser')
            moly_iframe = soup_king.find('iframe', {'src': re.compile(r'molystream\.org/embed/')})
            if not moly_iframe: return False
            moly_url = moly_iframe['src']
            
            r_moly = self.session.get(moly_url, headers={'Referer': king_url}, timeout=30)
            match = re.search(r'CryptoJS\.AES\.decrypt\("([^"]+)",\s*"([^"]+)"\)', r_moly.text, re.DOTALL)
            if not match: return False
            
            decrypted_html = self.decrypt(match.group(1), match.group(2))
            video_url = BeautifulSoup(decrypted_html, 'html.parser').find('source')['src']

            ydl_opts = {
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'http_headers': {'Referer': moly_url},
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
