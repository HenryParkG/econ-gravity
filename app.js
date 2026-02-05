let currentNewsData = [];

async function loadNews() {
    try {
        const response = await fetch('data/news.json');
        if (!response.ok) throw new Error('데이터를 불러올 수 없습니다.');

        const data = await response.json();
        currentNewsData = data.items;

        const container = document.getElementById('news-container');
        const lastUpdated = document.getElementById('last-updated');
        const briefingSection = document.getElementById('briefing-section');
        const briefingContent = document.getElementById('briefing-content');

        lastUpdated.textContent = `데이터 수집 시간: ${data.last_updated}`;

        if (data.briefing) {
            briefingSection.style.display = 'block';
            briefingContent.textContent = data.briefing;
        }

        container.innerHTML = '';
        data.items.forEach((item, index) => {
            const card = document.createElement('div');
            card.className = 'news-card animate-slide-up';
            card.style.animationDelay = `${index * 0.1}s`;
            card.style.cursor = 'pointer';

            card.innerHTML = `
                <span class="source-tag">${item.source}</span>
                <h3>${item.title}</h3>
                <div class="summary">${item.summary}</div>
            `;

            card.onclick = () => openModal(index);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error:', error);
        document.getElementById('news-container').innerHTML = `
            <div class="loading">현재 리포트를 불러올 수 없습니다. GitHub Secrets 설정을 확인해 주세요.</div>
        `;
    }
}

function openModal(index) {
    const item = currentNewsData[index];
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

    const modal = document.getElementById('news-modal');
    const closeBtn = document.querySelector('.modal-close');

    if (closeBtn) closeBtn.onclick = closeModal;
    window.onclick = (event) => {
        if (event.target == modal) closeModal();
    };
});
