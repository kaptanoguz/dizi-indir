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
            card.className = 'card';
            card.innerHTML = `
                <div class="card-img" style="${show.poster ? `background-image: url('${show.poster}'); background-size: cover;` : ''}">
                    ${show.poster ? '' : '<i class="fas fa-film"></i>'}
                    <div class="card-overlay">
                        <div class="btn-play-series"><i class="fas fa-list"></i></div>
                    </div>
                </div>
                <div class="card-info">
                    <h3>${show.name}</h3>
                    <p>${show.episodes.length} Bölüm</p>
                </div>
            `;
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
                <div class="ep-play"><i class="fas fa-play"></i></div>
            `;
            row.addEventListener('click', () => {
                epModal.classList.remove('active');
                playVideo(ep.url, ep.name, show.name);
            });
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
