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

function renderNewsItems(items, container) {
    items.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'news-card animate-slide-up';
        card.style.animationDelay = `${Math.min(index * 0.05, 1)}s`;
        card.style.cursor = 'pointer';

        const publishedDate = item.published_at || '';
        const datePart = publishedDate.split(' ')[0] || '';
        const timePart = publishedDate.split(' ')[1] ? publishedDate.split(' ')[1].substring(0, 5) : '--:--';
        const today = new Date().toISOString().split('T')[0];
        const displayTime = datePart === today ? timePart : `${datePart} ${timePart}`;

        card.innerHTML = `
            <div class="card-meta">
                <span class="category-tag">${item.category || '경제'}</span>
                <span class="time-tag">${displayTime}</span>
            </div>
            <h3>${item.title}</h3>
            <div class="summary">${item.summary || item.description || '내용을 불러오는 중...'}</div>
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
    document.getElementById('modal-source').textContent = item.source || 'Unknown';
    document.getElementById('modal-title').textContent = item.title || 'No Title';

    const content = item.content || item.description || '상세 내용을 준비 중입니다.';
    modalText.innerHTML = content.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>');

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
            modalImg.src = 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1024&auto=format&fit=crop';
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
