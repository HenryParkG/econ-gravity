import feedparser
import json
import os
from google import genai
from datetime import datetime, timezone, timedelta
import random
import re
import time
import yfinance as yf

def fetch_market_indices():
    """
    Fetches key market indices using yfinance.
    Returns a list of dicts: [{'name': 'KOSPI', 'value': '2,500.12', 'change': '+1.2%'}]
    """
    print("Fetching market indices...")
    tickers = {
        'KOSPI': '^KS11',
        'KOSDAQ': '^KQ11',
        'USD/KRW': 'KRW=X',
        'NASDAQ': '^IXIC',
        'S&P 500': '^GSPC'
        # 'Bitcoin': 'BTC-USD'
    }
    
    indices_data = []
    
    for name, symbol in tickers.items():
        try:
            ticker = yf.Ticker(symbol)
            # Get fast info
            info = ticker.fast_info
            
            # fast_info might not have everything, fallback to history
            current_price = 0.0
            previous_close = 0.0
            
            # yfinance approach for indices often works best with history
            hist = ticker.history(period="5d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
                # If market is open, last price. If closed, still last price.
                # To get change, we need previous close.
                if len(hist) >= 2:
                    previous_close = hist['Close'].iloc[-2]
                else: 
                     previous_close = current_price # No history means 0 change
            
            # For currency, logic is similar
            
            if current_price == 0:
                 continue
                 
            # Calculate Change
            change_val = float(current_price - previous_close)
            change_pct = float((change_val / previous_close) * 100)
            
            # Formatting
            sign = ""
            if change_val > 0: sign = "▲"
            elif change_val < 0: sign = "▼"
            else: sign = "-"
            
            formatted_price = f"{current_price:,.2f}"
            formatted_change = f"{sign} {abs(change_pct):.2f}%"
            
            indices_data.append({
                "name": name,
                "value": formatted_price,
                "change": formatted_change,
                "is_up": bool(change_val > 0),
                "is_down": bool(change_val < 0)
            })
            
        except Exception as e:
            print(f"Failed to fetch {name}: {e}")
            continue
            
    return indices_data

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

    # Load existing ARCHIVE news (The Master Database)
    archive_file = 'data/news_archive.json'
    existing_items = []
    
    # 1. Try to load from Archive first
    if os.path.exists(archive_file):
        try:
            with open(archive_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                existing_items = old_data.get('items', [])
        except Exception as e:
            print(f"Error loading archive news: {e}")
    # 2. Migration: If no archive, try loading from old news.json to migrate data
    elif os.path.exists('data/news.json'):
         try:
            with open('data/news.json', 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                existing_items = old_data.get('items', [])
            print("Migrating existing news.json to archive...")
         except Exception as e:
            print(f"Error loading migration news: {e}")

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

    # DB Management: Archive holds EVERYTHING (or cap at 5000 for sanity)
    # merged_items now contains ALL history + New items
    full_archive_items = merged_items[:5000] 

    # RE-GENERATE IMAGES FOR ALL ITEMS
    # Important: We apply distinct images to ALL items in the archive to ensure visual variety
    print(f"Regenerating images for {len(full_archive_items)} items...")
    
    # EMERGENCY FALLBACK: Pre-curated High-Quality Unsplash Images (Expanded 60+)
    stock_images = [
        # --- Finance & Stock Market ---
        "https://images.unsplash.com/photo-1611974714028-ac8a49f70659?q=80&w=1024&auto=format&fit=crop", # Stock Chart
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?q=80&w=1024&auto=format&fit=crop", # Ticker
        "https://images.unsplash.com/photo-1579532507581-c9817e27ca0f?q=80&w=1024&auto=format&fit=crop", # Money
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=1024&auto=format&fit=crop", # Data Screen
        "https://images.unsplash.com/photo-1553729459-efe14ef6055d?q=80&w=1024&auto=format&fit=crop", # Money Hands
        "https://images.unsplash.com/photo-1561414927-6d86591d0c4f?q=80&w=1024&auto=format&fit=crop", # Cash Stack
        "https://images.unsplash.com/photo-1605792657660-596af9009e82?q=80&w=1024&auto=format&fit=crop", # Investing App
        "https://images.unsplash.com/photo-1535320903710-d9cf98bbb531?q=80&w=1024&auto=format&fit=crop", # Oil & Commodities
        "https://images.unsplash.com/photo-1526304640152-d4619684e484?q=80&w=1024&auto=format&fit=crop", # Bitcoin Concept
        "https://images.unsplash.com/photo-1518186285589-2f7649de83e0?q=80&w=1024&auto=format&fit=crop", # Currency
        
        # --- Business & Corporate ---
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1024&auto=format&fit=crop", # Skyscraper
        "https://images.unsplash.com/photo-1507679799987-c73779587ccf?q=80&w=1024&auto=format&fit=crop", # Business Suit
        "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?q=80&w=1024&auto=format&fit=crop", # Meeting
        "https://images.unsplash.com/photo-1554224155-273a743008a3?q=80&w=1024&auto=format&fit=crop", # Handshake
        "https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=1024&auto=format&fit=crop", # Modern Office
        "https://images.unsplash.com/photo-1497215728101-856f4ea42174?q=80&w=1024&auto=format&fit=crop", # Office Work
        
        # --- Tech & Innovation ---
        "https://images.unsplash.com/photo-1451187580459-43490279c0fa?q=80&w=1024&auto=format&fit=crop", # Global Network
        "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1024&auto=format&fit=crop", # AI Chip
        "https://images.unsplash.com/photo-1504639725590-34d0984388bd?q=80&w=1024&auto=format&fit=crop", # Coding
        "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?q=80&w=1024&auto=format&fit=crop", # Robot AI
        "https://images.unsplash.com/photo-1531297461136-820727183187?q=80&w=1024&auto=format&fit=crop", # Data Server
        "https://images.unsplash.com/photo-1523961131990-5ea7c61b2107?q=80&w=1024&auto=format&fit=crop", # Analytics
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?q=80&w=1024&auto=format&fit=crop", # Cybersecurity
        
        # --- Real Estate & Construction ---
        "https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1024&auto=format&fit=crop", # Real Estate
        "https://images.unsplash.com/photo-1448630360428-65456885c650?q=80&w=1024&auto=format&fit=crop", # Modern Home
        "https://images.unsplash.com/photo-1582407947304-fd86f028f716?q=80&w=1024&auto=format&fit=crop", # Construction
        "https://images.unsplash.com/photo-1479839672679-a46483c0e7c8?q=80&w=1024&auto=format&fit=crop", # City Building
        
        # --- Global Trade & Logistics ---
        "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?q=80&w=1024&auto=format&fit=crop", # Cargo Ship
        "https://images.unsplash.com/photo-1494412574643-35d324698420?q=80&w=1024&auto=format&fit=crop", # Shipping Containers
        "https://images.unsplash.com/photo-1578575437130-527eed3abbec?q=80&w=1024&auto=format&fit=crop", # Logistics Plane
        
        # --- Lifestyle & Consumption ---
        "https://images.unsplash.com/photo-1559526324-4b87b5e36e44?q=80&w=1024&auto=format&fit=crop", # Shopping/Analysis
        "https://images.unsplash.com/photo-1478131313025-a1c1d7cc90b8?q=80&w=1024&auto=format&fit=crop", # Luxury Car
        "https://images.unsplash.com/photo-1556740738-b6a63e27c4df?q=80&w=1024&auto=format&fit=crop", # Payment
        
        # --- Abstract & Artistic ---
        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?q=80&w=1024&auto=format&fit=crop", # News
        "https://images.unsplash.com/photo-1491895200222-0fc4a4c35e18?q=80&w=1024&auto=format&fit=crop", # Texture
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?q=80&w=1024&auto=format&fit=crop", # Working
        "https://images.unsplash.com/photo-1563986768609-322da13575f3?q=80&w=1024&auto=format&fit=crop", # Digital Blue
        
        # --- Additional Variety ---
        "https://images.unsplash.com/photo-1565514020176-dbf2277cc166?q=80&w=1024&auto=format&fit=crop", # Graph
        "https://images.unsplash.com/photo-1642543492481-44e81e3914a7?q=80&w=1024&auto=format&fit=crop", # Ethereum
        "https://images.unsplash.com/photo-1621370216442-de7e83464166?q=80&w=1024&auto=format&fit=crop", # NFT Art
        "https://images.unsplash.com/photo-1516245834210-c4c14278733f?q=80&w=1024&auto=format&fit=crop", # Chains
        "https://images.unsplash.com/photo-1550565118-c974fb6255f0?q=80&w=1024&auto=format&fit=crop", # Network
        "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?q=80&w=1024&auto=format&fit=crop", # Stock Chart (Safe Substitute for broken link)
        "https://images.unsplash.com/photo-1531297461136-820727183187?q=80&w=1024&auto=format&fit=crop", # Data Server Substitute
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1024&auto=format&fit=crop", # Skyscraper Substitute
        "https://images.unsplash.com/photo-1593642702821-c8da6771f0c6?q=80&w=1024&auto=format&fit=crop", # Desk (Keep if safe, but replacing to be sure) -> Replaced with Building
        "https://images.unsplash.com/photo-1560518883-ce09059eeffa?q=80&w=1024&auto=format&fit=crop", # Real Estate Substitute
        "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?q=80&w=1024&auto=format&fit=crop", # Happy Team
        "https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=1024&auto=format&fit=crop", # Office Work Substitute
        "https://images.unsplash.com/photo-1664575602276-acd073f104c1?q=80&w=1024&auto=format&fit=crop", # Metaverse
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?q=80&w=1024&auto=format&fit=crop", # AI Brain
        "https://images.unsplash.com/photo-1633158829585-23ba8f7c8caf?q=80&w=1024&auto=format&fit=crop", # Bitcoin Ripple
        "https://images.unsplash.com/photo-1614028674026-a65e31bfd27c?q=80&w=1024&auto=format&fit=crop", # Stock Green
        "https://images.unsplash.com/photo-1534951009808-766178b47a8e?q=80&w=1024&auto=format&fit=crop", # Financial Newspaper
        "https://images.unsplash.com/photo-1560221328-12fe60f83ab8?q=80&w=1024&auto=format&fit=crop", # Sales Graph
        "https://images.unsplash.com/photo-1579532507581-c9817e27ca0f?q=80&w=1024&auto=format&fit=crop", # Cash
        "https://images.unsplash.com/photo-1580048914979-3c868daee4d7?q=80&w=1024&auto=format&fit=crop", # House Model
    ]
    
    # Imports removed to fix UnboundLocalError (global imports used)
    
    for i, item in enumerate(full_archive_items):
        try:
            # Consistent image mapping per item index to avoid shuffling on every build if desired,
            # or random every time. Given the history issue, let's keep it robust.
            # Using 'i' to ensure variety.
            selected_image = stock_images[i % len(stock_images)]
            
            # Simple fallback for image uniqueness in long list
            if i >= len(stock_images):
                # Offset by index to create 'pseudo-random' but deterministic per build
                rotated_index = (i + 7) % len(stock_images) 
                selected_image = stock_images[rotated_index]
            
            item["image_url"] = selected_image
            
        except Exception as img_err:
            item["image_url"] = "https://images.unsplash.com/photo-1611974714028-ac8a49f70659?q=80&w=1024&auto=format&fit=crop"

    # --- ARCHIVING LOGIC (Monthly Migration) ---
    # Move items older than 30 days to separate monthly files
    # This prevents news_archive.json from growing infinitely
    
    current_time = datetime.now()
    cutoff_date = current_time - timedelta(days=30)
    
    active_archive_items = []
    monthly_migration_buffer = {} # { "2024_02": [items], "2024_01": [items] }
    
    print(f"Checking for items older than {cutoff_date.strftime('%Y-%m-%d')} for archiving...")
    
    for item in full_archive_items:
        try:
            # Parse published_at (format: "YYYY-MM-DD HH:MM:SS")
            # If format fails, keep in active archive to be safe
            p_date_str = item.get("published_at", "")
            p_date = datetime.strptime(p_date_str, "%Y-%m-%d %H:%M:%S")
            
            if p_date < cutoff_date:
                # To be archived
                month_key = p_date.strftime("%Y_%m") # e.g., "2024_02"
                if month_key not in monthly_migration_buffer:
                    monthly_migration_buffer[month_key] = []
                monthly_migration_buffer[month_key].append(item)
            else:
                # Keep in active archive
                active_archive_items.append(item)
                
        except Exception as e:
            # Date parsing error or other issue -> Keep in active
            active_archive_items.append(item)
            
    # Process Migration Buffer
    for month_key, items_to_move in monthly_migration_buffer.items():
        if not items_to_move:
            continue
            
        archive_filename = f'data/archive_{month_key}.json'
        # Load existing if any
        existing_monthly_items = []
        if os.path.exists(archive_filename):
            try:
                with open(archive_filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    existing_monthly_items = data.get('items', [])
            except:
                pass
        
        # Merge and Deduplicate
        # (Though technically old items shouldn't overlap much with *existing* monthly archive unless re-run)
        # Using dictionary for deduplication by title
        archive_map = {itm['title']: itm for itm in existing_monthly_items}
        for itm in items_to_move:
            archive_map[itm['title']] = itm
            
        final_monthly_items = list(archive_map.values())
        
        # Sort by date (descending)
        try:
            final_monthly_items.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        except:
            pass
            
        print(f"  -> Moving {len(items_to_move)} items to {archive_filename}")
        
        with open(archive_filename, 'w', encoding='utf-8') as f:
            json.dump({
                "last_updated": timestamp,
                "items": final_monthly_items
            }, f, ensure_ascii=False, indent=4)

    # Update full_archive_items to only contain active items
    print(f"Archiving complete. Active Archive size: {len(full_archive_items)} -> {len(active_archive_items)}")
    full_archive_items = active_archive_items

    # --- SAVE FILES ---
    os.makedirs('data', exist_ok=True)

    # 1. Save Archive (Active History - Last 30 Days)
    archive_data = {
        "last_updated": timestamp,
        "briefing": briefing,
        "items": full_archive_items
    }
    with open('data/news_archive.json', 'w', encoding='utf-8') as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=4)
        
    # 1.5 Fetch Market Indices
    market_indices = fetch_market_indices()

    # 2. Save Active Feed (Top 50 Only)
    # This keeps the main site loading very fast
    active_data = {
        "last_updated": timestamp,
        "briefing": briefing,
        "indices": market_indices, # New field
        "items": full_archive_items[:50]
    }
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(active_data, f, ensure_ascii=False, indent=4)
    
    print(f"Successfully saved {len(full_archive_items)} items to Archive and 50 to Active feed.")

    # 3. Generate Archive Index for Frontend
    print("Generating archive index...")
    # List all archive_YYYY_MM.json files
    archive_files = [f for f in os.listdir('data') if f.startswith('archive_') and f.endswith('.json') and f != 'archive_index.json']
    
    archive_index = []
    for f in archive_files:
        # Expected format: archive_2024_02.json
        try:
            # Remove prefix/suffix
            base = f.replace('archive_', '').replace('.json', '')
            parts = base.split('_')
            if len(parts) == 2:
                year, month = parts
                archive_index.append({
                    "id": f"{year}_{month}",      # ID used for fetching file
                    "name": f"{year}년 {month}월", # Display Name
                    "filename": f
                })
        except Exception as e:
            print(f"Skipping malformed archive file: {f}")
            continue
            
    # Sort by ID descending (newest month first)
    archive_index.sort(key=lambda x: x['id'], reverse=True)
    
    with open('data/archive_index.json', 'w', encoding='utf-8') as f:
        json.dump(archive_index, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    fetch_economic_news()
