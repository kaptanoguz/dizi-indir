import os
import re
import requests
import yt_dlp
from bs4 import BeautifulSoup
from plugins.base_crawler import BaseCrawler

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
        # Use a browser-like User-Agent to avoid simplified HTML
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
        })
        
        try:
            r = self.session.get(url, timeout=30)
            soup = BeautifulSoup(r.text, 'html.parser')

            # 1. Scrape the nonce from the script with DOTALL to handle newlines
            nonce = None
            # Look for window.videoAjax = { ... nonce: '...' }
            nonce_match = re.search(r'videoAjax\s*=\s*\{.*?"?nonce"?:\s*\'([^\']+)\'', r.text, re.DOTALL)
            if not nonce_match:
                # Try single quotes for the key or other variations
                nonce_match = re.search(r'nonce\s*:\s*\'([^\']+)\'', r.text)
            
            if nonce_match:
                nonce = nonce_match.group(1)
            
            if not nonce:
                # Last resort: search for any 10-char alphanumeric string assigned to a nonce key in scripts
                for script in soup.find_all('script'):
                    if script.string and 'videoAjax' in script.string:
                        m = re.search(r'nonce\s*:\s*\'([^\']+)\'', script.string)
                        if m:
                            nonce = m.group(1)
                            break
            
            if not nonce:
                print("HDF Nonce bulunamadı. Sayfa içeriği aranıyor...")
                # Debug: print a portion of r.text to logs if possible
            
            # 2. Find FastPlay tab data
            tab = soup.find('a', attrs={'data-player-name': 'FastPlay'})
            if not tab:
                # Fallback to any available player if FastPlay is missing
                tab = soup.find('a', class_='options2')
            
            if not tab:
                print("HDF Oynatıcı sekmesi bulunamadı.")
                return False

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

            r_ajax = self.session.post(ajax_url, data=payload, headers=headers, timeout=20)
            ajax_data = r_ajax.json()
            
            if not ajax_data.get('success') or not ajax_data.get('data'):
                print(f"HDF AJAX hatası: {ajax_data}")
                return False
                
            video_url = ajax_data['data'] # This is the iframe URL (e.g., fastplay.mom/video/...)
            
            # Convert iframe URL to manifest URL if it's FastPlay
            if 'fastplay.mom' in video_url:
                video_id = video_url.split('/')[-1]
                video_url = f"https://fastplay.mom/manifests/{video_id}/master.txt"
            
            # Save logic
            show_name = info.get('show', 'Film')
            is_movie = show_name == 'Film' or info.get('season') == '-'
            
            if is_movie:
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
