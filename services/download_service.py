import threading
import logging
from .db_service import db_service

class DownloadService:
    def __init__(self, engine, socketio):
        self.engine = engine
        self.socketio = socketio
        self.queue = []
        self.queue_lock = threading.Lock()
        self.is_running = False

    def add_to_queue(self, download_item):
        with self.queue_lock:
            self.queue.append(download_item)
        db_service.add_history(download_item)
        self.start_worker()

    def worker(self):
        while True:
            item = None
            with self.queue_lock:
                if self.queue:
                    item = self.queue.pop(0)
                else:
                    self.is_running = False
                    break
                    
            if not item:
                break
                
            self.socketio.sleep(0.5) # Give frontend time to catch up
            item['status'] = 'downloading'
            self.socketio.emit('queue_update', {'id': item['id'], 'status': 'downloading'}, namespace='/')
            
            try:
                success = self.engine.download_episode(item['info'], item['id'])
            except Exception as e:
                logging.error(f"Download failed for {item['id']}: {e}")
                success = False
                
            item['status'] = 'completed' if success else 'error'
            self.socketio.emit('queue_update', {'id': item['id'], 'status': item['status']}, namespace='/')
            
            db_service.update_history_status(item['id'], item['status'])
            self.socketio.sleep(1)

    def start_worker(self):
        with self.queue_lock:
            if not self.is_running:
                self.is_running = True
                self.socketio.start_background_task(self.worker)
