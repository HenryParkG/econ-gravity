import feedparser
import json
import os
from google import genai
from datetime import datetime, timezone, timedelta
import random
import re
import time

def fetch_economic_news():
    # Google News RSS for "경제" (Economy) in Korean
    rss_url = "https://news.google.com/rss/search?q=경제&hl=ko&gl=KR&ceid=KR:ko"
    
    print(f"Fetching raw news from: {rss_url}")
    feed = feedparser.parse(rss_url)
    
    raw_news = []
    # Get top 20 news to feed into Gemini
    for entry in feed.entries[:20]:
        raw_news.append({
            "title": entry.title,
            "link": entry.link,
            "source": entry.get('source', {}).get('title', 'Unknown')
        })

    # Gemini API Integration
    api_key = os.environ.get("GEMINI_API_KEY")
    briefing = "오늘의 주요 경제 뉴스를 분석 중입니다."
    final_news = []
    
    if not api_key:
        print("Warning: GEMINI_API_KEY not found. Using raw news fallback.")
        final_news = raw_news[:5]
        for item in final_news:
            item["summary"] = "AI 요약을 사용하려면 GEMINI_API_KEY를 등록해 주세요."
            item["content"] = "GitHub 레포지토리의 Secrets에 GEMINI_API_KEY가 등록되지 않았습니다."
            item["image_prompt"] = "Economy business news"
    else:
        try:
            # Using the new google-genai SDK
            client = genai.Client(api_key=api_key)
            
            prompt = f"""
            다음은 오늘 수집된 주요 경제 뉴스 목록입니다:
            {json.dumps(raw_news, ensure_ascii=False)}
            
            1. 위 기사들을 종합하여 오늘의 경제 흐름을 보여주는 '오늘의 한 줄 브리핑(briefing)'을 2~3문장으로 작성해줘.
            2. 가장 중요도가 높은 뉴스 5개를 엄선해서 'items' 목록으로 정리해줘.
            3. 각 뉴스 아이템은 상세하고 알찬 기사 내용(content)으로 재구성해줘. (최소 3~4문단 이상)
            4. 각 뉴스의 주제와 분위기를 나타내는 3~5개의 구체적인 영어 키워드(image_prompt)를 작성해줘. (예: 'Stock market, dynamic graph, blue neon, professional')
            
            반드시 다음과 같은 JSON 형식으로만 응답해줘.
            형식:
            {{
                "briefing": "오늘의 전체적인 경제 흐름 요약",
                "items": [
                    {{
                        "title": "뉴스 제목",
                        "source": "출처",
                        "category": "카테고리 (예: 금융, 테크, 시장, 정책 등 2~4글자)",
                        "summary": "짧은 요약",
                        "content": "상세 리포트 내용",
                        "image_prompt": "Clean English Keywords"
                    }}
                ]
            }}
            """
            
            # Failover logic: Try Gemini 3 first, then fallback
            models_to_try = [
                'gemini-3-flash-preview', 
                'gemini-3-pro-preview', 
                'gemini-2.0-flash', 
                'gemini-1.5-pro', 
                'gemini-1.5-flash', 
                'gemini-1.5-flash-8b'
            ]
            success = False
            
            for model_name in models_to_try:
                try:
                    print(f"Attempting news synthesis with {model_name}...")
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt
                    )
                    content = response.text.replace('```json', '').replace('```', '').strip()
                    result = json.loads(content)
                    
                    briefing = result.get("briefing", "오늘의 경제 동향을 분석 중입니다.")
                    final_news = result.get("items", [])
                    success = True
                    print(f"Successfully synthesized news using {model_name}.")
                    break
                except Exception as model_err:
                    print(f"Model {model_name} failed: {model_err}")
                    if "503" in str(model_err) or "overloaded" in str(model_err).lower():
                        print("Server overloaded, waiting 2 seconds before next model...")
                        time.sleep(2)
                    continue
            
            if not success:
                raise Exception("All attempted AI models failed or were overloaded.")
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            print("Using raw news fallback.")
            briefing = "AI 브리핑을 생성하는 중 오류가 발생했습니다. API 설정을 확인해 주세요."
            final_news = raw_news[:5]
            for item in final_news:
                item["summary"] = "내용 요약을 불러올 수 없습니다."
                item["content"] = f"### AI 리포트 생성 오류\n\n오류 상세: {str(e)}"
                item["image_prompt"] = "Global Economy Technology"

    # --- GLOBAL DATA ACCUMULATION & IMAGE REGENERATION ---
    
    # KST (UTC+9) adjustment
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(timezone.utc).astimezone(kst)
    timestamp = now_kst.strftime("%Y-%m-%d %H:%M:%S")

    # Load existing news
    news_file = 'data/news.json'
    existing_items = []
    if os.path.exists(news_file):
        try:
            with open(news_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                existing_items = old_data.get('items', [])
        except Exception as e:
            print(f"Error loading existing news: {e}")

    # Add timestamp to new items
    for item in final_news:
        item["published_at"] = timestamp

    # Merge and remove duplicates (by title)
    seen_titles = set()
    merged_items = []
    
    # Add new items first (keep newest at top)
    for item in final_news:
        if item['title'] not in seen_titles:
            merged_items.append(item)
            seen_titles.add(item['title'])
            
    # Add old items
    for item in existing_items:
        if item['title'] not in seen_titles:
            merged_items.append(item)
            seen_titles.add(item['title'])

    # DB Management: Keep exactly 1000 items (Rolling buffer)
    # The user requested 'over 50' and 'accumulate continuously', so 1000 is a safe long-term buffer.
    merged_items = merged_items[:1000]

    # RE-GENERATE IMAGES FOR ALL ITEMS
    print(f"Regenerating images for {len(merged_items)} items...")
    
    # EMERGENCY FALLBACK: Pre-curated High-Quality Unsplash Images
    # Guaranteed to work, no API generation failures.
    stock_images = [
        "https://images.unsplash.com/photo-1611974714028-ac8a49f70659?q=80&w=1024&auto=format&fit=crop", # Stock Chart
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?q=80&w=1024&auto=format&fit=crop", # Stock Ticker
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=1024&auto=format&fit=crop", # Data Screen
        "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1024&auto=format&fit=crop", # Chip
        "https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1024&auto=format&fit=crop", # Laptop Graph
        "https://images.unsplash.com/photo-1579532507581-c9817e27ca0f?q=80&w=1024&auto=format&fit=crop", # Money
        "https://images.unsplash.com/photo-1526304640152-d4619684e484?q=80&w=1024&auto=format&fit=crop", # Bitcoin
        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1024&auto=format&fit=crop", # Abstract News
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1024&auto=format&fit=crop", # Skyscraper
        "https://images.unsplash.com/photo-1519389950473-47ba0277781c?q=80&w=1024&auto=format&fit=crop", # Teamwork
        "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?q=80&w=1024&auto=format&fit=crop", # Meeting
        "https://images.unsplash.com/photo-1554224155-273a743008a3?q=80&w=1024&auto=format&fit=crop", # Handshake
        "https://images.unsplash.com/photo-1553729459-efe14ef6055d?q=80&w=1024&auto=format&fit=crop", # Money Hands
        "https://images.unsplash.com/photo-1621370216442-de7e83464166?q=80&w=1024&auto=format&fit=crop", # Crypto Art
        "https://images.unsplash.com/photo-1516245834210-c4c14278733f?q=80&w=1024&auto=format&fit=crop", # Blockchain
        "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?q=80&w=1024&auto=format&fit=crop", # Bitcoin Gold
        "https://images.unsplash.com/photo-1535320903710-d9cf98bbb531?q=80&w=1024&auto=format&fit=crop", # Oil Rig
        "https://images.unsplash.com/photo-1504639725590-34d0984388bd?q=80&w=1024&auto=format&fit=crop", # Code Screen
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1024&auto=format&fit=crop", # Globe
        "https://images.unsplash.com/photo-1512756290469-ec264b7fbf87?q=80&w=1024&auto=format&fit=crop", # Laptop
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?q=80&w=1024&auto=format&fit=crop", # Digital Art
        "https://images.unsplash.com/photo-1478131313025-a1c1d7cc90b8?q=80&w=1024&auto=format&fit=crop", # Luxury Car
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?q=80&w=1024&auto=format&fit=crop", # Analysis
        "https://images.unsplash.com/photo-1523961131990-5ea7c61b2107?q=80&w=1024&auto=format&fit=crop", # Data Cloud
        "https://images.unsplash.com/photo-1642543492481-44e81e3914a7?q=80&w=1024&auto=format&fit=crop", # Ethereum
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=1024&auto=format&fit=crop", # NFT
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=1024&auto=format&fit=crop", # Cyberpunk
        "https://images.unsplash.com/photo-1487058792275-0ad4aaf24ca7?q=80&w=1024&auto=format&fit=crop", # Code Matrix
        "https://images.unsplash.com/photo-1561414927-6d86591d0c4f?q=80&w=1024&auto=format&fit=crop", # Money Stack
        "https://images.unsplash.com/photo-1605792657660-596af9009e82?q=80&w=1024&auto=format&fit=crop"  # Stock App
    ]
    
    import random
    import time
    
    for i, item in enumerate(merged_items):
        try:
            # Randomly select a high-quality stock image
            # Use 'i' to ensure adjacent items likely get different images if list > len
            selected_image = stock_images[i % len(stock_images)]
            
            # Shuffle slightly for variety across updates
            if i >= len(stock_images):
                selected_image = random.choice(stock_images)
            
            item["image_url"] = selected_image
            
        except Exception as img_err:
            item["image_url"] = "https://images.unsplash.com/photo-1611974714028-ac8a49f70659?q=80&w=1024&auto=format&fit=crop"

    data = {
        "last_updated": timestamp,
        "briefing": briefing,
        "items": merged_items
    }
    
    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"Successfully saved {len(merged_items)} news items to data/news.json")

if __name__ == "__main__":
    fetch_economic_news()
