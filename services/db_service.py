import json
import os
import tempfile
import threading
import logging
from config import Config

class DBService:
    def __init__(self):
        self.db_file = Config.DB_FILE
        self.lock = threading.Lock()
        self.db = self._load_db()

    def _load_db(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading DB: {e}")
        return {"downloads": [], "history": []}

    def save_db(self):
        with self.lock:
            try:
                # Atomik yazma işlemi: Önce geçici dosyaya yaz, sonra orijinalin üzerine taşı
                fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(self.db_file)))
                with os.fdopen(fd, 'w') as f:
                    json.dump(self.db, f, indent=4)
                os.replace(temp_path, self.db_file)
            except Exception as e:
                logging.error(f"Save DB error: {e}")

    def get_history(self):
        with self.lock:
            return list(self.db['history'])

    def add_history(self, item):
        with self.lock:
            self.db['history'].append(item)
        self.save_db()
        
    def update_history_status(self, item_id, status):
        with self.lock:
            for h in self.db['history']:
                if h['id'] == item_id:
                    h['status'] = status
        self.save_db()

db_service = DBService()
