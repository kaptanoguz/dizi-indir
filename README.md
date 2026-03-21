# Dizibox Premium Downloader GUI

Dizibox Downloader'ın komut satırı aracını, modern ve şık bir Web arayüzüne dönüştürülmüş halidir. Bu uygulama ile dizileri tarayıcı üzerinden kolayca indirebilir, indirme ilerlemesini takip edebilir ve kütüphanenizdeki dizileri doğrudan tarayıcıda izleyebilirsiniz.

### 🌟 Premium Özellikler

*   **Modern Web Arayüzü:** Koyu tema, cam morfolojisi (glassmorphism) ve neon vurgularla şık bir tasarım.
*   **Afiş Desteği:** İndirilen dizilerin afişleri otomatik olarak getirilir ve kütüphaneniz bir poster galerisine dönüşür.
*   **Gerçek Zamanlı İlerleme:** Socket.IO senkronizasyonu ile indirme yüzdesi, hızı ve kalan süreyi anlık takip edin.
*   **10 Kat Hız (Paralel İndirme):** HLS/Fragment tabanlı videoları 10 kanallı paralel indirme desteği ile saniyeler içinde indirin.
*   **Dahili Video Oynatıcı:** İndirdiğiniz bölümleri başka bir programa ihtiyaç duymadan tarayıcıda izleyin.
*   **Kalıcı Kütüphane:** `db.json` sayesinde indirme geçmişiniz her zaman güvende.

### 🚀 Kurulum

1.  **Bağımlılıkları Yükleyin:**
    ```bash
    pip install flask flask-socketio eventlet requests beautifulsoup4 pycryptodome tqdm yt-dlp
    ```
2.  **Uygulamayı Başlatın:**
    ```bash
    python app.py
    ```
3.  **Tarayıcıdan Erişin:**
    `http://localhost:5005` adresine gidin.

### 🛠️ Teknolojiler

*   **Backend:** Python 3.12+, Flask, Flask-SocketIO (Eventlet)
*   **Frontend:** Vanilla JS, CSS (Glassmorphism), FontAwesome
*   **Motor:** yt-dlp, BeautifulSoup4

### Notlar
- İndirmelerin hızlı ve stabil olması için sisteminizde `ffmpeg` yüklü olması önerilir.
- ANSI renk kodları arayüzde temizlenerek tertemiz bir metin sunulur.

---
Geliştirici: **trakir** | Premium GUI & Optimizasyon: **Antigravity AI**
