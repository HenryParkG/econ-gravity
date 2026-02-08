// --- Global Variables ---
let currentNewsData = [];
let filteredData = []; // To hold filtered list
let currentCategory = 'all';

async function loadNews() {
    try {
        const response = await fetch('data/news.json?t=' + new Date().getTime());
        if (!response.ok) throw new Error('데이터를 불러올 수 없습니다.');

        const data = await response.json();
        currentNewsData = data.items;

        // Initial filter (shows all)
        filterNews('all');

        const lastUpdated = document.getElementById('last-updated');
        const briefingSection = document.getElementById('briefing-section');
        const briefingContent = document.getElementById('briefing-content');
        const loadMoreContainer = document.getElementById('load-more-container');

        if (lastUpdated) lastUpdated.textContent = `최근 업데이트: ${data.last_updated}`;

        if (data.briefing && briefingSection) {
            briefingSection.style.display = 'block';
            briefingContent.textContent = data.briefing;

            // TTS Logic
            const ttsBtn = document.getElementById('tts-btn');
            if (ttsBtn) {
                ttsBtn.onclick = () => {
                    if ('speechSynthesis' in window) {
                        if (window.speechSynthesis.speaking) {
                            window.speechSynthesis.cancel();
                            ttsBtn.classList.remove('tts-playing');
                            ttsBtn.textContent = '🔈 듣기';
                        } else {
                            const utterance = new SpeechSynthesisUtterance(data.briefing);
                            utterance.lang = 'ko-KR';
                            utterance.rate = 1.0;
                            utterance.pitch = 1.0;

                            utterance.onend = () => {
                                ttsBtn.classList.remove('tts-playing');
                            };

                            window.speechSynthesis.speak(utterance);
                            ttsBtn.classList.add('tts-playing');
                            ttsBtn.textContent = '🔊 중지';
                        }
                    } else {
                        alert('이 브라우저는 음성 합성을 지원하지 않습니다.');
                    }
                };
            }
        }

        // Ticker Logic
        if (data.indices && data.indices.length > 0) {
            const tickerContainer = document.getElementById('ticker-container');
            const tickerContent = document.getElementById('ticker-content');

            if (tickerContainer && tickerContent) {
                tickerContainer.style.display = 'block';
                // Adjust header padding for ticker
                // const isMobile = window.innerWidth <= 768;
                // if (!isMobile) document.querySelector('header').style.paddingTop = '100px'; 

                tickerContent.innerHTML = data.indices.map(idx => `
                    <div class="ticker-item">
                        <span class="ticker-name">${idx.name}</span>
                        <span class="ticker-value">${idx.value}</span>
                        <span class="ticker-change ${idx.is_up ? 'up' : 'down'}">${idx.change}</span>
                    </div>
                `).join('');

                // Duplicate for smooth loop if not enough items
                if (data.indices.length < 10) {
                    tickerContent.innerHTML += tickerContent.innerHTML + tickerContent.innerHTML;
                }
            }
        }

    } catch (error) {
        console.error('Error:', error);
        document.getElementById('news-container').innerHTML = `
            <div class="loading">리포트를 불러오는 중 오류가 발생했습니다.</div>
        `;
    }
}

function filterNews(category) {
    currentCategory = category;

    // Update visual state of buttons (Sidebar & Chips)
    document.querySelectorAll('.nav-item').forEach(el => {
        if (el.dataset.category === category) el.classList.add('active');
        else el.classList.remove('active');
    });

    document.querySelectorAll('.chip').forEach(btn => {
        // Simple check based on text context for chips as they just have onclick
        // Or better, add data attributes to chips too. 
        // For now, let's rely on the text matching logical mapping or just re-render
    });

    // Specifically for Chips:
    const chips = document.querySelectorAll('.chip');
    chips.forEach(chip => {
        if (chip.textContent.includes('전체') && category === 'all') chip.classList.add('active');
        else if (chip.textContent.includes(category)) chip.classList.add('active');
        else chip.classList.remove('active');
    });

    const container = document.getElementById('news-container');
    const loadMoreContainer = document.getElementById('load-more-container');
    container.innerHTML = '';

    // Filter Logic
    if (category === 'all') {
        filteredData = currentNewsData;
    } else {
        filteredData = currentNewsData.filter(item =>
            (item.category && item.category.includes(category))
        );
    }

    if (filteredData.length === 0) {
        container.innerHTML = '<div class="loading">해당 카테고리의 뉴스가 없습니다.</div>';
        if (loadMoreContainer) loadMoreContainer.style.display = 'none';
        return;
    }

    renderNewsItems(filteredData, container);

    // Show 'Load More' only if showing 'All' and we have enough items
    // (Simplification: Load Archive is designed to append to EVERYTHING. 
    // Filtering complex mixed lists is tricky. For now, hide Load More on filters)
    if (loadMoreContainer) {
        if (category === 'all' && currentNewsData.length >= 50) {
            loadMoreContainer.style.display = 'block';
        } else {
            loadMoreContainer.style.display = 'none';
        }
    }

    // Close sidebar on mobile selection
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar && sidebar.classList.contains('active')) {
        sidebar.classList.remove('active');
        overlay.classList.remove('active');
    }
}


// ... (loadNews and filterNews remain the same) ...

async function loadArchive() {
    const btn = document.getElementById('load-more-btn');
    const BATCH_SIZE = 20; // Number of items to show per click

    // 1. If buffer has items, just render the next batch
    if (archiveBuffer.length > 0) {
        renderNextBatch(btn, BATCH_SIZE);
        return;
    }

    // 2. If already fetched but buffer empty, it means we really have nothing left
    if (isArchiveFetched && archiveBuffer.length === 0) {
        btn.style.display = 'none';
        return;
    }

    // 3. First time fetching archive
    btn.textContent = '불러오는 중...';
    btn.disabled = true;

    try {
        const response = await fetch('data/news_archive.json?t=' + new Date().getTime());
        if (!response.ok) throw new Error('아카이브를 불러올 수 없습니다.');

        const data = await response.json();

        // Deduplicate against current displayed list
        const currentTitles = new Set(currentNewsData.map(item => item.title));

        // Store ONLY new items in the buffer
        archiveBuffer = data.items.filter(item => !currentTitles.has(item.title));
        isArchiveFetched = true;

        if (archiveBuffer.length > 0) {
            btn.disabled = false;
            btn.textContent = '지난 뉴스 더 보기'; // Reset text
            renderNextBatch(btn, BATCH_SIZE);
        } else {
            alert("더 이상 불러올 과거 뉴스가 없습니다.");
            btn.textContent = '모든 뉴스를 불러왔습니다';
        }

    } catch (error) {
        console.error('Archive Error:', error);
        btn.textContent = '실패 (다시 시도)';
        btn.disabled = false;
    }
}

function renderNextBatch(btn, batchSize) {
    const container = document.getElementById('news-container');

    // Take a slice from the buffer
    const batch = archiveBuffer.splice(0, batchSize);

    if (batch.length > 0) {
        // Append to global data source (so filters work on them later)
        currentNewsData = currentNewsData.concat(batch);

        // Render this batch to DOM
        renderNewsItems(batch, container);

        // If user was filtering, we might need to re-apply filter to hide non-matching items from this new batch
        // But simply calling filterNews(currentCategory) re-renders EVERYTHING which mocks the point of batching?
        // No, current renderNewsItems appends. 
        // Best approach: Just render. Then if category is NOT all, hide the ones that don't match.
        // Actually simpler: re-run filter logic if category != all
        if (currentCategory !== 'all') {
            filterNews(currentCategory);
        }
    }

    // Check if we need to hide button
    if (archiveBuffer.length === 0) {
        btn.textContent = '모든 뉴스를 불러왔습니다';
        btn.disabled = true;
        setTimeout(() => { btn.style.display = 'none'; }, 2000);
    }
}

// Fallback Images (Curated High-Quality Finance/Tech)
const fallbackImages = [
    "https://images.unsplash.com/photo-1611974714028-ac8a49f70659?q=80&w=1024&auto=format&fit=crop", // Stock Chart
    "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?q=80&w=1024&auto=format&fit=crop", // Ticker
    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1024&auto=format&fit=crop", // Skyscraper
    "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1024&auto=format&fit=crop", // Global Network
    "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1024&auto=format&fit=crop", // AI Chip
    "https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1024&auto=format&fit=crop", // Real Estate
    "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?q=80&w=1024&auto=format&fit=crop", // Cargo Ship
    "https://images.unsplash.com/photo-1534951009808-766178b47a8e?q=80&w=1024&auto=format&fit=crop", // Financial Newspaper
    "https://images.unsplash.com/photo-1642543492481-44e81e3914a7?q=80&w=1024&auto=format&fit=crop", // Ethereum
    "https://images.unsplash.com/photo-1550565118-c974fb6255f0?q=80&w=1024&auto=format&fit=crop", // Network
];

function renderNewsItems(items, container) {
    items.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'news-card animate-slide-up';
        card.style.animationDelay = `${Math.min(index * 0.05, 1)}s`;
        card.style.cursor = 'pointer';

        // Add hero-card class to first item for grid sizing
        if (index === 0) card.classList.add('hero-card');

        const publishedDate = item.published_at || '';
        const datePart = publishedDate.split(' ')[0] || '';
        const timePart = publishedDate.split(' ')[1] ? publishedDate.split(' ')[1].substring(0, 5) : '--:--';
        const today = new Date().toISOString().split('T')[0];
        const displayTime = datePart === today ? timePart : `${datePart} ${timePart}`;

        // Select a deterministic fallback image based on title hash
        // This ensures the same article always gets the same fallback image even on refresh
        let hash = 0;
        const titleForHash = item.title || 'default';
        for (let i = 0; i < titleForHash.length; i++) {
            hash = (hash << 5) - hash + titleForHash.charCodeAt(i);
            hash |= 0; // Convert to 32bit integer
        }
        const safeIndex = Math.abs(hash) % fallbackImages.length;
        const randomFallback = fallbackImages[safeIndex];

        const imageUrl = item.image_url || randomFallback;

        // UNIFIED STRUCTURE: Image Top, Content Bottom
        // Using <img> tag with randomized fallback on error
        card.innerHTML = `
            <div class="news-image-wrapper" style="height: ${index === 0 ? '300px' : '160px'}; width: 100%; margin-bottom: 20px; overflow: hidden; border-radius: 12px; background-color: #f0f0f0;">
                <img src="${imageUrl}" 
                     alt="${item.title}" 
                     class="news-image-mobile" 
                     style="width: 100%; height: 100%; object-fit: cover; display: block;"
                     onerror="this.onerror=null; this.src='${randomFallback}';">
            </div>
            <div class="news-content">
                <div class="card-meta">
                    <span class="category-tag">${item.category || '경제'}</span>
                    <span class="time-tag">${displayTime}</span>
                </div>
                <h3>${item.title}</h3>
                <div class="summary">${item.summary || item.description || '내용을 불러오는 중...'}</div>
            </div>
        `;

        card.onclick = () => openModalWithItem(item);
        container.appendChild(card);
    });
}

// Refactored to accept item object directly to handle mixed data sources safely
function openModalWithItem(item) {
    if (!item) return;

    const modal = document.getElementById('news-modal');
    const modalImg = document.getElementById('modal-image');
    const modalText = document.getElementById('modal-text');

    // Defensive checks for old data format
    modalImg.src = item.image_url || 'https://images.unsplash.com/photo-1611974714028-ac8a49f70659?q=80&w=1024&auto=format&fit=crop';

    // User Request: Show Date instead of Source
    const dateStr = item.published_at || new Date().toISOString().replace('T', ' ').substring(0, 16);
    document.getElementById('modal-source').textContent = dateStr; // Now showing Date

    document.getElementById('modal-title').textContent = item.title || 'No Title';

    const content = item.content || item.description || '상세 내용을 준비 중입니다.';
    let formattedContent = content.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');

    // Add Source and Link (Conditioned)
    formattedContent += `
        <br><br>
        <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--glass-border); font-size: 0.9rem; color: var(--text-secondary);">
            <strong>출처:</strong> ${item.source || 'Unknown'} <br>
    `;

    if (item.link && item.link.startsWith('http')) {
        formattedContent += `
            <a href="${item.link}" target="_blank" style="color: var(--accent-color); text-decoration: none; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; margin-top: 8px; pointer-events: auto;">
                🔗 원문 기사 보러가기
            </a>
        </div>
        `;
    } else {
        formattedContent += `</div>`;
    }

    modalText.innerHTML = formattedContent;

    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    const modal = document.getElementById('news-modal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// ... (previous functions)

document.addEventListener('DOMContentLoaded', () => {
    loadNews();

    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
        loadMoreBtn.onclick = loadArchive;
    }

    // Modal Logic
    const modal = document.getElementById('news-modal');
    const closeBtn = document.querySelector('.modal-close');
    const modalImg = document.getElementById('modal-image');

    if (modalImg) {
        modalImg.onerror = () => {
            modalImg.src = 'https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?q=80&w=1024&auto=format&fit=crop';
        };
    }

    if (closeBtn) closeBtn.onclick = closeModal;
    window.onclick = (event) => {
        if (event.target == modal) closeModal();
    };

    // Sidebar Navigation Logic
    document.querySelectorAll('.nav-item').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const category = e.target.closest('.nav-item').dataset.category;
            filterNews(category);
        });
    });

    // Mobile Menu Toggle
    const menuBtn = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    if (menuBtn && sidebar && overlay) {
        menuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('active');
            overlay.classList.toggle('active');
        });

        overlay.addEventListener('click', () => {
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        });
    }

    // Theme Toggle Logic
    const themeToggle = document.getElementById('theme-toggle');
    const html = document.documentElement;
    const body = document.body;

    // Check saved theme
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        body.setAttribute('data-theme', 'light');
        if (themeToggle) themeToggle.textContent = '☀️';
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = body.getAttribute('data-theme');
            if (currentTheme === 'light') {
                body.removeAttribute('data-theme');
                themeToggle.textContent = '🌙';
                localStorage.setItem('theme', 'dark');
            } else {
                body.setAttribute('data-theme', 'light');
                themeToggle.textContent = '☀️';
                localStorage.setItem('theme', 'light');
            }
        });
    }

    // Sidebar: Archive Toggle Logic
    const archiveToggle = document.getElementById('archive-toggle');
    const archiveList = document.getElementById('archive-list');

    if (archiveToggle && archiveList) {
        // Toggle Menu
        archiveToggle.addEventListener('click', (e) => {
            e.preventDefault();
            archiveList.classList.toggle('open');
            const isExpanded = archiveList.classList.contains('open');
            archiveToggle.setAttribute('aria-expanded', isExpanded);

            // Load index only once on first open
            if (isExpanded && archiveList.children.length === 0) {
                loadArchiveIndex();
            }
        });
    }

    // Function to load Archive Index
    async function loadArchiveIndex() {
        const archiveList = document.getElementById('archive-list');
        archiveList.innerHTML = '<li style="padding:10px; color:#666;">로딩 중...</li>';

        try {
            const response = await fetch('data/archive_index.json?t=' + new Date().getTime());
            if (!response.ok) {
                if (response.status === 404) {
                    archiveList.innerHTML = '<li style="padding:10px; color:#666;">아직 아카이브가 없습니다.</li>';
                    return;
                }
                throw new Error('Index fetch failed');
            }

            const indexData = await response.json();
            archiveList.innerHTML = '';

            if (indexData.length === 0) {
                archiveList.innerHTML = '<li style="padding:10px; color:#666;">저장된 과거 뉴스가 없습니다.</li>';
                return;
            }

            indexData.forEach(month => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = '#';
                a.textContent = month.name; // e.g., "2026년 2월"
                a.dataset.id = month.id;    // e.g., "2026_02"

                a.onclick = (e) => {
                    e.preventDefault();
                    // Load specific month
                    loadArchiveMonth(month.id, month.name);

                    // Update UI active state
                    document.querySelectorAll('.sub-menu a').forEach(el => el.classList.remove('active'));
                    e.target.classList.add('active');

                    // Close mobile sidebar if open
                    const sidebar = document.getElementById('sidebar');
                    const overlay = document.getElementById('sidebar-overlay');
                    if (sidebar && sidebar.classList.contains('active')) {
                        sidebar.classList.remove('active');
                        overlay.classList.remove('active');
                    }
                };

                li.appendChild(a);
                archiveList.appendChild(li);
            });

        } catch (error) {
            console.error(error);
            archiveList.innerHTML = '<li style="padding:10px; color:#666;">불러오기 실패</li>';
        }
    }

    // Function to Load Specific Month Archive
    window.loadArchiveMonth = async function (monthId, monthName) {
        const container = document.getElementById('news-container');
        const loadMore = document.getElementById('load-more-btn');
        const chipContainer = document.querySelector('.category-filter');

        // UI Reset
        container.innerHTML = '<div class="loading">📦 아카이브를 불러오는 중입니다...</div>';
        if (loadMore) loadMore.style.display = 'none'; // Hide load more in archive mode

        // Highlight logic
        // Reset top filter chips
        if (chipContainer) {
            // Optional: maybe add a title saying "Archive: 2026 Feb"
        }

        try {
            const response = await fetch(`data/archive_${monthId}.json`);
            if (!response.ok) throw new Error("File not found");

            const data = await response.json();
            currentNewsData = data.items; // Replace global data

            // Render All
            container.innerHTML = '';
            if (!currentNewsData || currentNewsData.length === 0) {
                container.innerHTML = `<div class="loading">${monthName}에 저장된 뉴스가 없습니다.</div>`;
                return;
            }

            renderNewsItems(currentNewsData, container);

            // Add a header/notice
            const notice = document.createElement('div');
            notice.style.gridColumn = "1 / -1";
            notice.style.padding = "20px";
            notice.style.textAlign = "center";
            notice.style.color = "#94a3b8";
            notice.innerHTML = `📅 <b>${monthName}</b>의 뉴스 아카이브입니다.`;
            container.insertBefore(notice, container.firstChild);

        } catch (e) {
            container.innerHTML = `<div class="loading">아카이브 파일을 찾을 수 없습니다.<br>(${monthId})</div>`;
        }
    };
});
