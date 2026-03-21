import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from downloader_engine import DiziboxEngine
import os
import threading
import uuid
import time
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dizibox-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- DATABASE LOGIC ---
DB_FILE = "db.json"
BASE_DOWNLOADS = "downloads"
os.makedirs(BASE_DOWNLOADS, exist_ok=True)

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return {"downloads": [], "history": []}

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

db = load_db()

# --- ENGINE ---
engine = DiziboxEngine(socketio=socketio)
download_queue = []
worker_thread = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/library')
def get_library():
    result = {'series': [], 'movies': []}
    if not os.path.exists(BASE_DOWNLOADS):
        return jsonify(result)
    
    for item in sorted(os.listdir(BASE_DOWNLOADS)):
        full_path = os.path.join(BASE_DOWNLOADS, item)
        
        # 1. Eski Tip Doğrudan .mp4 (Kök dizindeki filmler/tekliler)
        if os.path.isfile(full_path) and item.endswith('.mp4'):
            movie_name = item.replace('.mp4', '')
            poster_url = None
            if os.path.exists(os.path.join(BASE_DOWNLOADS, f"{movie_name}.jpg")):
                poster_url = f"/video/{movie_name}.jpg"
                
            source = "Dizibox" # ya da HDFilmCehennemi
            for h in db['history']:
                if h['info'].get('title', '').startswith(movie_name):
                    source = h['info'].get('source', 'Dizibox') # varsayılan
                    break
                    
            result['movies'].append({
                'name': movie_name,
                'poster': poster_url,
                'source': source,
                'path': item,
                'url': f'/video/{item}'
            })
            continue

        if not os.path.isdir(full_path): continue
            
        if item == "Filmler":
            # Filmler klasörünün içindeki her alt klasör bir filmdir
            for movie_dir in sorted(os.listdir(full_path)):
                movie_path = os.path.join(full_path, movie_dir)
                if os.path.isdir(movie_path):
                    movie_file = None
                    for f in sorted(os.listdir(movie_path)):
                        if f.endswith('.mp4'):
                            movie_file = f
                            break
                    
                    if movie_file:
                        poster_url = None
                        if os.path.exists(os.path.join(movie_path, "poster.jpg")):
                            poster_url = f"/video/Filmler/{movie_dir}/poster.jpg"
                            
                        # Try to find source in history for movies
                        source = "HDFilmCehennemi"
                        for h in db['history']:
                            if h['info'].get('title', '').startswith(movie_dir):
                                source = h['info'].get('source', 'HDFilmCehennemi')
                                break
                                
                        result['movies'].append({
                            'name': movie_dir,
                            'poster': poster_url,
                            'source': source,
                            'path': os.path.join("Filmler", movie_dir, movie_file),
                            'url': f'/video/Filmler/{movie_dir}/{movie_file}'
                        })
        else:
            # Diziler
            episodes = []
            poster_url = None
            source = "Dizibox" # Default
            
            for h in db['history']:
                if h['info'].get('title', '').startswith(item):
                    source = h['info'].get('source', 'Dizibox')
                    break

            if os.path.exists(os.path.join(full_path, "poster.jpg")):
                poster_url = f"/video/{item}/poster.jpg"
                
            for ep_file in sorted(os.listdir(full_path)):
                if ep_file.endswith('.mp4'):
                    ep_path = os.path.join(item, ep_file)
                    episodes.append({
                        'name': ep_file.replace('.mp4', ''),
                        'path': ep_path,
                        'url': f'/video/{ep_path}'
                    })
                    
            if episodes:
                result['series'].append({
                    'name': item,
                    'poster': poster_url,
                    'source': source,
                    'episodes': episodes
                })
                
    return jsonify(result)

@app.route('/video/<path:filename>')
def serve_video(filename):
    return send_from_directory(BASE_DOWNLOADS, filename)

@app.route('/api/add_download', methods=['POST'])
def add_download():
    data = request.json
    url = data.get('url')
    mode = data.get('mode', 'single')
    
    if not url: return jsonify({'error': 'URL is required'}), 400

    info_list = []
    if mode == 'season':
        links = engine.get_season_links(url)
        for link in links:
            info = engine.get_episode_info(link)
            if info: info_list.append(info)
    else:
        info = engine.get_episode_info(url)
        if info: info_list.append(info)
        else: return jsonify({'error': 'Could not get episode info'}), 404

    new_downloads = []
    for info in info_list:
        download_id = str(uuid.uuid4())
        download_item = {'id': download_id, 'info': info, 'status': 'pending', 'added_at': time.time()}
        download_queue.append(download_item)
        new_downloads.append(download_item)
        
        # Save to DB history
        db['history'].append(download_item)
        save_db(db)
        
    start_worker()
    return jsonify({'downloads': new_downloads})

def worker():
    while download_queue:
        socketio.sleep(0.5) # Give frontend time to catch up
        item = download_queue.pop(0)
        item['status'] = 'downloading'
        socketio.emit('queue_update', {'id': item['id'], 'status': 'downloading'}, namespace='/')
        
        success = engine.download_episode(item['info'], item['id'])
        
        item['status'] = 'completed' if success else 'error'
        socketio.emit('queue_update', {'id': item['id'], 'status': item['status']}, namespace='/')
        
        # Update DB
        for h in db['history']:
            if h['id'] == item['id']: h['status'] = item['status']
        save_db(db)
        
        socketio.sleep(1)

def start_worker():
    global worker_thread
    if worker_thread is None or not worker_thread.is_alive():
        worker_thread = threading.Thread(target=worker)
        worker_thread.daemon = True
        worker_thread.start()

@app.route('/api/watch_vlc', methods=['POST'])
def watch_vlc():
    data = request.json
    path = data.get('path')
    
    if not path:
        return jsonify({'error': 'Yol belirtilmedi'}), 400
    
    # If relative, join with downloads folder
    if not os.path.isabs(path):
        abs_path = os.path.abspath(os.path.join(BASE_DOWNLOADS, path))
    else:
        abs_path = path
    
    if not os.path.exists(abs_path):
        return jsonify({'error': 'Dosya bulunamadı'}), 404
        
    try:
        import subprocess
        # Try to open with vlc
        subprocess.Popen(['vlc', abs_path])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/open_downloads', methods=['POST'])
def open_downloads():
    try:
        import subprocess, sys
        downloads_path = os.path.abspath(BASE_DOWNLOADS)
        if sys.platform == "win32":
            os.startfile(downloads_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", downloads_path])
        else:
            subprocess.Popen(["xdg-open", downloads_path])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5005, debug=True)
