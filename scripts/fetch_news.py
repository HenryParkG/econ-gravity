import feedparser
import json
import os
from google import genai
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
    final_news = []
    
    if not api_key:
        print("Warning: GEMINI_API_KEY not found. Using raw news fallback.")
        final_news = raw_news[:5]
        for item in final_news:
            item["summary"] = "AI 요약을 사용하려면 GEMINI_API_KEY를 등록해 주세요."
            item["content"] = "GitHub 레포지토리의 Secrets에 GEMINI_API_KEY가 등록되지 않았습니다. API 키를 등록하면 AI가 기사를 분석하여 이 자리에 심층 리포트를 작성해 드립니다."
            item["image_url"] = "https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1024&auto=format&fit=crop"
    else:
        try:
            # Using the new google-genai SDK as per documentation
            client = genai.Client(api_key=api_key)
            
            prompt = f"""
            다음은 오늘 수집된 주요 경제 뉴스 목록입니다:
            {json.dumps(raw_news, ensure_ascii=False)}
            
            1. 위 기사들을 종합하여 오늘의 경제 흐름을 보여주는 '오늘의 한 줄 브리핑(briefing)'을 2~3문장으로 작성해줘.
            2. 가장 중요도가 높은 뉴스 5개를 엄선해서 'items' 목록으로 정리해줘.
            3. 각 뉴스 아이템은 단순 요약이 아니라, 전문 경제 뉴스 리포터가 작성한 것처럼 상세하고 알찬 기사 내용(content)으로 재구성해줘. (최소 3~4문단 이상)
            4. 각 뉴스의 주제와 분위기를 나타내는 3~5개의 구체적인 영어 키워드(image_prompt)를 작성해줘. (예: 'Stock market, dynamic graph, blue neon, professional')
            
            반드시 다음과 같은 JSON 형식으로만 응답해줘. 다른 말은 절대 하지 마.
            형식:
            {{
                "briefing": "오늘의 전체적인 경제 흐름 요약 및 브리핑",
                "items": [
                    {{
                        "title": "뉴스 제목 (마치 개별 기사처럼 매력적으로 작성)",
                        "source": "출처 (원문 출처 표기)",
                        "category": "카테고리 (예: 금융, 테크, 시장, 정책 등 2~4글자)",
                        "summary": "목록에서 보여줄 짧은 요약 (1~2문장)",
                        "content": "AI가 재구성한 상세 리포트 내용 (markdown 형식 사용 가능)",
                        "image_prompt": "An artistic and clean digital illustration about [topic], high quality, financial aesthetic, 16:9"
                    }},
                    ...
                ]
            }}
            """
            
            # Failover logic: Try Gemini 3 first, then fallback to 2.0 or 1.5 if overloaded
            models_to_try = ['gemini-3-flash-preview', 'gemini-2.0-flash', 'gemini-1.5-flash']
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
                    continue
            
            if not success:
                raise Exception("All attempted AI models failed or were overloaded.")
            
            # Add image URL generation using Pollinations API
            import random
            import re
            for i, item in enumerate(final_news):
                # Simplify and clean prompt for URL safety
                raw_prompt = item.get("image_prompt", "Economy business report")
                # Remove special characters and limit length
                clean_prompt = re.sub(r'[^a-zA-Z0-9\s]', '', raw_prompt)
                encoded_prompt = clean_prompt.replace(" ", "%20")
                
                dynamic_seed = random.randint(1, 99999)
                # Keep the prompt concise for the API
                item["image_url"] = f"https://pollinations.ai/p/{encoded_prompt}?width=1024&height=576&seed={dynamic_seed}&model=flux&nologo=true"

            print(f"Successfully synthesized deep reports using Gemini 3 and generated unique AI images.")
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            
            # Diagnostic: List models if possible (new SDK has different method)
            try:
                print("--- Available Models Diagnostic ---")
                for m in client.models.list():
                    print(f"Available Model: {m.name}")
                print("-----------------------------------")
            except Exception as list_err:
                print(f"Could not list models: {list_err}")

            print("Using raw news fallback.")
            briefing = "AI 브리핑을 생성하는 중 오류가 발생했습니다. API 설정을 확인해 주세요."
            final_news = raw_news[:5]
            for item in final_news:
                item["summary"] = "내용 요약을 불러올 수 없습니다."
                item["content"] = f"### AI 리포트 생성 오류\n\n죄송합니다. 현재 Gemini 3 서비스를 일시적으로 사용할 수 없어 상세 리포트를 생성하지 못했습니다.\n\n**오류 상세:** {str(e)}\n\n**조치 방법:** GitHub Secrets에 `GEMINI_API_KEY`가 올바르게 등록되어 있는지 확인해 주세요."
                item["image_url"] = "https://images.unsplash.com/photo-1460925895917-afdab827c52f?q=80&w=1024&auto=format&fit=crop"

    # KST (UTC+9) adjustment for GitHub Actions environment
    from datetime import timezone, timedelta
    kst = timezone(timedelta(hours=9))
    now_kst = datetime.now(timezone.utc).astimezone(kst)

    data = {
        "last_updated": now_kst.strftime("%Y-%m-%d %H:%M:%S"),
        "briefing": briefing,
        "items": final_news
    }
    
    os.makedirs('data', exist_ok=True)
    with open('data/news.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"Successfully saved {len(final_news)} news items to data/news.json")

if __name__ == "__main__":
    fetch_economic_news()
