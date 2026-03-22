import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-in-production'
    HOME_DIR = os.path.expanduser("~")
    BASE_DOWNLOADS = os.environ.get('DOWNLOADS_DIR', os.path.join(HOME_DIR, 'Downloads', 'CipherDrop'))
    
    # Category specific directories
    SERIES_DIR = os.environ.get('SERIES_DIR', BASE_DOWNLOADS)
    MOVIES_DIR = os.environ.get('MOVIES_DIR', os.path.join(BASE_DOWNLOADS, 'Filmler'))
    
    # Security: List of all allowed base paths for traversal checks
    ALLOWED_ROOTS = [os.path.realpath(p) for p in [BASE_DOWNLOADS, SERIES_DIR, MOVIES_DIR]]
    
    CONFIG_DIR = os.path.join(HOME_DIR, '.config', 'cipherdrop')
    os.makedirs(CONFIG_DIR, exist_ok=True)
    DB_FILE = os.environ.get('DB_FILE', os.path.join(CONFIG_DIR, 'db.json'))
    
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5005')
    ALLOWED_DOWNLOAD_DOMAINS = ['dizibox.live', 'www.dizibox.live', 'hdfilmcehennemi.now', 'www.hdfilmcehennemi.now']
    MAX_URL_LENGTH = 500
