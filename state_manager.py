# -*- coding: utf-8 -*-
import json
import os
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

STATE_PATH = os.path.join(os.path.dirname(__file__), "state.json")
KST = ZoneInfo("Asia/Seoul")

MIN_INTERVAL_MIN = 120  # 2시간
MAX_INTERVAL_MIN = 180  # 3시간


def _now_kst():
    return datetime.now(KST)


def load_state():
    if not os.path.exists(STATE_PATH):
        return {
            "sent_urls_today": [],
            "sent_date": _now_kst().strftime("%Y-%m-%d"),
            "next_run_at": _now_kst().isoformat(),  # 최초 실행은 바로 가능하도록
            "total_sent_count": 0,
        }
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)

    today = _now_kst().strftime("%Y-%m-%d")
    if state.get("sent_date") != today:
        state["sent_date"] = today
        state["sent_urls_today"] = []

    return state


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def is_due(state):
    next_run = datetime.fromisoformat(state["next_run_at"])
    return _now_kst() >= next_run


def is_already_sent(state, url):
    key = url.split("?")[0]
    return key in state.get("sent_urls_today", [])


def mark_sent(state, url):
    key = url.split("?")[0]
    state.setdefault("sent_urls_today", []).append(key)
    state["total_sent_count"] = state.get("total_sent_count", 0) + 1
    schedule_next(state)


def schedule_next(state):
    minutes = random.randint(MIN_INTERVAL_MIN, MAX_INTERVAL_MIN)
    state["next_run_at"] = (_now_kst() + timedelta(minutes=minutes)).isoformat()
    state["last_interval_minutes"] = minutes
    return state
