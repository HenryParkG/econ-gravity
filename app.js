async function loadNews() {
    try {
        const response = await fetch('data/news.json');
        if (!response.ok) throw new Error('News data not found');
        
        const data = await response.json();
        const container = document.getElementById('news-container');
        const lastUpdated = document.getElementById('last-updated');
        
        lastUpdated.textContent = `마지막 업데이트: ${data.last_updated}`;
        
        container.innerHTML = '';
        data.items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'news-card';
            card.innerHTML = `
                <a href="${item.link}" target="_blank">
                    <h3>${item.title}</h3>
                    <div class="meta">${item.pubDate} | ${item.source}</div>
                    <div class="summary">${item.description}</div>
                </a>
            `;
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading news:', error);
        document.getElementById('news-container').innerHTML = `
            <div class="loading">뉴스를 불러오는 데 실패했습니다. 잠시 후 다시 시도해 주세요.</div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', loadNews);
