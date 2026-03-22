import os
import uuid
import time
import shutil
import subprocess
import sys
from urllib.parse import urlparse
from flask import Blueprint, request, jsonify
from config import Config
from services.library_service import get_library_data

api_bp = Blueprint('api', __name__)

def init_api_routes(download_service, engine):
    
    @api_bp.route('/library')
    def get_library():
        result = get_library_data()
        return jsonify(result)

    @api_bp.route('/add_download', methods=['POST'])
    def add_download():
        data = request.json
        url = data.get('url', '').strip()
        mode = data.get('mode', 'single')
        
        if not url: return jsonify({'error': 'URL is required'}), 400
        if len(url) > Config.MAX_URL_LENGTH: return jsonify({'error': 'URL_too_long'}), 400
        
        # Domain validation
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            if domain not in Config.ALLOWED_DOWNLOAD_DOMAINS:
                return jsonify({'error': 'Desteklenmeyen domain'}), 403
        except Exception:
            return jsonify({'error': 'Geçersiz URL formatı'}), 400

        info_list = []
        if mode == 'season':
            try:
                links = engine.get_season_links(url)
                if not links: return jsonify({'error': 'Sezon linkleri bulunamadı'}), 404
                for link in links:
                    info = engine.get_episode_info(link)
                    if info: info_list.append(info)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        else:
            try:
                info = engine.get_episode_info(url)
                if info: info_list.append(info)
                else: return jsonify({'error': 'Bölüm bilgisi alınamadı'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        new_downloads = []
        for info in info_list:
            if not info: continue
            download_id = str(uuid.uuid4())
            download_item = {'id': download_id, 'info': info, 'status': 'pending', 'added_at': time.time()}
            
            new_downloads.append(download_item)
            download_service.add_to_queue(download_item)
            
        return jsonify({'downloads': new_downloads})

    @api_bp.route('/watch_vlc', methods=['POST'])
    def watch_vlc():
        data = request.json
        path = data.get('path')
        
        if not path:
            return jsonify({'error': 'Yol belirtilmedi'}), 400
            
        # Path traversal prevention
        abs_path = os.path.realpath(os.path.join(Config.BASE_DOWNLOADS, path))
        base_real = os.path.realpath(Config.BASE_DOWNLOADS)
        if not abs_path.startswith(base_real):
            return jsonify({'error': 'Yetkisiz yol erişimi'}), 403
        
        if not os.path.exists(abs_path):
            return jsonify({'error': 'Dosya bulunamadı'}), 404
            
        # VLC executable check
        vlc_executable = shutil.which('vlc')
        if not vlc_executable:
            vlc_executable = shutil.which('vlc.exe')
            if not vlc_executable:
                return jsonify({'error': 'VLC oynatıcı sistemde bulunamadı.'}), 500
            
        try:
            subprocess.Popen([vlc_executable, abs_path])
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @api_bp.route('/open_downloads', methods=['POST'])
    def open_downloads():
        try:
            req_path = request.json.get('path', '') if request.is_json else ''
            downloads_path = os.path.realpath(os.path.join(Config.BASE_DOWNLOADS, req_path))
            base_real = os.path.realpath(Config.BASE_DOWNLOADS)
            
            # Path traverse protection
            if not downloads_path.startswith(base_real):
                downloads_path = base_real
                
            if not os.path.exists(downloads_path):
                os.makedirs(downloads_path, exist_ok=True)
                
            if sys.platform == "win32":
                os.startfile(downloads_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", downloads_path])
            else:
                subprocess.Popen(["xdg-open", downloads_path])
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return api_bp
