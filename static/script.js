const socket = io();

// ---------------------------
// TOAST NOTIFICATION SYSTEM
// ---------------------------
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';
    
    toast.innerHTML = `
        <i class="fas ${icon}"></i>
        <div class="toast-message">${message}</div>
    `;
    
    container.appendChild(toast);
    
    // Auto dismiss after 4 seconds
    setTimeout(() => {
        toast.classList.add('closing');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ---------------------------
// NAVIGATION
// ---------------------------
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        item.classList.add('active');
        
        const targetId = item.getAttribute('data-target');
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(targetId).classList.add('active');
    });
});

// ---------------------------
// URL VALIDATION & SMART SWITCH
// ---------------------------
const urlInput = document.getElementById('url-input');
const urlIndicator = document.getElementById('url-indicator');
const modeToggle = document.getElementById('mode-toggle');
const labelSingle = document.getElementById('label-single');
const labelSeason = document.getElementById('label-season');

urlInput.addEventListener('input', (e) => {
    const val = e.target.value.trim();
    if (val.length === 0) {
        urlIndicator.className = 'url-indicator';
        urlIndicator.innerHTML = '<i class="fas fa-check-circle"></i>';
        return;
    }
    
    // Basic validation for supported domains
    if (val.includes('dizibox') || val.includes('hdfilmcehennemi')) {
        urlIndicator.className = 'url-indicator valid';
        urlIndicator.innerHTML = '<i class="fas fa-check-circle"></i>';
    } else {
        urlIndicator.className = 'url-indicator invalid';
        urlIndicator.innerHTML = '<i class="fas fa-times-circle"></i>';
    }
    
    // Smart switch: If URL contains "-sezon-" or similar, suggest season mode
    if (val.includes('-sezon-') || val.includes('season')) {
        modeToggle.checked = true;
        updateModeLabels();
    }
});

modeToggle.addEventListener('change', updateModeLabels);

function updateModeLabels() {
    if (modeToggle.checked) {
        labelSingle.classList.remove('active');
        labelSeason.classList.add('active');
    } else {
        labelSeason.classList.remove('active');
        labelSingle.classList.add('active');
    }
}

// ---------------------------
// DOWNLOAD LOGIC & QUEUE
// ---------------------------
const btnDownload = document.getElementById('btn-download');
const queueList = document.getElementById('queue-list');
const queueCount = document.getElementById('queue-count');

let activeDownloads = {};

btnDownload.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) {
        showToast("Lütfen bir URL girin.", "error");
        return;
    }

    const mode = modeToggle.checked ? 'season' : 'single';
    btnDownload.disabled = true;
    btnDownload.innerHTML = '<i class="fas fa-spinner fa-spin"></i> İşleniyor...';

    try {
        const response = await fetch('/api/add_download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, mode })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`${data.downloads.length} öğe kuyruğa eklendi.`, "success");
            urlInput.value = '';
            urlIndicator.className = 'url-indicator';
            
            // Remove empty state if exists
            const emptyState = queueList.querySelector('.empty-state');
            if (emptyState) emptyState.remove();
            
            data.downloads.forEach(dl => {
                createQueueItem(dl);
                activeDownloads[dl.id] = dl;
            });
            updateQueueCount();
        } else {
            showToast(data.error || "İndirme başlatılamadı.", "error");
        }
    } catch (err) {
        showToast("Sunucu ile bağlantı kurulamadı.", "error");
    } finally {
        btnDownload.disabled = false;
        btnDownload.innerHTML = '<i class="fas fa-download"></i> İndirmeyi Başlat';
    }
});

function createQueueItem(dl) {
    const item = document.createElement('div');
    item.className = 'queue-item';
    item.id = `queue-${dl.id}`;
    
    item.innerHTML = `
        <div class="queue-info">
            <h4>${dl.info.show} - ${dl.info.season}.S ${dl.info.episode}.B</h4>
            <p id="progress-text-${dl.id}">${dl.info.title || "Hazırlanıyor..."}</p>
        </div>
        <div class="status-badge status-${dl.status}" id="badge-${dl.id}">
            ${dl.status === 'pending' ? 'BEKLİYOR' : dl.status.toUpperCase()}
        </div>
        <div class="shimmer-progress" id="progress-bar-${dl.id}"></div>
    `;
    queueList.prepend(item);
}

function updateQueueCount() {
    const count = Object.keys(activeDownloads).length;
    queueCount.textContent = `${count} Öğe`;
}

// Socket.io listeners
socket.on('queue_update', (data) => {
    const badge = document.getElementById(`badge-${data.id}`);
    if (badge) {
        badge.className = `status-badge status-${data.status}`;
        let statusText = data.status === 'downloading' ? 'İNDİRİLİYOR' :
                         data.status === 'completed' ? 'TAMAMLANDI' :
                         data.status === 'error' ? 'HATA' : 'BEKLİYOR';
        badge.textContent = statusText;
        
        if (data.status === 'completed') {
            showToast("İndirme tamamlandı!", "success");
            const pb = document.getElementById(`progress-bar-${data.id}`);
            if(pb) { pb.style.width = '100%'; pb.style.background = 'var(--success)'; }
        } else if (data.status === 'error') {
            showToast("İndirme sırasında bir hata oluştu.", "error");
            const pb = document.getElementById(`progress-bar-${data.id}`);
            if(pb) { pb.style.width = '100%'; pb.style.background = 'var(--error)'; }
        }
    }
});

socket.on('download_progress', (data) => {
    const pText = document.getElementById(`progress-text-${data.id}`);
    const pBar = document.getElementById(`progress-bar-${data.id}`);
    
    if (pText && pBar) {
        if (data.status === 'downloading') {
            const percent = (data.downloaded_bytes / data.total_bytes) * 100 || 0;
            pText.textContent = `%${percent.toFixed(1)} - ${formatBytes(data.speed)}/s`;
            pBar.style.width = `${percent}%`;
        }
    }
});

function formatBytes(bytes, decimals = 2) {
    if (!+bytes) return '0 Bytes';
    const k = 1024, dm = decimals < 0 ? 0 : decimals, sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

// ---------------------------
// LIBRARY & LAZY LOADING
// ---------------------------
async function loadLibrary() {
    try {
        const res = await fetch('/api/library');
        const data = await res.json();
        
        renderSeries(data.series);
        renderMovies(data.movies);
    } catch (err) {
        showToast("Kütüphane yüklenemedi.", "error");
    }
}

// Intersection Observer for Lazy Loading Images
const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            img.src = img.dataset.src;
            img.onload = () => img.classList.add('loaded');
            observer.unobserve(img);
        }
    });
}, { rootMargin: "50px" });

function renderSeries(seriesList) {
    const grid = document.getElementById('series-grid');
    grid.innerHTML = '';
    
    seriesList.forEach(show => {
        const card = document.createElement('div');
        card.className = 'media-card';
        
        let posterHTML = '';
        if (show.poster) {
            posterHTML = `<img data-src="${show.poster}" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=" alt="${show.name}">`;
        } else {
            const letter = show.name.charAt(0).toUpperCase();
            posterHTML = `<div class="avatar-placeholder">${letter}</div>`;
        }
        
        card.innerHTML = `
            <div class="poster-wrapper">
                ${posterHTML}
                <div class="card-overlay">
                    <button class="overlay-btn play-btn" title="Bölümleri Gör"><i class="fas fa-play"></i></button>
                    <button class="overlay-btn vlc-btn" title="Klasörde Aç"><i class="fas fa-folder"></i></button>
                </div>
            </div>
            <div class="card-info">
                <h3>${show.name}</h3>
                <p>${show.source} • ${show.episodes.length} Bölüm</p>
            </div>
        `;
        
        const img = card.querySelector('img');
        if (img) imageObserver.observe(img);
        
        card.querySelector('.play-btn').onclick = (e) => {
            e.stopPropagation();
            openShowEpisodes(show);
        };
        
        card.querySelector('.vlc-btn').onclick = async (e) => {
            e.stopPropagation();
            await fetch('/api/open_downloads', {method: 'POST'});
        };
        
        grid.appendChild(card);
    });
}

function renderMovies(movieList) {
    const grid = document.getElementById('movies-grid');
    grid.innerHTML = '';
    
    movieList.forEach(movie => {
        const card = document.createElement('div');
        card.className = 'media-card';
        
        let posterHTML = '';
        if (movie.poster) {
            posterHTML = `<img data-src="${movie.poster}" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=" alt="${movie.name}">`;
        } else {
            const letter = movie.name.charAt(0).toUpperCase();
            posterHTML = `<div class="avatar-placeholder">${letter}</div>`;
        }
        
        card.innerHTML = `
            <div class="poster-wrapper">
                ${posterHTML}
                <div class="card-overlay">
                    <button class="overlay-btn play-btn" title="İzle"><i class="fas fa-play"></i></button>
                    <button class="overlay-btn vlc-btn" title="VLC'de İzle"><i class="fas fa-traffic-cone"></i></button>
                </div>
            </div>
            <div class="card-info">
                <h3>${movie.name}</h3>
                <p>Film • ${movie.source}</p>
            </div>
        `;
        
        const img = card.querySelector('img');
        if (img) imageObserver.observe(img);
        
        card.querySelector('.play-btn').onclick = (e) => {
            e.stopPropagation();
            openPlayer(movie.url, movie.name, "Film");
        };
        
        card.querySelector('.vlc-btn').onclick = async (e) => {
            e.stopPropagation();
            try {
                const res = await fetch('/api/watch_vlc', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({path: movie.path})
                });
                const data = await res.json();
                if(data.error) showToast(data.error, "error");
            } catch(e) {
                showToast("VLC açılamadı.", "error");
            }
        };
        
        grid.appendChild(card);
    });
}

// ---------------------------
// EPISODES MODAL
// ---------------------------
const epModal = document.getElementById('episodes-modal');
const epList = document.getElementById('episodes-list');

function openShowEpisodes(show) {
    document.getElementById('ep-show-name').textContent = show.name;
    epList.innerHTML = '';
    
    show.episodes.forEach((ep, i) => {
        const row = document.createElement('div');
        row.className = 'ep-row';
        row.innerHTML = `
            <div class="ep-num">${i + 1}</div>
            <div class="ep-name">${ep.name}</div>
            <div class="ep-actions">
                <div class="ep-action-btn vlc" title="VLC'de İzle"><i class="fas fa-traffic-cone"></i></div>
                <div class="ep-action-btn play" title="İzle"><i class="fas fa-play"></i></div>
            </div>
        `;
        
        row.querySelector('.play').onclick = () => {
            epModal.classList.remove('active');
            openPlayer(ep.url, ep.name, show.name);
        };
        
        row.querySelector('.vlc').onclick = async () => {
            try {
                const res = await fetch('/api/watch_vlc', {
                    method: 'POST',
                    headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({path: ep.path})
                });
                const data = await res.json();
                if(data.error) showToast(data.error, "error");
            } catch(e) {
                showToast("VLC açılamadı.", "error");
            }
        };
        
        epList.appendChild(row);
    });
    
    epModal.classList.add('active');
}

document.querySelector('.close-modal-ep').onclick = () => epModal.classList.remove('active');

// ---------------------------
// CUSTOM VIDEO PLAYER
// ---------------------------
const playerModal = document.getElementById('player-modal');
const videoElement = document.getElementById('custom-video');
const playPauseBtn = document.getElementById('play-pause-btn');
const muteBtn = document.getElementById('mute-btn');
const volumeSlider = document.getElementById('volume-slider');
const progressContainer = document.getElementById('progress-container');
const progressBar = document.getElementById('progress-bar');
const currentTimeEl = document.getElementById('current-time');
const durationEl = document.getElementById('duration');
const fullscreenBtn = document.getElementById('fullscreen-btn');
const playerContainer = document.querySelector('.player-container');

function openPlayer(url, title, subtitle) {
    document.getElementById('player-title').textContent = title;
    document.getElementById('player-subtitle').textContent = subtitle;
    videoElement.src = url;
    playerModal.classList.add('active');
    
    videoElement.play().catch(e => {
        showToast("Otomatik oynatma tarayıcı tarafından engellendi.", "info");
        playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
    });
}

function closePlayer() {
    playerModal.classList.remove('active');
    videoElement.pause();
    videoElement.src = '';
    // if fullscreen, exit it
    if(document.fullscreenElement) document.exitFullscreen();
}

document.querySelector('.close-player').onclick = closePlayer;

// Video controls logic
let controlsTimeout;
function showControls() {
    playerContainer.classList.add('show-controls');
    clearTimeout(controlsTimeout);
    controlsTimeout = setTimeout(() => {
        if (!videoElement.paused) {
            playerContainer.classList.remove('show-controls');
        }
    }, 3000);
}

playerContainer.onmousemove = showControls;
videoElement.onplay = showControls;

playPauseBtn.onclick = togglePlay;
videoElement.onclick = togglePlay;

function togglePlay() {
    if (videoElement.paused) {
        videoElement.play();
        playPauseBtn.innerHTML = '<i class="fas fa-pause"></i>';
    } else {
        videoElement.pause();
        playPauseBtn.innerHTML = '<i class="fas fa-play"></i>';
    }
}

videoElement.addEventListener('timeupdate', () => {
    const percent = (videoElement.currentTime / videoElement.duration) * 100 || 0;
    progressBar.style.width = `${percent}%`;
    currentTimeEl.textContent = formatTime(videoElement.currentTime);
});

videoElement.addEventListener('loadedmetadata', () => {
    durationEl.textContent = formatTime(videoElement.duration);
});

progressContainer.addEventListener('click', (e) => {
    const rect = progressContainer.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    videoElement.currentTime = pos * videoElement.duration;
});

muteBtn.onclick = () => {
    videoElement.muted = !videoElement.muted;
    muteBtn.innerHTML = videoElement.muted ? '<i class="fas fa-volume-mute"></i>' : '<i class="fas fa-volume-up"></i>';
    volumeSlider.value = videoElement.muted ? 0 : videoElement.volume;
};

volumeSlider.addEventListener('input', (e) => {
    videoElement.volume = e.target.value;
    videoElement.muted = e.target.value == 0;
    muteBtn.innerHTML = videoElement.muted ? '<i class="fas fa-volume-mute"></i>' : '<i class="fas fa-volume-up"></i>';
});

fullscreenBtn.onclick = () => {
    if (!document.fullscreenElement) {
        playerContainer.requestFullscreen().catch(err => {
            showToast("Tam ekran desteklenmiyor", "error");
        });
    } else {
        document.exitFullscreen();
    }
};

function formatTime(seconds) {
    if(isNaN(seconds)) return "00:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// Keybindings
document.addEventListener('keydown', (e) => {
    if (!playerModal.classList.contains('active')) return;
    
    switch(e.key.toLowerCase()) {
        case ' ':
        case 'k':
            e.preventDefault();
            togglePlay();
            break;
        case 'f':
            e.preventDefault();
            fullscreenBtn.click();
            break;
        case 'm':
            e.preventDefault();
            muteBtn.click();
            break;
        case 'arrowright':
            e.preventDefault();
            videoElement.currentTime = Math.min(videoElement.duration, videoElement.currentTime + 10);
            break;
        case 'arrowleft':
            e.preventDefault();
            videoElement.currentTime = Math.max(0, videoElement.currentTime - 10);
            break;
        case 'escape':
            if (!document.fullscreenElement) closePlayer();
            break;
    }
});

// Windows open folder
document.querySelectorAll('.btn-open-folder').forEach(btn => {
    btn.addEventListener('click', async () => {
        try {
            const reqPath = btn.getAttribute('data-path') || '';
            const res = await fetch('/api/open_downloads', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: reqPath})
            });
            const data = await res.json();
            if(data.error) showToast(data.error, "error");
        } catch(e) {
            showToast("Klasör açılamadı", "error");
        }
    });
});

// Modal dismiss by clicking outside
window.onclick = (e) => {
    if (e.target === playerModal) closePlayer();
    if (e.target === epModal) epModal.classList.remove('active');
};
