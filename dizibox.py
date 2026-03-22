import requests
import re
from bs4 import BeautifulSoup
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from hashlib import md5
import base64
import sys
import os
from tqdm import tqdm
import yt_dlp
from concurrent.futures import ThreadPoolExecutor, as_completed

def bytes_to_key(data, salt, output=48):
    data += salt; key = md5(data).digest(); final_key = key
    while len(final_key) < output: key = md5(key + data).digest(); final_key += key
    return final_key[:output]

def decrypt(encrypted_data, password):
    encrypted_data_bytes = base64.b64decode(encrypted_data); salt = encrypted_data_bytes[8:16]; ciphertext = encrypted_data_bytes[16:]
    key_iv = bytes_to_key(password.encode(), salt, 48); key = key_iv[:32]; iv = key_iv[32:]
    cipher = AES.new(key, AES.MODE_CBC, iv); return unpad(cipher.decrypt(ciphertext), AES.block_size).decode()

def sanitize_filename(name):
    cleaned_name = ' '.join(name.split()); return re.sub(r'[\\/*?:"<>|]', "", cleaned_name).strip()

def download_with_yt_dlp(video_url, referer, output_path):
    pbar = None
    def progress_hook(d):
        nonlocal pbar
        if d['status'] == 'downloading':
            if pbar is None: pbar = tqdm(total=d.get('total_bytes_estimate', 0), unit='B', unit_scale=True, unit_divisor=1024, desc="-> İndiriliyor (HLS)", leave=False, bar_format='{l_bar}{bar:20}{r_bar}')
            if d.get('total_bytes_estimate'): pbar.total = d['total_bytes_estimate']
            pbar.update(d['downloaded_bytes'] - pbar.n)
    try:
        with yt_dlp.YoutubeDL({'outtmpl': output_path, 'quiet': True, 'noprogress': True, 'http_headers': {'Referer': referer}, 'progress_hooks':[progress_hook], 'retries': 5, 'concurrent_fragment_downloads': 64}) as ydl: ydl.download([video_url])
        return True
    finally:
        if pbar:
            if pbar.total and pbar.n < pbar.total: pbar.update(pbar.total - pbar.n)
            pbar.close()

def download_parallel_mp4(video_url, referer, output_path, session, connections=64):
    headers = {'Referer': referer, 'User-Agent': session.headers['User-Agent']}
    try:
        r = session.head(video_url, headers=headers, allow_redirects=True, timeout=10)
        if r.status_code not in (200, 206): r = session.get(video_url, headers=headers, stream=True, timeout=10)
    except: return download_with_yt_dlp(video_url, referer, output_path)
    
    file_size = int(r.headers.get('Content-Length', 0))
    if r.headers.get('Accept-Ranges', '') != 'bytes' or file_size == 0 or 'm3u8' in video_url: return download_with_yt_dlp(video_url, referer, output_path)
    
    chunk_size = file_size // connections
    ranges =[(i * chunk_size, (i + 1) * chunk_size - 1 if i < connections - 1 else file_size - 1) for i in range(connections)]
    with open(output_path, "wb") as f: f.truncate(file_size)
    pbar = tqdm(total=file_size, unit='B', unit_scale=True, unit_divisor=1024, desc=f"-> Sömürülüyor ({connections} Kol)", leave=False, bar_format='{l_bar}{bar:20}{r_bar}')
    
    def download_chunk(start, end):
        req_headers = headers.copy(); current_start = start
        for _ in range(5):
            req_headers['Range'] = f'bytes={current_start}-{end}'
            try:
                resp = session.get(video_url, headers=req_headers, stream=True, timeout=15)
                with open(output_path, "r+b") as f:
                    f.seek(current_start)
                    for chunk in resp.iter_content(chunk_size=1048576):
                        if chunk: f.write(chunk); pbar.update(len(chunk)); current_start += len(chunk)
                return True
            except: continue
        raise Exception("Parça koptu")

    try:
        with ThreadPoolExecutor(max_workers=connections) as executor:
            for future in as_completed([executor.submit(download_chunk, s, e) for s, e in ranges]): future.result()
        return True
    except Exception: return download_with_yt_dlp(video_url, referer, output_path)
    finally: pbar.close()

def attempt_dizibox_download(episode_url, output_path, session):
    print("-> Ana sistem (Dizibox) deneniyor...")
    response = session.get(episode_url, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    king_php_url = soup.find('iframe', {'src': re.compile(r'king\.php')})['src']
    response = session.get(king_php_url, headers={'Referer': episode_url}, timeout=30)
    soup = BeautifulSoup(response.text, 'html.parser')
    moly_embed_url = soup.find('iframe', {'src': re.compile(r'molystream\.org/embed/')})['src']
    response = session.get(moly_embed_url, headers={'Referer': king_php_url}, timeout=30)
    match = re.search(r'CryptoJS\.AES\.decrypt\("([^"]+)",\s*"([^"]+)"\)', response.text, re.DOTALL)
    if not match: raise ValueError("Dizibox: Kripto verisi bulunamadı.")
    decrypted_html = decrypt(match.group(1), match.group(2))
    final_video_url = BeautifulSoup(decrypted_html, 'html.parser').find('source')['src']
    
    download_parallel_mp4(final_video_url, moly_embed_url, output_path, session)
    print("-> TAMAMLANDI")
    return True

def main():
    if len(sys.argv) < 2: print("Kullanım:\n  Tek bölüm: ...py \"LINK\"\n  Tüm sezon: ...py \"LINK\" --sezon"); return
    start_url = re.sub(r'/\d+$', '', sys.argv[1].rstrip('/'))
    season_mode = '--sezon' in sys.argv
    session = requests.Session(); session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'})
    successful_downloads, failed_downloads = [],[]

    try:
        print("Analiz başlıyor..."); response = session.get(start_url); soup = BeautifulSoup(response.text, 'html.parser')
        episode_links = [start_url]
        if season_mode:
            print("Sezon modu aktif..."); ul = soup.select_one('#related-posts > ul')
            if ul: episode_links = [li.find('a', href=True)['href'] for li in ul.find_all('li') if li.find('a', href=True)]
            if not episode_links: print("HATA: Hiç bölüm linki bulunamadı."); return
        else: print("Tek bölüm modu aktif.")
        
        print(f"Toplam {len(episode_links)} bölüm işlenecek."); print("=" * 40)
        
        for i, link in enumerate(episode_links, 1):
            filename = "Bilinmiyor"
            try:
                page_response = session.get(link); page_soup = BeautifulSoup(page_response.text, 'html.parser')
                dizi_adi_tag = page_soup.select_one('#main-wrapper > div.content-wrapper > div.title > h1 > span.tv-title-archive > span')
                sezon_bolum_tag = page_soup.select_one('#main-wrapper > div.content-wrapper > div.title > h1 > span.tv-title-episode')
                bolum_adi_tag = page_soup.select_one('#main-wrapper > div.content-wrapper > div.title > h1 > small')
                if not (dizi_adi_tag and sezon_bolum_tag): raise ValueError("Dizi/Sezon bilgileri okunamadı.")
                dizi_adi = dizi_adi_tag.text.strip(); sezon_bolum_text = sezon_bolum_tag.text.strip()
                bolum_adi = re.sub(r'^\s*\((.*?)\)\s*$', r'\1', bolum_adi_tag.text) if bolum_adi_tag else ""
                sezon_no = re.search(r'(\d+)\.Sezon', sezon_bolum_text).group(1)
                bolum_no = re.search(r'(\d+)\.Bölüm', sezon_bolum_text).group(1)
                folder_name = sanitize_filename(f"{dizi_adi} {sezon_no}.Sezon"); os.makedirs(folder_name, exist_ok=True)
                filename = sanitize_filename(f"{bolum_no}. Bölüm{f' - {bolum_adi}' if bolum_adi else ''}.mp4")
                output_path = os.path.join(folder_name, filename)

                print(f"İşlem[{i}/{len(episode_links)}]: {filename}")
                
                if os.path.exists(output_path):
                    print("-> MEVCUT, atlanıyor."); successful_downloads.append(filename + " (Mevcut)"); continue
                
                if attempt_dizibox_download(link, output_path, session):
                    successful_downloads.append(filename)
                else:
                    raise Exception("Ana sistemden bilinmeyen bir hata döndü.")

            except Exception as e:
                error_info = f"'{filename}' - Sebep: {e}"; print(f"HATA: {error_info}"); failed_downloads.append(error_info)
            finally:
                print("-" * 40)
    finally:
        print("\nİşlem Raporu:"); print("=" * 40)
        if successful_downloads: print(f"Başarılı: {len(successful_downloads)}")
        if failed_downloads:
            print(f"Başarısız: {len(failed_downloads)}");[print(f"  - {item}") for item in failed_downloads]
        print("=" * 40); print("Tüm işlemler tamamlandı.")

if __name__ == '__main__':
    main()
