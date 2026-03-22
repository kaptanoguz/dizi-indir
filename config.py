import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-in-production'
    BASE_DOWNLOADS = os.environ.get('DOWNLOADS_DIR', 'downloads')
    DB_FILE = os.environ.get('DB_FILE', 'db.json')
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5005')
    ALLOWED_DOWNLOAD_DOMAINS = ['dizibox.live', 'www.dizibox.live', 'hdfilmcehennemi.now', 'www.hdfilmcehennemi.now']
    MAX_URL_LENGTH = 500
