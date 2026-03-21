document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const views = document.querySelectorAll('.view');
    const navItems = document.querySelectorAll('.nav-links li');
    const libraryGrid = document.getElementById('library-grid');
    const dlList = document.getElementById('dl-list');
    const dlCountBadge = document.getElementById('dl-count');
    
    let activeDownloadsCount = 0;
    const downloadCards = {};

    // --- VIEW NAVIGATION ---
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const viewId = 'view-' + item.getAttribute('data-view');
            navItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            views.forEach(v => {
                v.classList.remove('active');
                if (v.id === viewId) v.classList.add('active');
            });
            if (viewId === 'view-library') loadLibrary();
        });
    });

    // --- ADD DOWNLOAD ---
    const btnStartDl = document.getElementById('btn-start-dl');
    const dlUrlInput = document.getElementById('dl-url');
    const modeButtons = document.querySelectorAll('.mode-switch button');
    let currentMode = 'single';

    modeButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            modeButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentMode = btn.getAttribute('data-mode');
        });
    });

    btnStartDl.addEventListener('click', async () => {
        const url = dlUrlInput.value.trim();
        if (!url) return;

        btnStartDl.disabled = true;
        btnStartDl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analiz Ediliyor...';

        try {
            const response = await fetch('/api/add_download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, mode: currentMode })
            });
            const data = await response.json();
            if (data.error) throw new Error(data.error);

            dlUrlInput.value = '';
            document.querySelector('[data-view="downloads"]').click();
            data.downloads.forEach(dl => createDownloadCard(dl));
        } catch (err) {
            alert('Hata: ' + err.message);
        } finally {
            btnStartDl.disabled = false;
            btnStartDl.innerHTML = '<i class="fas fa-magic"></i> Analiz Et ve Başlat';
        }
    });

    // --- DOWNLOAD CARDS ---
    function createDownloadCard(dl) {
        if (downloadCards[dl.id]) return;
        const card = document.createElement('div');
        card.className = 'dl-card';
        card.id = `dl-${dl.id}`;
        card.innerHTML = `
            <div class="dl-icon"><i class="fas fa-cloud-download-alt"></i></div>
            <div class="dl-main">
                <div class="dl-info">
                    <h4>${dl.info.show} - S${dl.info.season}E${dl.info.episode}</h4>
                    <span class="dl-status">Bekliyor...</span>
                </div>
                <div class="progress-bar"><div class="progress-fill" style="width: 0%"></div></div>
                <div class="dl-meta">
                    <span class="dl-percent">0%</span>
                    <span class="dl-speed">-- MB/s</span>
                    <span class="dl-eta">Kalan: --:--</span>
                    <span class="dl-size">-- / --</span>
                </div>
            </div>
        `;
        dlList.appendChild(card);
        downloadCards[dl.id] = card;
        activeDownloadsCount++;
        updateDlBadge();
        applyBufferedMessages(dl.id);
    }

    function updateDlBadge() {
        dlCountBadge.textContent = activeDownloadsCount;
        dlCountBadge.style.display = activeDownloadsCount > 0 ? 'block' : 'none';
    }

    const socketBuffer = {};

    function applyBufferedMessages(id) {
        if (socketBuffer[id]) {
            socketBuffer[id].forEach(data => {
                if (data.type === 'progress') handleProgress(data);
                else if (data.type === 'queue') handleQueue(data);
            });
            delete socketBuffer[id];
        }
    }

    // --- SOCKET.IO EVENTS ---
    socket.on('download_progress', (data) => {
        data.type = 'progress';
        const card = downloadCards[data.id];
        if (!card) {
            if (!socketBuffer[data.id]) socketBuffer[data.id] = [];
            socketBuffer[data.id].push(data);
            return;
        }
        handleProgress(data);
    });

    socket.on('queue_update', (data) => {
        data.type = 'queue';
        const card = downloadCards[data.id];
        if (!card) {
            if (!socketBuffer[data.id]) socketBuffer[data.id] = [];
            socketBuffer[data.id].push(data);
            return;
        }
        handleQueue(data);
    });

    function handleProgress(data) {
        const card = downloadCards[data.id];
        const fill = card.querySelector('.progress-fill');
        const percent = card.querySelector('.dl-percent');
        const speed = card.querySelector('.dl-speed');
        const eta = card.querySelector('.dl-eta');
        const status = card.querySelector('.dl-status');
        const meta = card.querySelector('.dl-size');

        if (data.status === 'downloading') {
            const p = parseFloat(data.progress);
            if (p > 0) {
                fill.style.width = p + '%';
                percent.textContent = p + '%';
                fill.classList.remove('pulse');
            } else {
                fill.style.width = '100%';
                fill.classList.add('pulse');
                percent.textContent = 'İndiriliyor...';
            }
            speed.textContent = data.speed;
            eta.textContent = 'Kalan: ' + data.eta;
            status.textContent = 'İndiriliyor...';
            meta.textContent = `${data.downloaded} / ${data.total}`;
        } else if (data.status === 'finished' || data.status === 'already_exists') {
            fill.classList.remove('pulse');
            fill.style.width = '100%';
            percent.textContent = '100%';
            status.textContent = data.status === 'finished' ? 'Tamamlandı' : 'Zaten Mevcut';
            status.style.color = '#2ecc71';
            setTimeout(() => {
                activeDownloadsCount = Math.max(0, activeDownloadsCount - 1);
                updateDlBadge();
                loadLibrary();
            }, 2000);
        } else if (data.status === 'error') {
            status.textContent = 'Hata!';
            status.style.color = '#ff4757';
        }
    }

    function handleQueue(data) {
        const card = downloadCards[data.id];
        const status = card.querySelector('.dl-status');
        const fill = card.querySelector('.progress-fill');
        
        if (data.status === 'downloading') {
            status.textContent = 'İşleniyor...';
            status.style.color = 'var(--accent)';
        } else if (data.status === 'completed') {
            status.textContent = 'Tamamlandı';
            status.style.color = '#2ecc71';
            fill.style.width = '100%';
            setTimeout(() => {
                loadLibrary();
            }, 2000);
        } else if (data.status === 'error') {
            status.textContent = 'Hata!';
            status.style.color = '#ff4757';
        }
    }

    // --- VLC ICON SVG (Premium Realistic Cone) ---
    const vlcIconSvg = `<svg class="vlc-icon-svg" viewBox="0 0 512 512" width="22" height="22" xmlns="http://www.w3.org/2000/svg">
        <path fill="#e67e22" d="M464 448H352.4L281.8 86.6c-3.5-17.8-19.1-30.6-37.2-30.6h-1.3c-18.1 0-33.7 12.8-37.2 30.6L135.5 448H48c-8.8 0-16 7.2-16 16v16c0 8.8 7.2 16 16 16h416c8.8 0 16-7.2 16-16v-16c0-8.8-7.2-16-16-16z"/>
        <path fill="#fff" d="M155.2 416l25.6-128h152l25.6 128H155.2z"/>
        <path fill="#fff" d="M211.8 224h88.4l12.8-64h-114l12.8 64z"/>
    </svg>`;

    // --- VLC INTEGRATION ---
    async function watchInVlc(path) {
        if (!path) return;
        try {
            const response = await fetch('/api/watch_vlc', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });
            const result = await response.json();
            if (!result.success) alert("VLC başlatılamadı: " + result.error);
        } catch (error) {
            console.error("VLC hatası:", error);
        }
    }

    // --- LIBRARY LOGIC ---
    async function loadLibrary() {
        try {
            const res = await fetch('/api/library');
            const data = await res.json();
            renderLibrary(data);
        } catch (err) { console.error('Library Load Error:', err); }
    }

    function renderLibrary(shows) {
        libraryGrid.innerHTML = '';
        if (shows.length === 0) {
            libraryGrid.innerHTML = '<div class="empty-state">Henüz dizi indirilmemiş.</div>';
            return;
        }

        shows.forEach(show => {
            const card = document.createElement('div');
            card.className = 'lib-card';
            card.innerHTML = `
                <div class="lib-poster">
                    <img src="${show.poster || '/static/placeholder.jpg'}" alt="${show.name}">
                    <div class="lib-source-badge">${show.source || 'Dizibox'}</div>
                    <div class="lib-overlay">
                        <button class="lib-play" title="Hemen İzle"><i class="fas fa-play"></i></button>
                        <button class="lib-vlc" title="VLC'de İzle">${vlcIconSvg}</button>
                    </div>
                </div>
                <div class="lib-info">
                    <h3>${show.name}</h3>
                    <p>${show.source === 'HDFilmCehennemi' && show.episodes.length === 1 ? 'Film' : show.episodes.length + ' Bölüm'}</p>
                </div>
            `;
            
            // Add event listener for VLC
            card.querySelector('.lib-vlc').onclick = (e) => {
                e.stopPropagation();
                // Assuming the first episode's path for VLC for a show card
                if (show.episodes && show.episodes.length > 0) {
                    watchInVlc(show.episodes[0].path);
                } else {
                    alert("Bu dizi için oynatılabilir bölüm bulunamadı.");
                }
            };
            
            card.addEventListener('click', () => openShowEpisodes(show));
            libraryGrid.appendChild(card);
        });
    }

    // --- EPISODES MODAL ---
    const epModal = document.getElementById('episodes-modal');
    const epShowName = document.getElementById('ep-show-name');
    const epList = document.getElementById('episodes-list');
    const closeEpModal = document.querySelector('.close-modal-ep');

    function openShowEpisodes(show) {
        epShowName.textContent = show.name;
        epList.innerHTML = '';
        show.episodes.forEach((ep, index) => {
            const row = document.createElement('div');
            row.className = 'ep-row';
            row.innerHTML = `
                <div class="ep-num">${index + 1}</div>
                <div class="ep-name">${ep.name.replace('.mp4', '')}</div>
                <div class="ep-actions">
                    <div class="ep-vlc" title="VLC'de İzle">${vlcIconSvg}</div>
                    <div class="ep-play" title="İzle"><i class="fas fa-play"></i></div>
                </div>
            `;
            
            // Fix row click - make it more specific
            row.querySelector('.ep-play').onclick = () => {
                epModal.classList.remove('active');
                playVideo(ep.url, ep.name, show.name);
            };
            
            row.querySelector('.ep-vlc').onclick = (e) => {
                e.stopPropagation();
                watchInVlc(ep.path);
            };

            epList.appendChild(row);
        });
        epModal.classList.add('active');
    }

    closeEpModal.onclick = () => epModal.classList.remove('active');

    // --- VIDEO PLAYER MODAL ---
    const playerModal = document.getElementById('player-modal');
    const videoPlayer = document.getElementById('video-player');
    const playerTitle = document.getElementById('player-title');
    const playerSubtitle = document.getElementById('player-subtitle');
    const closeModal = document.querySelector('.close-modal');

    function playVideo(url, title, subtitle) {
        videoPlayer.src = url;
        playerTitle.textContent = title.replace('.mp4', '');
        playerSubtitle.textContent = subtitle;
        playerModal.classList.add('active');
        videoPlayer.play();
    }

    closeModal.onclick = () => {
        playerModal.classList.remove('active');
        videoPlayer.pause();
        videoPlayer.src = '';
    };

    window.onclick = (e) => {
        if (e.target === playerModal) closeModal.onclick();
        if (e.target === epModal) epModal.classList.remove('active');
    };

    loadLibrary();
});
