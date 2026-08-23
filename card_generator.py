# -*- coding: utf-8 -*-
"""
카드뉴스 이미지 생성 (TradingView 라이트 테마 느낌: 흰 배경 + 초록/빨강 포인트)
"""
import os
import subprocess
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1350  # 인스타 카드뉴스 비율 느낌

COLOR_BG = (255, 255, 255)
COLOR_TEXT_MAIN = (30, 34, 45)
COLOR_TEXT_SUB = (110, 118, 132)
COLOR_GREEN = (8, 153, 129)      # TradingView 상승 초록
COLOR_GREEN_BG = (224, 247, 240)
COLOR_RED = (242, 54, 69)        # TradingView 하락 빨강
COLOR_RED_BG = (253, 226, 228)
COLOR_LINE = (235, 238, 242)
COLOR_STAR_ON = (255, 179, 0)
COLOR_STAR_OFF = (225, 228, 233)

FONT_DIR = "/usr/share/fonts/opentype/noto"
FONT_REGULAR = os.path.join(FONT_DIR, "NotoSansCJK-Regular.ttc")
FONT_MEDIUM = os.path.join(FONT_DIR, "NotoSansCJK-Medium.ttc")
FONT_BOLD = os.path.join(FONT_DIR, "NotoSansCJK-Bold.ttc")
FONT_BLACK = os.path.join(FONT_DIR, "NotoSansCJK-Black.ttc")

# 환경에 따라 noto-cjk 설치 경로/파일명이 다를 수 있어 후보들을 순서대로 시도한다.
_FALLBACK_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJKkr-Regular.otf",
    "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
]


def _resolve_font_path(preferred):
    """지정한 경로를 우선 시도하고, 없으면 fc-match로 시스템에 실제 설치된
    한국어 지원 폰트를 찾아내고, 그마저 실패하면 후보 목록을 순서대로 시도한다."""
    if preferred and os.path.exists(preferred):
        return preferred

    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", "Noto Sans CJK KR"],
            capture_output=True, text=True, timeout=5,
        )
        path = result.stdout.strip()
        if path and os.path.exists(path):
            return path
    except Exception:
        pass

    for cand in _FALLBACK_CANDIDATES:
        if os.path.exists(cand):
            return cand

    raise RuntimeError(
        "한국어 지원 폰트를 찾을 수 없습니다. 워크플로우에서 "
        "'fonts-noto-cjk' 또는 'fonts-nanum' 패키지가 설치됐는지 확인하세요."
    )


_RESOLVED_CACHE = {}


def _font(path, size):
    if path not in _RESOLVED_CACHE:
        try:
            _RESOLVED_CACHE[path] = _resolve_font_path(path)
        except RuntimeError:
            _RESOLVED_CACHE[path] = None

    resolved = _RESOLVED_CACHE[path]
    if resolved is None:
        # 폰트를 전혀 못 찾은 경우 Pillow 기본 폰트로라도 렌더링 (한글은 깨지지만 죽지는 않음)
        return ImageFont.load_default(size=size)

    try:
        return ImageFont.truetype(resolved, size, index=0)
    except Exception:
        try:
            return ImageFont.truetype(resolved, size)
        except Exception:
            return ImageFont.load_default(size=size)


def _wrap_text(draw, text, font, max_width):
    """단어/글자 단위 줄바꿈 (한글 포함 대응, 공백 없어도 강제 줄바꿈)"""
    lines = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            lines.append("")
            continue
        line = ""
        for ch in paragraph:
            test = line + ch
            if draw.textlength(test, font=font) <= max_width:
                line = test
            else:
                lines.append(line)
                line = ch
        lines.append(line)
    return lines


def _draw_pepe(draw, cx, cy, r):
    """이모지 폰트 의존 없이 심플한 개구리(페페st) 도트 아이콘을 직접 그림"""
    green = (94, 191, 109)
    dark = (43, 122, 63)
    white = (255, 255, 255)
    # 머리
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=green, outline=dark, width=3)
    # 눈 (위쪽 두 개 볼록 튀어나온 형태)
    eye_r = int(r * 0.34)
    for dx in (-1, 1):
        ex, ey = cx + dx * int(r * 0.55), cy - int(r * 0.55)
        draw.ellipse([ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r], fill=green, outline=dark, width=2)
        draw.ellipse([ex - eye_r * 0.55, ey - eye_r * 0.55, ex + eye_r * 0.55, ey + eye_r * 0.55], fill=white)
        pr = int(eye_r * 0.32)
        draw.ellipse([ex - pr, ey - pr, ex + pr, ey + pr], fill=(20, 20, 20))
    # 입 (일자 라인, 진중한 표정)
    draw.line([cx - r * 0.45, cy + r * 0.25, cx + r * 0.45, cy + r * 0.25], fill=dark, width=4)


def _tri_up(draw, cx, cy, r, color):
    draw.polygon([(cx, cy - r), (cx - r, cy + r), (cx + r, cy + r)], fill=color)


def _tri_down(draw, cx, cy, r, color):
    draw.polygon([(cx, cy + r), (cx - r, cy - r), (cx + r, cy - r)], fill=color)


def _stars(draw, x, y, count, size=34, gap=8):
    count = max(0, min(5, round(count)))
    star_font = _font(FONT_BLACK, size)
    for i in range(5):
        color = COLOR_STAR_ON if i < count else COLOR_STAR_OFF
        draw.text((x + i * (size + gap), y), "★", font=star_font, fill=color)


def _chip_row(draw, x, y, max_width, labels, bg, fg, font):
    """섹터 태그들을 칩(pill) 형태로 줄바꿈하며 배치, 다음 y 좌표 반환"""
    pad_x, pad_y, gap = 22, 12, 14
    cur_x, cur_y = x, y
    for label in labels:
        tw = draw.textlength(label, font=font)
        chip_w = tw + pad_x * 2
        chip_h = font.size + pad_y * 2
        if cur_x + chip_w > x + max_width:
            cur_x = x
            cur_y += chip_h + gap
        draw.rounded_rectangle(
            [cur_x, cur_y, cur_x + chip_w, cur_y + chip_h],
            radius=chip_h // 2, fill=bg
        )
        draw.text((cur_x + pad_x, cur_y + pad_y - 2), label, font=font, fill=fg)
        cur_x += chip_w + gap
    return cur_y + font.size + pad_y * 2 + gap


def generate_card(
    out_path,
    title,
    importance,          # 1~5
    summary,
    beneficiary_sectors,  # list[str]
    risk_sectors,          # list[str]
    source,
    time_str,
    tag="MARKET NEWS",
):
    img = Image.new("RGB", (W, H), COLOR_BG)
    d = ImageDraw.Draw(img)

    margin = 64

    # 상단 태그 바
    tag_font = _font(FONT_BOLD, 28)
    d.rounded_rectangle([margin, 56, margin + d.textlength(tag, font=tag_font) + 44, 56 + 52],
                         radius=26, fill=COLOR_GREEN)
    d.text((margin + 22, 56 + 10), tag, font=tag_font, fill=(255, 255, 255))

    # 페페 아이콘 (우측 상단)
    _draw_pepe(d, W - margin - 44, 56 + 44, 44)

    # 시간/출처
    meta_font = _font(FONT_REGULAR, 24)
    meta = f"{source}  ·  {time_str}"
    d.text((margin, 150), meta, font=meta_font, fill=COLOR_TEXT_SUB)

    # 구분선
    d.line([margin, 190, W - margin, 190], fill=COLOR_LINE, width=2)

    # 제목
    title_font = _font(FONT_BLACK, 52)
    y = 220
    for line in _wrap_text(d, title, title_font, W - margin * 2):
        d.text((margin, y), line, font=title_font, fill=COLOR_TEXT_MAIN)
        y += 64
    y += 10

    # 중요도 별점
    label_font = _font(FONT_MEDIUM, 26)
    d.text((margin, y), "중요도", font=label_font, fill=COLOR_TEXT_SUB)
    _stars(d, margin + 110, y - 4, importance, size=32, gap=6)
    y += 60

    d.line([margin, y, W - margin, y], fill=COLOR_LINE, width=2)
    y += 34

    # 요약 본문
    body_font = _font(FONT_REGULAR, 32)
    for line in _wrap_text(d, summary, body_font, W - margin * 2):
        d.text((margin, y), line, font=body_font, fill=COLOR_TEXT_MAIN)
        y += 46
    y += 30

    # 수혜 섹터
    sec_label_font = _font(FONT_BOLD, 28)
    chip_font = _font(FONT_MEDIUM, 26)
    _tri_up(d, margin + 10, y + 18, 12, COLOR_GREEN)
    d.text((margin + 32, y), "수혜 예상 섹터", font=sec_label_font, fill=COLOR_GREEN)
    y += 46
    y = _chip_row(d, margin, y, W - margin * 2, beneficiary_sectors or ["해당 없음"],
                  COLOR_GREEN_BG, COLOR_GREEN, chip_font)
    y += 20

    # 리스크 섹터
    _tri_down(d, margin + 10, y + 18, 12, COLOR_RED)
    d.text((margin + 32, y), "리스크 예상 섹터", font=sec_label_font, fill=COLOR_RED)
    y += 46
    y = _chip_row(d, margin, y, W - margin * 2, risk_sectors or ["해당 없음"],
                  COLOR_RED_BG, COLOR_RED, chip_font)

    # 하단 푸터
    footer_font = _font(FONT_REGULAR, 22)
    footer_text = "자동 요약 · 투자 판단은 본인 책임"
    d.line([margin, H - 90, W - margin, H - 90], fill=COLOR_LINE, width=2)
    d.text((margin, H - 68), footer_text, font=footer_font, fill=COLOR_TEXT_SUB)
    _draw_pepe(d, margin + d.textlength(footer_text, font=footer_font) + 34, H - 68 + 12, 16)

    img.save(out_path, quality=95)
    return out_path


if __name__ == "__main__":
    generate_card(
        "/home/claude/news-card-bot/sample_card.png",
        title="연준 9월 금리 인하 기대감 확대, 국채 금리 급락",
        importance=4,
        summary=(
            "이번 주 발표된 고용지표가 예상치를 밑돌면서 시장은 9월 FOMC에서의 금리 인하 "
            "가능성을 더 높게 반영하기 시작했습니다. 단기 국채 금리가 큰 폭으로 하락했고, "
            "성장주 중심으로 매수세가 유입되는 모습입니다."
        ),
        beneficiary_sectors=["빅테크", "반도체", "리츠(REITs)", "성장주"],
        risk_sectors=["금융(은행)", "달러 강세 수혜주"],
        source="Yahoo Finance",
        time_str="2026.08.24 14:30 KST",
    )
    print("saved")
