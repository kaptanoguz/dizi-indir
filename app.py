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

@app.route('/video_file')
def video_file():
    target_path = request.args.get('path')
    if not target_path:
        return "Path required", 400
        
    abs_path = os.path.realpath(target_path)
    base_check = False
    for root in Config.ALLOWED_ROOTS:
        if abs_path.startswith(root):
            base_check = True
            break
            
    if not base_check or not os.path.exists(abs_path):
        return "Unauthorized or Not Found", 403
        
    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory, filename)

if __name__ == '__main__':
    logging.info("Starting CipherDrop on port 5005")
    socketio.run(app, host='0.0.0.0', port=5005, debug=False)
