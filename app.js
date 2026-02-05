let currentNewsData = [];
let isArchiveLoaded = false;

async function loadNews() {
    try {
        const response = await fetch('data/news.json?t=' + new Date().getTime());
        if (!response.ok) throw new Error('데이터를 불러올 수 없습니다.');

        const data = await response.json();
        currentNewsData = data.items;

        const container = document.getElementById('news-container');
        const lastUpdated = document.getElementById('last-updated');
        const briefingSection = document.getElementById('briefing-section');
        const briefingContent = document.getElementById('briefing-content');
        const loadMoreContainer = document.getElementById('load-more-container');

        lastUpdated.textContent = `데이터 수집 시간: ${data.last_updated}`;

        if (data.briefing) {
            briefingSection.style.display = 'block';
            briefingContent.textContent = data.briefing;
        }

        container.innerHTML = '';
        renderNewsItems(data.items, container);

        // Show Load More button if we have full buffer
        if (data.items.length >= 50) {
            loadMoreContainer.style.display = 'block';
        }

    } catch (error) {
        console.error('Error:', error);
        document.getElementById('news-container').innerHTML = `
            <div class="loading">현재 리포트를 불러올 수 없습니다. GitHub Secrets 설정을 확인해 주세요.</div>
        `;
    }
}

async function loadArchive() {
    const btn = document.getElementById('load-more-btn');
    btn.textContent = '불러오는 중...';
    btn.disabled = true;

    try {
        const response = await fetch('data/news_archive.json?t=' + new Date().getTime());
        if (!response.ok) throw new Error('아카이브를 불러올 수 없습니다.');

        const data = await response.json();
        const container = document.getElementById('news-container');

        // Filter out items already shown (by title) to avoid duplication on UI
        const currentTitles = new Set(currentNewsData.map(item => item.title));
        const newItems = data.items.filter(item => !currentTitles.has(item.title));

        if (newItems.length > 0) {
            renderNewsItems(newItems, container, currentNewsData.length);
            currentNewsData = currentNewsData.concat(newItems);
            btn.style.display = 'none'; // Hide button after loading everything
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

function renderNewsItems(items, container, startIndex = 0) {
    items.forEach((item, index) => {
        const card = document.createElement('div');
        card.className = 'news-card animate-slide-up';
        card.style.animationDelay = `${(index * 0.05)}s`; // Faster animation for batch load
        card.style.cursor = 'pointer';

        // Format time (HH:mm)
        const publishedDate = item.published_at || '';
        const datePart = publishedDate.split(' ')[0] || '';
        const timePart = publishedDate.split(' ')[1] ? publishedDate.split(' ')[1].substring(0, 5) : '--:--';

        // Show date if it's an old item (simple logic: if not today, show date)
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

        // Correct index mapping for modal
        // We need the ACTUAL global index in currentNewsData, which will be updated after this render logic
        // But for onclick, we can just bind the specific object or use relative index + offset
        // Let's use flexible closure binding
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

document.addEventListener('DOMContentLoaded', () => {
    loadNews();

    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) {
        loadMoreBtn.onclick = loadArchive;
    }

    const modal = document.getElementById('news-modal');
    const closeBtn = document.querySelector('.modal-close');
    const modalImg = document.getElementById('modal-image');

    // Fallback for broken images
    modalImg.onerror = () => {
        modalImg.src = 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1024&auto=format&fit=crop';
    };

    if (closeBtn) closeBtn.onclick = closeModal;
    window.onclick = (event) => {
        if (event.target == modal) closeModal();
    };
});
