from datetime import datetime, timedelta, timezone
import os
import re
import feedparser
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont
import requests

# 1. API 키 및 환경 변수 로드
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_API_KEY)

# 2. 실시간 최신 뉴스 수집 (dot notation 차단 및 완전 안전식 설계)
def get_recent_news():
    rss_url = "https://finance.yahoo.com/news/rssindex"
    feed = feedparser.parse(rss_url)
    
    now = datetime.now(timezone.utc)
    time_limit = now - timedelta(hours=6) # 넉넉하게 최근 6시간 이내 뉴스
    
    recent_articles = []
    
    # feed.entries를 dict 형태로 안전하게 순회하며 entry.summary 절대 호출 안 함
    for item in feed.entries:
        # dict로 강제 변환하거나 안전한 get 사용
        entry = dict(item) if not isinstance(item, dict) else item
        
        published_parsed = entry.get("published_parsed")
        if published_parsed:
            try:
                pub_date = datetime(*published_parsed[:6], tzinfo=timezone.utc)
                if pub_date >= time_limit:
                    title = entry.get('title', '제목 없음')
                    summary = entry.get('summary', entry.get('description', '요약 내용 없음'))
                    source = entry.get('source', {})
                    source_name = source.get('title', 'Yahoo Finance') if isinstance(source, dict) else 'Yahoo Finance'
                    
                    recent_articles.append(f"제목: {title}\n요약: {summary}\n출처: {source_name}\n")
            except Exception:
                continue
    
    # 만약 최근 시간 내 뉴스가 없다면 가장 최신 뉴스 1개 강제 추출
    if not recent_articles and feed.entries:
        item = feed.entries[0]
        entry = dict(item) if not isinstance(item, dict) else item
        title = entry.get('title', '제목 없음')
        summary = entry.get('summary', entry.get('description', '요약 내용 없음'))
        recent_articles.append(f"제목: {title}\n요약: {summary}\n출처: Yahoo Finance\n")

    return "\n---\n".join(recent_articles)

# 3. Gemini API로 중요 뉴스 선별 및 구조화
def analyze_with_gemini(news_text):
    if not news_text:
        return None

    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
    아래는 방금 수집된 야후 파이낸스 실시간 경제 뉴스들입니다.
    이 중 주식/금융 시장에 가장 중요도가 높은 뉴스 1개를 선별하세요.
    중요한 뉴스가 있다면 반드시 아래 형식으로만 출력하세요:
    [중요도] (1~5 중 숫자로만, 예: 5)
    [제목] (한국어 번역 핵심 제목, 20자 이내)
    [요약] (핵심 내용 2~3줄 요약, 한국어)
    [수혜] (수혜 받을 섹터/종목)
    [리스크] (피해 입거나 리스크 있는 섹터/종목)
    [출처] (원문 출처 매체명, 예: Yahoo Finance)

    뉴스 목록:
    {news_text}
    """
    
    response = model.generate_content(prompt)
    text = response.text.strip()
    
    if "NONE" in text or not text:
        return None
        
    return text

# 4. 카드뉴스 이미지 동적 생성
def create_card_image(data_text):
    importance_num = re.search(r"\[중요도\]\s*(\d)", data_text)
    stars = "⭐" * int(importance_num.group(1)) if importance_num else "⭐⭐⭐⭐"
    
    title = re.search(r"\[제목\]\s*(.*)", data_text)
    title_str = title.group(1) if title else "MARKET NEWS"
    
    summary = re.search(r"\[요약\]\s*([\s\S]*?)(?=\[수혜\]|$)", data_text)
    summary_str = summary.group(1).strip() if summary else ""
    
    benefit = re.search(r"\[수혜\]\s*(.*)", data_text)
    benefit_str = benefit.group(1) if benefit else "없음"
    
    risk = re.search(r"\[리스크\]\s*(.*)", data_text)
    risk_str = risk.group(1) if risk else "없음"

    source = re.search(r"\[출처\]\s*(.*)", data_text)
    source_str = source.group(1).strip() if source else "Yahoo Finance"

    # 이미지 캔버스 (1080x1080)
    width, height = 1080, 1080
    image = Image.new("RGB", (width, height), color="#0F172A")
    draw = ImageDraw.Draw(image)

    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 45)
        font_body = ImageFont.truetype("DejaVuSans.ttf", 32)
        font_small = ImageFont.truetype("DejaVuSans.ttf", 24)
    except:
        font_title = font_body = font_small = ImageFont.load_default()

    # 테두리 및 타이틀
    draw.rectangle([50, 50, 1030, 1030], outline="#334155", width=4)
    draw.rectangle([80, 80, 420, 140], fill="#1E293B")
    draw.text((100, 95), "⚡ MARKET PULSE", fill="#10B981", font=font_title)
    draw.text((750, 95), stars, fill="#F59E0B", font=font_title)

    # 뉴스 제목
    draw.text((80, 180), title_str, fill="#FFFFFF", font=font_title)
    draw.line([(80, 250), (1000, 250)], fill="#334155", width=2)

    # 본문 요약
    draw.text((80, 280), "■ 핵심 요약", fill="#94A3B8", font=font_body)
    draw.text((80, 330), summary_str, fill="#F8FAFC", font=font_body)

    # 수혜 / 리스크 섹터 박스
    draw.rectangle([80, 640, 1000, 755], fill="#132E27")
    draw.text((110, 655), "🟢 수혜 예상 섹터", fill="#34D399", font=font_body)
    draw.text((110, 700), benefit_str, fill="#FFFFFF", font=font_body)

    draw.rectangle([80, 780, 1000, 895], fill="#31191D")
    draw.text((110, 795), "🔴 리스크/피해 섹터", fill="#F87171", font=font_body)
    draw.text((110, 840), risk_str, fill="#FFFFFF", font=font_body)

    # 하단 출처 표기
    draw.line([(80, 920), (1000, 920)], fill="#334155", width=1)
    draw.text((80, 950), f"출처 | {source_str}", fill="#64748B", font=font_small)
    draw.text((800, 950), "AUTO GENERATED", fill="#475569", font=font_small)

    img_path = "card_news.png"
    image.save(img_path)
    return img_path

# 5. 텔레그램 전송
def send_telegram(image_path):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(image_path, "rb") as photo:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID}, files={'photo': photo})

if __name__ == "__main__":
    recent_news = get_recent_news()
    if recent_news:
        analysis = analyze_with_gemini(recent_news)
        if analysis:
            img_path = create_card_image(analysis)
            send_telegram(img_path)
