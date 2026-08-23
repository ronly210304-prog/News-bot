# -*- coding: utf-8 -*-
"""
실행 흐름:
1) STOP 파일 있으면 즉시 종료 (사용자가 중지시킨 상태)
2) state.json 확인 -> 아직 다음 발송 시각이 안 됐으면 조용히 종료 (비용 0)
3) RSS에서 최신 뉴스 수집 -> 오늘 이미 보낸 것 제외하고 가장 최신 1건 선택
4) 보낼 뉴스가 없으면 종료 (다음 스케줄은 그대로 둠, 다음 워크플로우 실행 때 재시도)
5) Gemini로 요약 -> 카드 이미지 생성 -> 텔레그램 발송
6) state.json 갱신(발송 기록 + 다음 발송시각 랜덤 2~3시간 뒤) 후 저장
   (실제 git commit/push는 GitHub Actions workflow 쪽에서 처리)
"""
import os
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from news_fetcher import fetch_latest_news
from gemini_summarizer import summarize_news
from card_generator import generate_card
from telegram_sender import send_photo, send_message
from state_manager import load_state, save_state, is_due, is_already_sent, mark_sent, schedule_next

STOP_FLAG_PATH = os.path.join(os.path.dirname(__file__), "STOP")
KST = ZoneInfo("Asia/Seoul")


def log(msg):
    print(f"[{datetime.now(KST).strftime('%H:%M:%S')}] {msg}")


def main():
    if os.path.exists(STOP_FLAG_PATH):
        log("STOP 파일이 존재합니다. 아무 작업도 하지 않고 종료합니다.")
        return

    state = load_state()

    if not is_due(state):
        log(f"아직 발송 시각이 아닙니다. 다음 발송 예정: {state['next_run_at']}")
        save_state(state)  # 날짜 롤오버 등 반영
        return

    log("발송 시각 도달. 뉴스 수집 시작...")
    news_list = fetch_latest_news(max_items=40)
    log(f"수집된 뉴스 {len(news_list)}건")

    candidate = None
    for item in news_list:
        if not is_already_sent(state, item["url"]):
            candidate = item
            break

    if candidate is None:
        log("보낼 새 뉴스가 없습니다 (전부 중복이거나 피드 실패). 다음 워크플로우 실행 때 재시도합니다.")
        save_state(state)
        return

    log(f"선택된 뉴스: [{candidate['source']}] {candidate['title']}")

    try:
        analysis = summarize_news(
            candidate["title"], candidate["source"], candidate["summary_raw"]
        )
    except Exception:
        log("Gemini 요약 실패:")
        traceback.print_exc()
        # 실패한 뉴스는 건너뛰되, 다음 새 뉴스로 재시도할 수 있도록 sent 처리는 하지 않고 종료
        save_state(state)
        return

    time_str = datetime.now(KST).strftime("%Y.%m.%d %H:%M KST")
    out_path = os.path.join(os.path.dirname(__file__), "output_card.png")

    generate_card(
        out_path,
        title=analysis["title"],
        importance=analysis["importance"],
        summary=analysis["summary"],
        beneficiary_sectors=analysis["beneficiary_sectors"],
        risk_sectors=analysis["risk_sectors"],
        source=candidate["source"],
        time_str=time_str,
    )
    log("카드 이미지 생성 완료")

    try:
        send_photo(out_path, caption=f"{analysis['title']}\n{candidate['url']}")
        log("텔레그램 발송 완료")
    except Exception:
        log("텔레그램 발송 실패:")
        traceback.print_exc()
        save_state(state)
        return

    mark_sent(state, candidate["url"])
    save_state(state)
    log(f"상태 저장 완료. 다음 발송 예정: {state['next_run_at']} (간격 {state['last_interval_minutes']}분)")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("치명적 오류 발생:")
        traceback.print_exc()
        # 워크플로우 자체는 실패시켜서 Actions 탭에서 바로 알아챌 수 있게 함
        sys.exit(1)
