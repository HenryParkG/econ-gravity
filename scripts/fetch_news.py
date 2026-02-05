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

    # Keep exactly 1000 items
    merged_items = merged_items[:1000]

    # RE-GENERATE IMAGES FOR ALL ITEMS
    print(f"Regenerating images for {len(merged_items)} items...")
    
    # Safe, diverse visual themes to guarantee no fallback images
    safe_themes = [
        "Futuristic Financial District at Night", "Glowing Blue Stock Market Graph", "Abstract Digital Network Connections", 
        "Gold Bars and Silver Coins", "High Tech Server Room aesthetic", "Global World Map with Data Lines", 
        "Modern Glass Skyscraper Low Angle", "Cyberpunk City Street with Neon Lights", "Minimalist White Business Desk", 
        "Blue Architectural Blueprint Schematics", "Busy Shipping Container Port Aerial View", "Electric Vehicle Charging Station", 
        "Green Energy Wind Turbines on a Hill", "Robotic Arm Assembly Line", "Artificial Intelligence Digital Brain",
        "Bitcoin and Cryptocurrency Coins", "Abstract Geometric 3D Shapes", "Stock Exchange Trading Floor Blur",
        "Rocket Launching into Space", "Drone Delivering Package", "Smart City Traffic Lights",
        "VR Headset Man Using Interface", "Microchip Processor Macro Shot", "Solar Panels on Roof",
        "Hydroponic Future Farm", "Molecular Structure Science", "DNA Helix Glowing",
        "Cyber Security Padlock Concept", "Cloud Computing Data Center", "5G Network Tower",
        "Smart Watch Wearable Tech", "Autonomous Self Driving Car", "Industrial Factory Smoke Stacks",
        "Oil Rig in Ocean at Sunset", "Construction Crane Silhouette", "Luxury Private Jet Interior",
        "Yacht on Blue Ocean", "Golden Bull Statue Wall Street", "Hourglass with Sand Falling",
        "Chess Board Strategy Game", "Puzzle Pieces Fitting Together", "Lightbulb Innovation Idea",
        "Magnifying Glass Analyzing Data", "Calculator and Financial Papers", "Credit Card Chip Macro",
        "Shopping Cart filled with boxes", "Bar Chart Rising Upwards", "Pie Chart Interface",
        "Globe Spinning in Space", "Network Server Cables", "Keyboard with RGB Lighting"
    ]
    
    import random
    import time
    
    for i, item in enumerate(merged_items):
        try:
            # Randomly select a safe theme
            selected_theme = random.choice(safe_themes)
            
            # Dynamic seed + style
            dynamic_seed = random.randint(1, 9999999) + i
            
            # Timestamp to bust cache
            ts = int(time.time())
            
            # Use 'flux' model with nologo
            encoded_prompt = selected_theme.replace(" ", "%20")
            item["image_url"] = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=576&seed={dynamic_seed}&model=flux&nologo=true&enhance=true&t={ts}-{i}"
            
        except Exception as img_err:
            # Absolute fallback
            item["image_url"] = f"https://pollinations.ai/p/abstract%20digital%20art?width=1024&height=576&seed={i}&nologo=true"

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
