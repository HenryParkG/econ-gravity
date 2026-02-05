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
            
            1. 위 기사들을 종합하여 오늘의 경제 흐름을 보여주는 '오늘의 한 줄 브리핑(briefing)'을 2~3문장으로 작성해줘.
            2. 가장 중요도가 높은 뉴스 5개를 엄선해서 'items' 목록으로 정리해줘.
            3. 각 뉴스 아이템은 단순 요약이 아니라, 전문 경제 뉴스 리포터가 작성한 것처럼 상세하고 알찬 기사 내용(content)으로 재구성해줘. (최소 3~4문단 이상)
            4. 각 뉴스의 주제를 잘 나타내는 AI 이미지 생성을 위한 영어 프롬프트(image_prompt)를 1문장의 영어로 작성해줘.
            
            반드시 다음과 같은 JSON 형식으로만 응답해줘. 다른 말은 절대 하지 마.
            형식:
            {{
                "briefing": "오늘의 전체적인 경제 흐름 요약 및 브리핑",
                "items": [
                    {{
                        "title": "뉴스 제목 (마치 개별 기사처럼 매력적으로 작성)",
                        "source": "출처 (원문 출처 표기)",
                        "summary": "목록에서 보여줄 짧은 요약 (1~2문장)",
                        "content": "AI가 재구성한 상세 리포트 내용 (markdown 형식 사용 가능)",
                        "image_prompt": "An artistic and clean digital illustration about [topic], high quality, financial aesthetic, 16:9"
                    }},
                    ...
                ]
            }}
            """
            
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
                item["description"] = "내용 요약을 불러올 수 없습니다."

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
