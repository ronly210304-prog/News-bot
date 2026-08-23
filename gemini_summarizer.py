# -*- coding: utf-8 -*-
"""
Gemini API 호출 - 뉴스 원문을 받아 카드뉴스용 JSON(제목/중요도/요약/수혜섹터/리스크섹터)으로 변환.
비용 절감을 위해 기본적으로 gemini-flash-lite-latest(경량/저가 alias) 사용, 출력 토큰도 짧게 제한.
"""
import json
import os
import re
import requests

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

SYSTEM_PROMPT = """당신은 금융 뉴스를 한국어 카드뉴스용으로 압축하는 애널리스트입니다.
말투는 가볍지 않고 진중하게, 하지만 과장된 공포/희망 조장 없이 사실 기반으로 씁니다.
반드시 아래 JSON 스키마로만 응답하세요. 다른 텍스트, 설명, 마크다운 코드블록 없이 순수 JSON만 출력합니다.

{
  "title": "한국어로 압축한 헤드라인 (최대 28자)",
  "importance": 1~5 사이 정수 (시장 전체에 미치는 영향 크기, 5가 가장 중요),
  "summary": "3~4문장, 한국어, 핵심 사실과 시장에 미치는 의미 위주로 요약 (250자 내외)",
  "beneficiary_sectors": ["수혜 예상 섹터/테마 한국어 명칭, 2~4개"],
  "risk_sectors": ["리스크/타격 예상 섹터/테마 한국어 명칭, 1~3개, 없으면 빈 배열"]
}
"""


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    return json.loads(text)


def summarize_news(title, source, raw_summary_html):
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY 환경변수가 설정되어 있지 않습니다.")

    user_content = (
        f"[출처] {source}\n"
        f"[원제목] {title}\n"
        f"[원문 요약/본문 일부]\n{raw_summary_html[:1500]}"
    )

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 400,
            "response_mime_type": "application/json",
        },
    }

    resp = requests.post(
        API_URL,
        params={"key": GEMINI_API_KEY},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Gemini 응답 파싱 실패: {data}") from e

    parsed = _extract_json(text)

    # 방어적 기본값
    parsed.setdefault("title", title[:28])
    parsed.setdefault("importance", 3)
    parsed.setdefault("summary", "")
    parsed.setdefault("beneficiary_sectors", [])
    parsed.setdefault("risk_sectors", [])
    parsed["importance"] = max(1, min(5, int(parsed["importance"])))

    return parsed


if __name__ == "__main__":
    # 로컬 테스트용 (GEMINI_API_KEY 환경변수 필요)
    result = summarize_news(
        "Fed rate cut odds jump after weak jobs report",
        "Yahoo Finance",
        "The September jobs report came in below expectations, pushing traders to price in a higher chance of a Fed rate cut this month...",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
