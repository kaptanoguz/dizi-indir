import os
import logging
from config import Config
from .db_service import db_service

def get_library_data():
    result = {'series': [], 'movies': []}
    base_dir = Config.BASE_DOWNLOADS
    
    if not os.path.exists(base_dir):
        return result
    
    try:
        items = sorted(os.listdir(base_dir))
    except Exception as e:
        logging.error(f"Error reading library directory: {e}")
        return result
        
    history = db_service.get_history()
    
    for item in items:
        full_path = os.path.join(base_dir, item)
        
        # 1. Eski Tip Doğrudan .mp4
        if os.path.isfile(full_path) and item.endswith('.mp4'):
            movie_name = item.replace('.mp4', '')
            poster_url = None
            if os.path.exists(os.path.join(base_dir, f"{movie_name}.jpg")):
                poster_url = f"/video/{movie_name}.jpg"
                
            source = "Dizibox"
            for h in history:
                if h['info'].get('title', '').startswith(movie_name):
                    source = h['info'].get('source', 'Dizibox')
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
            try:
                movie_dirs = sorted(os.listdir(full_path))
            except Exception as e:
                logging.error(f"Error reading Filmler directory: {e}")
                continue
                
            for movie_dir in movie_dirs:
                movie_path = os.path.join(full_path, movie_dir)
                if os.path.isdir(movie_path):
                    movie_file = None
                    try:
                        for f in sorted(os.listdir(movie_path)):
                            if f.endswith('.mp4'):
                                movie_file = f
                                break
                    except Exception as e:
                        logging.error(f"Error reading movie directory {movie_dir}: {e}")
                        continue
                    
                    if movie_file:
                        poster_url = None
                        if os.path.exists(os.path.join(movie_path, "poster.jpg")):
                            poster_url = f"/video/Filmler/{movie_dir}/poster.jpg"
                            
                        source = "HDFilmCehennemi"
                        for h in history:
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
            source = "Dizibox"
            
            for h in history:
                if h['info'].get('title', '').startswith(item):
                    source = h['info'].get('source', 'Dizibox')
                    break

            if os.path.exists(os.path.join(full_path, "poster.jpg")):
                poster_url = f"/video/{item}/poster.jpg"
                
            try:
                ep_files = sorted(os.listdir(full_path))
            except Exception as e:
                logging.error(f"Error reading series directory {item}: {e}")
                continue
                
            for ep_file in ep_files:
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
                
    return result
