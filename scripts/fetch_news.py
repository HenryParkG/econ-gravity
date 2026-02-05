import feedparser
import json
import os
import google.generativeai as genai
from datetime import datetime

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
    
    if not api_key:
        print("Warning: GEMINI_API_KEY not found. Using raw news fallback.")
        final_news = raw_news[:5]
        for item in final_news:
            item["summary"] = "AI 요약을 사용하려면 GEMINI_API_KEY를 등록해 주세요."
            item["content"] = "GitHub 레포지토리의 Secrets에 GEMINI_API_KEY가 등록되지 않았습니다. API 키를 등록하면 AI가 기사를 분석하여 이 자리에 심층 리포트를 작성해 드립니다."
            item["image_url"] = "https://images.unsplash.com/photo-1611974714028-ac8a49f70659?q=80&w=1024&auto=format&fit=crop"
    else:
        try:
# ... (rest of the try/except logic)
            response = model.generate_content(prompt)
            content = response.text.replace('```json', '').replace('```', '').strip()
            result = json.loads(content)
            
            briefing = result.get("briefing", "오늘의 경제 동향을 분석 중입니다.")
            final_news = result.get("items", [])
            
            # Add image URL generation using Pollinations API
            for item in final_news:
                img_prompt = item.get("image_prompt", "Business economy digital art").replace(" ", "%20")
                item["image_url"] = f"https://pollinations.ai/p/{img_prompt}?width=1024&height=576&seed=42&model=flux&nologo=true"

            print(f"Successfully synthesized deep reports and generated AI images.")
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}. Using raw news fallback.")
            briefing = "AI 브리핑을 생성하는 중 오류가 발생했습니다."
            final_news = raw_news[:5]
            for item in final_news:
                item["summary"] = "내용 요약을 불러올 수 없습니다."
                item["content"] = f"AI 리포트 생성 중 오류가 발생했습니다: {str(e)}"
                item["image_url"] = "https://images.unsplash.com/photo-1611974714028-ac8a49f70659?q=80&w=1024&auto=format&fit=crop"

    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "briefing": briefing,
        "items": final_news
    }
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Save to JSON
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"Successfully saved {len(final_news)} news items to data/news.json")

if __name__ == "__main__":
    fetch_economic_news()
