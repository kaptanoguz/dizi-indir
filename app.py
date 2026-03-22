import os
import logging
import eventlet
eventlet.monkey_patch()

from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from config import Config
from downloader_engine import DiziboxEngine
from services.download_service import DownloadService
from routes.views import views_bp
from routes.api import init_api_routes

# Loglama Konfigürasyonu (Console ve Dosya)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='app.log')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)

app = Flask(__name__)
app.config.from_object(Config)

# CORS güvenliği
socketio = SocketIO(app, cors_allowed_origins=Config.ALLOWED_ORIGINS.split(','))

os.makedirs(Config.BASE_DOWNLOADS, exist_ok=True)

# Servisler
engine = DiziboxEngine(socketio=socketio)
download_service = DownloadService(engine=engine, socketio=socketio)

# Rotaları Kayıt Et
app.register_blueprint(views_bp)
api_bp = init_api_routes(download_service, engine)
app.register_blueprint(api_bp, url_prefix='/api')

@app.route('/video/<path:filename>')
def serve_video(filename):
    # Path Traversal (Yetkisiz dizin erişimi) kontrolü
    abs_path = os.path.realpath(os.path.join(Config.BASE_DOWNLOADS, filename))
    base_real = os.path.realpath(Config.BASE_DOWNLOADS)
    if not abs_path.startswith(base_real):
        return "Unauthorized", 403
    return send_from_directory(Config.BASE_DOWNLOADS, filename)

if __name__ == '__main__':
    logging.info("Starting DiziBOX Platform on port 5005")
    socketio.run(app, host='0.0.0.0', port=5005, debug=False)
