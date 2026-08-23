# -*- coding: utf-8 -*-
import os
import requests

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_photo(image_path, caption=""):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 환경변수가 필요합니다.")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption[:1024]},
            files={"photo": f},
            timeout=30,
        )
    if resp.status_code != 200:
        raise RuntimeError(f"텔레그램 발송 실패: {resp.status_code} {resp.text}")
    return resp.json()


def send_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 환경변수가 필요합니다.")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": CHAT_ID, "text": text[:4000]}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"텔레그램 메시지 발송 실패: {resp.status_code} {resp.text}")
    return resp.json()
