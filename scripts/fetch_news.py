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
    if not api_key:
        print("Warning: GEMINI_API_KEY not found. Using raw news fallback.")
        final_news = raw_news[:10]
    else:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""
            다음은 오늘 수집된 주요 경제 뉴스 목록입니다:
            {json.dumps(raw_news, ensure_ascii=False)}
            
            이 중에서 가장 중요하고 사람들의 관심이 높을만한 뉴스 5개를 엄선해서 정리해줘.
            반드시 다음과 같은 JSON 형식으로만 응답해줘. 다른 말은 하지 마.
            형식:
            {{
                "items": [
                    {{
                        "title": "뉴스 제목",
                        "link": "원문 링크",
                        "source": "출처",
                        "description": "뉴스 핵심 내용 1~2문장 요약 (한국어)"
                    }},
                    ...
                ]
            }}
            """
            
            response = model.generate_content(prompt)
            # Remove markdown code blocks if present
            content = response.text.replace('```json', '').replace('```', '').strip()
            final_news = json.loads(content)["items"]
            print(f"Successfully curated 5 news items using Gemini API.")
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}. Using raw news fallback.")
            final_news = raw_news[:5]
            for item in final_news:
                item["description"] = "내용 요약을 불러올 수 없습니다."

    data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
