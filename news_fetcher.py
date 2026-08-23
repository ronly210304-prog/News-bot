# -*- coding: utf-8 -*-
"""
야후 파이낸스 등 RSS에서 최신 금융 뉴스를 모아온다.
"""
import feedparser
from datetime import datetime, timezone

RSS_FEEDS = [
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
    ("Yahoo Finance", "https://finance.yahoo.com/rss/topstories"),
    ("MarketWatch", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("Investing.com", "https://www.investing.com/rss/news_25.rss"),
    ("Reuters Business", "https://www.reutersagency.com/feed/?best-topics=business-finance"),
]


def _to_utc(struct_time):
    if not struct_time:
        return datetime.now(timezone.utc)
    return datetime(*struct_time[:6], tzinfo=timezone.utc)


def fetch_latest_news(max_items=40):
    """모든 피드를 모아 최신순으로 정렬해서 반환. 실패한 피드는 조용히 건너뜀."""
    items = []
    for source, url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:20]:
                link = entry.get("link")
                title = entry.get("title")
                if not link or not title:
                    continue
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                summary = entry.get("summary", "")
                items.append({
                    "source": source,
                    "title": title.strip(),
                    "url": link.strip(),
                    "summary_raw": summary,
                    "published_utc": _to_utc(published),
                })
        except Exception as e:
            print(f"[news_fetcher] {source} 피드 실패: {e}")
            continue

    # 최신순 정렬 + URL 기준 중복 제거(같은 뉴스가 여러 피드에 뜨는 경우)
    seen = set()
    deduped = []
    items.sort(key=lambda x: x["published_utc"], reverse=True)
    for it in items:
        key = it["url"].split("?")[0]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    return deduped[:max_items]


if __name__ == "__main__":
    for n in fetch_latest_news(10):
        print(n["published_utc"], "-", n["source"], "-", n["title"])
