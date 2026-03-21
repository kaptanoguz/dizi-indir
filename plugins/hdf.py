import os
import re
import requests
import yt_dlp
from bs4 import BeautifulSoup
import shutil
from plugins.base_crawler import BaseCrawler

class HDFPlugin(BaseCrawler):
    def __init__(self, socketio=None):
        super().__init__(socketio)

    def _log_and_emit(self, download_id, msg, is_error=False):
        status_type = 'error' if is_error else 'info'
        print(f"[HDF PLUGIN] {msg}")
        if self.socketio:
            self.socketio.emit('download_progress', {
                'id': download_id, 'status': status_type, 'message': msg
            }, namespace='/')

    def check_ffmpeg(self, download_id):
        if not shutil.which('ffmpeg'):
            self._log_and_emit(download_id, "UYARI: ffmpeg sisteminizde yüklü değil! M3U8 (HLS) videoları indirilemeyebilir.", is_error=False)

    def extract_fallback(self, soup, download_id):
        # 1. Search IFRAMEs
        keywords = ['embed', 'player', 'vidmoly', 'dood', 'stream', 'aparat']
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src')
            if src:
                if any(k in src.lower() for k in keywords):
                    if src.startswith('//'): src = 'https:' + src
                    elif src.startswith('/'): src = 'https://www.hdfilmcehennemi.now' + src
                    self._log_and_emit(download_id, f"Uyumlu Iframe kaynağı bulundu: {src}")
                    return src
        
        # 2. Search Script Tags for .m3u8
        for script in soup.find_all('script'):
            if script.string:
                match = re.search(r'https?://[^\'"\s]+\.m3u8[^\'"]*', script.string)
                if match:
                    src = match.group(0)
                    self._log_and_emit(download_id, f"Script içerisinde HLS/m3u8 akışı bulundu: {src}")
                    return src
                    
        # 3. Search Data Attributes
        for tag in soup.find_all(['div', 'video', 'span', 'a']):
            src = tag.get('data-video-src') or tag.get('data-source') or tag.get('data-src')
            if src and 'http' in src:
                self._log_and_emit(download_id, f"Data attribute kaynağı bulundu: {src}")
                return src
                
        return None

    def get_info(self, url):
        try:
            r = self.session.get(url, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Title - Prioritize og:title as it's usually cleaner
            title = "Bilinmiyor"
            meta_title = soup.find('meta', property='og:title')
            if meta_title:
                title = meta_title.get('content')
            else:
                title_tag = soup.find('h1')
                if title_tag:
                    title = title_tag.text.strip()
            
            # Clean title from common suffixes
            title = title.split('|')[0].replace('izle', '').strip()
            
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
        # Use a browser-like User-Agent to avoid simplified HTML
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        
        try:
            r = self.session.get(url, timeout=30)
            soup = BeautifulSoup(r.text, 'html.parser')

            self.check_ffmpeg(download_id)
            self._log_and_emit(download_id, "HDFilmCehennemi video kaynağı çözümleniyor...")

            # 1. Scrape the nonce using a very flexible regex
            # We look for something like nonce: 'e1b94ba64b' or "nonce":"e1b94ba64b"
            nonce = None
            
            # Pattern 1: Specifically near videoAjax (broad search)
            # Find the videoAjax block first
            video_ajax_block = re.search(r'videoAjax\s*=\s*\{([^}]+)\}', r.text, re.DOTALL)
            if video_ajax_block:
                block_content = video_ajax_block.group(1)
                m = re.search(r'nonce\s*:\s*[\'"]([a-f0-9]{10,12})[\'"]', block_content)
                if m:
                    nonce = m.group(1)
            
            # Pattern 2: Global search for the first 10-char hex nonce in a script that looks like it's for video
            if not nonce:
                nonce_matches = re.findall(r'nonce\s*:\s*[\'"]([a-f0-9]{10,12})[\'"]', r.text)
                if nonce_matches:
                    # In HDF, the video nonce is usually one of the first few
                    nonce = nonce_matches[0]
            
            if not nonce:
                self._log_and_emit(download_id, "HDF Nonce bulunamadı! Normal kaynak araması (Fallback) denenecek.")
            else:
                self._log_and_emit(download_id, f"HDF Nonce başarıyla yakalandı: {nonce}")
            
            video_url_orig = None
            
            # --- YÖNTEM 1: AJAX TABANLI OYNATICI (FastPlay, SetPlay vb.) ---
            self._log_and_emit(download_id, "Adım 1: AJAX tabanlı oynatıcılar (FastPlay/SetPlay) aranıyor...")
            tab = soup.find('a', attrs={'data-player-name': 'FastPlay'})
            if not tab:
                # Fallback to any available player if FastPlay is missing
                tab = soup.find('a', class_='options2')
            
            if tab and nonce:

                post_id = tab.get('data-post-id')
                player_name = tab.get('data-player-name')
                part_key = tab.get('data-part-key')
                
                # The AJAX endpoint
                ajax_url = "https://www.hdfilmcehennemi.now/wp-admin/admin-ajax.php"
                
                # Form data for the AJAX request
                payload = {
                    'action': 'get_video_url',
                    'nonce': nonce,
                    'post_id': post_id,
                    'player_name': player_name,
                    'part_key': part_key
                }

                headers = {
                    'Referer': url,
                    'X-Requested-With': 'XMLHttpRequest',
                    'Origin': 'https://www.hdfilmcehennemi.now'
                }

                self._log_and_emit(download_id, f"AJAX isteği gönderiliyor... (Oynatıcı: {player_name})")
                r_ajax = self.session.post(ajax_url, data=payload, headers=headers, timeout=20)
                ajax_data = r_ajax.json()
                
                if ajax_data.get('success') and ajax_data.get('data'):
                    data_val = ajax_data['data']
                    if isinstance(data_val, dict) and 'url' in data_val:
                        video_url_orig = data_val['url']
                    else:
                        video_url_orig = str(data_val)
                    self._log_and_emit(download_id, f"AJAX Başarılı! Oynatıcı URL: {video_url_orig}")
                else:
                    self._log_and_emit(download_id, f"AJAX Başarısız oldu. Yanıt: {ajax_data}")

            # --- YÖNTEM 2: FALLBACK (İframe, script içi m3u8, data attributes) ---
            if not video_url_orig:
                self._log_and_emit(download_id, "Adım 2: Alternatif modda oynatıcı/iframe aranıyor...")
                video_url_orig = self.extract_fallback(soup, download_id)

            if not video_url_orig:
                self._log_and_emit(download_id, "Kritik Hata: Analiz edilen sayfada bilinen hiçbir video kaynağı (FastPlay, Iframe, Embed, M3U8) bulunamadı!", is_error=True)
                return False

            # Convert iframe URL to manifest URL if it's FastPlay or SetPlay
            video_url = video_url_orig
            
            if 'fastplay.mom' in video_url:
                video_id = video_url.rstrip('/').split('/')[-1]
                video_url = f"https://fastplay.mom/manifests/{video_id}/master.txt"
                self._log_and_emit(download_id, f"FastPlay Manifest URL oluşturuldu: {video_url}")
            elif 'setplay.shop' in video_url or 'index.php' in video_url:
                self._log_and_emit(download_id, f"SetPlay/Ara Oynatıcı algılandı, sayfa çözümleniyor: {video_url}")
                try:
                    # Oynatıcı iframe sayfasını kendimiz indirelim (yt-dlp takılmasın)
                    player_r = self.session.get(video_url, headers={'Referer': url}, timeout=15)
                    # Sayfa içindeki file: "..." veya src: "..." bilgisini bulalım
                    match = re.search(r'(?:file|src)\s*:\s*[\'"](https?://[^\'"]+)[\'"]', player_r.text)
                    if match:
                        video_url = match.group(1)
                        # yt-dlp'nin .txt engeline takılmamak için URL sonuna query ekleyelim
                        if video_url.endswith('.txt'):
                            video_url += '#.m3u8'
                        self._log_and_emit(download_id, f"Ara oynatıcıdan Manifest URL çıkarıldı: {video_url}")
                except Exception as e:
                    self._log_and_emit(download_id, f"Ara oynatıcı çözümlenirken hata: {e}")
            
            # Save logic
            show_name = info.get('show', 'Film')
            title_sanitized = self.sanitize_filename(info['title'])
            is_movie = show_name == 'Film' or info.get('season') == '-'
            
            if is_movie:
                # Each movie in its own folder inside 'Filmler'
                save_dir = os.path.join('downloads', 'Filmler', title_sanitized)
                filename = f"{title_sanitized}.mp4"
            else:
                save_dir = os.path.join('downloads', self.sanitize_filename(show_name))
                filename = f"{title_sanitized}.mp4"
            
            if not os.path.exists(save_dir): os.makedirs(save_dir)
            output_path = os.path.join(save_dir, filename)
            self._log_and_emit(download_id, f"Hedef Dosya Yolu: {output_path}")
            
            # Poster
            if info.get('poster'):
                self.download_poster(info['poster'], os.path.join(save_dir, "poster.jpg"))
            
            # 4. Download with yt-dlp
            # NEW: Determine Referer dynamically based on the player URL
            player_domain = video_url_orig.split('/')[2] if '://' in video_url_orig else 'hdfilmcehennemi.now'
            fixed_referer = f"https://{player_domain}/"
            
            # Special case for FastPlay fragments
            if 'fastplay.mom' in video_url_orig:
                fixed_referer = "https://fastplay.mom/"
            
            self._log_and_emit(download_id, f"yt-dlp Motoru Başlatılıyor... | Referer: {fixed_referer}")
            
            ydl_opts = {
                'outtmpl': output_path,
                'quiet': False,
                'no_warnings': False,
                'http_headers': {
                    'User-Agent': self.session.headers.get('User-Agent'),
                    'Referer': fixed_referer,
                    'Origin': f"https://{player_domain}",
                    'Accept': '*/*',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                },
                'progress_hooks': [lambda d: self.progress_hook(d, download_id)],
                'retries': 15,
                'fragment_retries': 15,
                'concurrent_fragment_downloads': 10,
                'nocheckcertificate': True,
                'ignoreerrors': True,
                # Kullanıcı talebi üzerine ekstra parametreler
                'noplaylist': True,
                'external_downloader_args': ['-loglevel', 'info'],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # ffmpeg'i önceliklendir (kullanıcı talebi)
                ydl.params['hls_prefer_ffmpeg'] = True
                ydl.params['hls_prefer_native'] = False
                ydl.download([video_url])
            
            self._log_and_emit(download_id, f"İndirme motoru işlemi tamamladı.")
            return True
            
            return True
        except Exception as e:
            if self.socketio:
                self.socketio.emit('download_progress', {'id': download_id, 'status': 'error', 'error': str(e)}, namespace='/')
            return False
