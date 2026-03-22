<div align="center">
  <img src="static/cipherdrop_logo.png" alt="CipherDrop Logo" width="300">
</div>

# CipherDrop

Dizibox Downloader'ın komut satırı aracını, **güvenliği artırılmış modüler mimari** ve modern bir Web (Glassmorphism) arayüzüne dönüştürülmüş halidir. 

### 🌟 Premium V2 Özellikleri

*   **Modern Web Arayüzü (Glassmorphism):** Koyu tema, akıllı bildirimler (Toasts), neon vurgular ve indirme animasyonlarıyla göz alıcı bir tasarım.
*   **Modüler Crawler Mimarisi:** Dizibox ve HDFilmCehennemi gibi birden fazla siteyi `plugins/` klasörü üzerinden kolayca destekler ve eş zamanlı dizi/film indirir.
*   **Kapsamlı Güvenlik:** CORS (Sadece yerel izinler), URL doğrulama, Domain filtreleri, Path Traversal korumaları ve atomik DB yazımlarıyla tamamen güvenli arka plan.
*   **Dahili Gelişmiş Video Oynatıcı:** Kısayol (Space/F/Oklar) uyumlu, modal içi tam ekran ve özel progress çubuğu ile entegre izleme.
*   **10 Kat Hız (Paralel İndirme):** HLS/Fragment tabanlı videoları yt-dlp 10 kanallı paralel indirme desteği ile kurar.
*   **Afiş ve Kütüphane Izgarası:** İndirilenlerin posterleri alınarak "Filmler" ve "Diziler" şeklinde şık kart tasarımlarında listelenir. "Klasörü Aç" butonları ile yerel dosyalara hızlı erişim.

### 🚀 Kurulum

1.  **Sanal Ortam ve Bağımlılıkları Yükleyin:**
    ```bash
    python -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Konfigürasyonu Ayarlayın:**
    ```bash
    cp .env.example .env
    ```
    *(İsteğe bağlı)* `.env` dosyası içindeki `SECRET_KEY` değerini değiştirebilirsiniz (Örn: `python -c "import secrets; print(secrets.token_hex(32))"`).

3.  **Uygulamayı Başlatın:**
    ```bash
    python app.py
    ```

4.  **Tarayıcıdan Erişin:**
    `http://localhost:5005` adresine gidin.

### 🛠️ Teknolojiler

*   **Backend:** Python 3.12, Flask, Flask-SocketIO
*   **Güvenlik ve Mimari:** python-dotenv, Service-Routes ayrımı, Thread-safe JSON Yönetimi.
*   **Frontend:** Vanilla JS, CSS (Glassmorphism), FontAwesome
*   **Motor:** yt-dlp, BeautifulSoup4

### 📝 Notlar
- İndirmelerin hızlı ve stabil olması için sisteminizde `ffmpeg` ve `vlc` yüklü olması önerilir.
- Tüm I/O işlemleri Atomik yapıya geçirilerek ani kapanmalarda veri bozulması önlenmiştir.
- ANSI renk kodları arayüzde temizlenerek tertemiz bir indirme özeti sunulur.

---
Geliştirici: **trakir** | Premium Modüler Mimari & Optimizasyon: **Antigravity AI**
