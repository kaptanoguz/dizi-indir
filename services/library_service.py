import os
import logging
from config import Config
from .db_service import db_service

def get_library_data():
    result = {'series': [], 'movies': []}
    history = db_service.get_history()
    
    # 1. Scan Movies
    movies_dir = Config.MOVIES_DIR
    if os.path.exists(movies_dir):
        try:
            movie_items = sorted(os.listdir(movies_dir))
            for item in movie_items:
                full_path = os.path.join(movies_dir, item)
                
                # Double handling: item is a file (.mp4) or a directory containing .mp4
                movie_file = None
                movie_name = ""
                movie_root_path = ""
                
                if os.path.isfile(full_path) and item.endswith('.mp4'):
                    movie_file = item
                    movie_name = item.replace('.mp4', '')
                    movie_root_path = movies_dir
                elif os.path.isdir(full_path):
                    movie_name = item
                    movie_root_path = full_path
                    for f in sorted(os.listdir(full_path)):
                        if f.endswith('.mp4'):
                            movie_file = f
                            break
                
                if movie_file:
                    poster_url = None
                    if os.path.exists(os.path.join(movie_root_path, "poster.jpg")):
                        poster_url = f"/video_file?path={os.path.join(movie_root_path, 'poster.jpg')}"
                    elif os.path.exists(os.path.join(movies_dir, f"{movie_name}.jpg")):
                        poster_url = f"/video_file?path={os.path.join(movies_dir, f'{movie_name}.jpg')}"
                        
                    source = "HDFilmCehennemi"
                    for h in history:
                        if h['info'].get('title', '').startswith(movie_name):
                            source = h['info'].get('source', 'HDFilmCehennemi')
                            break
                            
                    result['movies'].append({
                        'name': movie_name,
                        'poster': poster_url,
                        'source': source,
                        'path': os.path.join(movie_root_path, movie_file),
                        'url': f"/video_file?path={os.path.join(movie_root_path, movie_file)}"
                    })
        except Exception as e:
            logging.error(f"Error reading movies directory: {e}")

    # 2. Scan Series
    series_dir = Config.SERIES_DIR
    if os.path.exists(series_dir):
        try:
            series_items = sorted(os.listdir(series_dir))
            for item in series_items:
                # Avoid "Filmler" if it's inside series_dir (default case)
                if item == "Filmler": continue
                
                full_path = os.path.join(series_dir, item)
                if not os.path.isdir(full_path): continue
                
                episodes = []
                poster_url = None
                if os.path.exists(os.path.join(full_path, "poster.jpg")):
                    poster_url = f"/video_file?path={os.path.join(full_path, 'poster.jpg')}"
                
                source = "Dizibox"
                for h in history:
                    if h['info'].get('title', '').startswith(item):
                        source = h['info'].get('source', 'Dizibox')
                        break
                
                ep_files = sorted(os.listdir(full_path))
                for ep_file in ep_files:
                    if ep_file.endswith('.mp4'):
                        ep_real_path = os.path.join(full_path, ep_file)
                        episodes.append({
                            'name': ep_file.replace('.mp4', ''),
                            'path': ep_real_path,
                            'url': f"/video_file?path={ep_real_path}"
                        })
                        
                if episodes:
                    result['series'].append({
                        'name': item,
                        'poster': poster_url,
                        'source': source,
                        'episodes': episodes
                    })
        except Exception as e:
            logging.error(f"Error reading series directory: {e}")
                
    return result
                
    return result
