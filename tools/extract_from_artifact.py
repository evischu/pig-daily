#!/usr/bin/env python3
"""一次性遷移工具：把舊版手寫的豬豬日報 HTML 抽成 data/YYYY-MM-DD.json。

用法：
    python3 tools/extract_from_artifact.py <舊版.html> <輸出.json>

之後每天不需要再用這支，直接編輯／產生 data/*.json 即可。
"""
import json
import re
import sys
from html import unescape

# 舊版把配色寫死在 inline style，這裡反查回類別代碼
COLOR_TO_CAT = {
    "#B91C1C": "war",
    "#B45309": "finance",
    "#4C5FD5": "world",
    "#0E7490": "tech",
    "#BE123C": "society",
    "#C0267A": "entertainment",
    "#15803D": "sports",
    "#C2410C": "disaster",
    "#7C3AED": "politics",
}
LABEL_TO_CAT = {
    "戰爭": "war",
    "財經": "finance",
    "經濟": "finance",
    "國際": "world",
    "科技": "tech",
    "社會": "society",
    "娛樂": "entertainment",
    "體育": "sports",
    "天災": "disaster",
    "政治": "politics",
}


def clean(s):
    return unescape(re.sub(r"\s+", " ", s or "")).strip()


def cat_of(color, label):
    for name in LABEL_TO_CAT:
        if label and name in label:
            return LABEL_TO_CAT[name]
    return COLOR_TO_CAT.get((color or "").upper(), "world")


def parse_cards(block, tag):
    """抓 hero-card / news-card 這種大中型卡片。"""
    out = []
    pattern = re.compile(
        r'<article class="(?:hero|news)-card[^"]*">.*?'
        r'--cat-color:(#[0-9A-Fa-f]{6}).*?'
        r'<span class="rank-num">(\d+)</span>.*?'
        r'<span class="chip"[^>]*>(.*?)</span>\s*'
        r"<(h3|h4)>(.*?)</\4>\s*"
        r"<p>(.*?)</p>\s*"
        r'<a class="src" href="([^"]+)"[^>]*>(.*?)</a>',
        re.S,
    )
    for m in pattern.finditer(block):
        color, rank, chip, _, title, summary, url, source = m.groups()
        out.append(
            {
                "rank": int(rank),
                "category": cat_of(color, clean(chip)),
                "title": clean(title),
                "summary": clean(summary),
                "url": url,
                "source": clean(source).replace("↗", "").strip(),
                "tier": tag,
            }
        )
    return out


def parse_mini(block):
    out = []
    pattern = re.compile(
        r'<a class="mini-row" href="([^"]+)"[^>]*>\s*'
        r'<span class="mini-rank">(\d+)</span>.*?'
        r"--cat-color:(#[0-9A-Fa-f]{6}).*?"
        r'<span class="mini-title">(.*?)</span>\s*'
        r'<span class="mini-desc">(.*?)</span>\s*'
        r'<span class="mini-cat">(.*?)</span>.*?'
        r'<span class="mini-src">(.*?)</span>',
        re.S,
    )
    for m in pattern.finditer(block):
        url, rank, color, title, desc, chip, source = m.groups()
        out.append(
            {
                "rank": int(rank),
                "category": cat_of(color, clean(chip)),
                "title": clean(title),
                "summary": clean(desc),
                "url": url,
                "source": clean(source).replace("↗", "").strip(),
                "tier": "list",
            }
        )
    return out


def slice_section(html, sid):
    m = re.search(r'<section id="%s">(.*?)</section>' % sid, html, re.S)
    return m.group(1) if m else ""


def parse_market(block):
    out = []
    pattern = re.compile(
        r'<article class="market-card (\w+)">.*?'
        r'<span class="sent-badge \w+">(.*?)</span>\s*'
        r'<span class="market-tag">(.*?)</span>\s*'
        r'<span class="market-industry">(.*?)</span>.*?'
        r"<h4>(.*?)</h4>\s*"
        r'<p class="market-summary">(.*?)</p>\s*'
        r'<p class="market-reason"><strong>判斷原因：</strong>(.*?)</p>.*?'
        r'<span class="stocks">(.*?)</span>\s*'
        r'<a class="src" href="([^"]+)"',
        re.S,
    )
    for m in pattern.finditer(block):
        sent, badge, market, industry, title, summary, reason, stocks, url = m.groups()
        out.append(
            {
                "sentiment": sent,
                "sentiment_label": clean(badge),
                "market": clean(market),
                "industry": clean(industry),
                "title": clean(title),
                "summary": clean(summary),
                "reason": clean(reason),
                "tickers": [s.strip() for s in clean(stocks).replace("、", ",").split(",") if s.strip()],
                "url": url,
            }
        )
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    html = open(src, encoding="utf-8").read()
    # 移除內嵌 base64，正則才跑得動
    html = re.sub(r"data:image/[a-z+]+;base64,[A-Za-z0-9+/=]+", "IMG", html)

    date_m = re.search(r'class="masthead-date">(.*?)</div>', html)

    top3 = slice_section(html, "top3")
    glob = slice_section(html, "global")
    twcn = slice_section(html, "twcn")
    market = slice_section(html, "market")

    def split_tiers(sec):
        lead = re.search(r'<h3 class="tier-label">焦點頭條</h3>(.*?)<h3 class="tier-label">', sec, re.S)
        mid = re.search(r'<h3 class="tier-label">重點新聞</h3>(.*?)<h3 class="tier-label">', sec, re.S)
        rest = re.search(r'<h3 class="tier-label">更多熱門.*?</h3>(.*)', sec, re.S)
        return (
            parse_cards(lead.group(1) if lead else "", "lead"),
            parse_cards(mid.group(1) if mid else "", "mid"),
            parse_mini(rest.group(1) if rest else ""),
        )

    g_lead, g_mid, g_rest = split_tiers(glob)
    t_lead, t_mid, t_rest = split_tiers(twcn)

    data = {
        "date": "2026-08-26",
        "published": clean(date_m.group(1)) if date_m else "",
        "top3": parse_cards(top3, "top3"),
        "global": g_lead + g_mid + g_rest,
        "twcn": t_lead + t_mid + t_rest,
        "market": parse_market(market),
    }
    json.dump(data, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(
        f"top3={len(data['top3'])} global={len(data['global'])} "
        f"twcn={len(data['twcn'])} market={len(data['market'])}"
    )


if __name__ == "__main__":
    main()
