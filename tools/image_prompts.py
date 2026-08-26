#!/usr/bin/env python3
"""列出當天缺配圖的新聞，並產生可直接貼到 claude.ai 生圖的 prompt。

用法：
    python3 tools/image_prompts.py 2026-08-26            # 只列缺圖的
    python3 tools/image_prompts.py 2026-08-26 --all      # 全部（想整批換成 AI 圖時用）
    python3 tools/image_prompts.py 2026-08-26 --md > prompts.md

生好的圖存成 images/manual/<檔名>.jpg，再跑一次 build.py 就會自動換上去，
不需要改任何設定。檔名就是每則下面標的那串 hash。

風格分兩種，這不是美感問題，是可信度問題：
  photo     ── 場景本身泛用（交易大廳、晶圓廠、球場、機場），可以走寫實攝影感
  editorial ── 牽涉真實政治人物或具體軍事行動，改用象徵性的編輯插畫。
               把不存在的事件畫成寫實新聞照，那張圖單獨流出去就是假新聞素材。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fetch_images import key_of  # noqa: E402

EDITORIAL_CATS = {"war", "politics"}
# 出現這些字就一律走插畫，不做寫實人像
FIGURES = ("普丁", "川普", "習近平", "拜登", "賴清德", "金正恩", "澤倫斯基",
           "納坦雅胡", "尼坦雅胡", "庫許納", "教宗", "總統", "總理", "首相")
# 具體衝突／傷亡事件也一律插畫：這種畫面做成寫實照片最容易被當成真的
CONFLICT = ("空襲", "轟炸", "砲擊", "交火", "喪生", "死亡", "傷亡", "遇襲",
            "軍事", "導彈", "飛彈", "無人機", "停火", "制裁", "綁架", "屠殺")

BASE = (
    "16:9 橫幅新聞配圖，1600×900。"
    "畫面下緣三分之一留一條深色漸層字幕條，條上以繁體中文黑體排入標題：「{title}」；"
    "右上角放一個小的紅色角標，內容為「豬豬日報」四個繁體字。"
    "不要出現任何電視台台標、LIVE 字樣、時間戳或其他新聞機構識別。"
    "不要出現英文標題列。"
)
PHOTO = (
    "寫實新聞攝影風格，自然光，淺景深，構圖沉穩，"
    "如同通訊社攝影記者拍攝的現場照片。畫面主題：{subject}。"
)
EDITORIAL = (
    "編輯插畫風格（非寫實攝影）：平塗色塊、粗線條、印刷網點質感，"
    "刻意讓人一眼看出是插畫而非照片。不要描繪可辨識的真實人物臉孔，"
    "改用剪影、象徵物件或場景符號。畫面主題：{subject}。"
)


def style_of(item):
    if item.get("category") in EDITORIAL_CATS:
        return "editorial"
    blob = item["title"] + item.get("summary", "")
    if any(f in blob for f in FIGURES) or any(k in blob for k in CONFLICT):
        return "editorial"
    return "photo"


def prompt_for(item):
    style = style_of(item)
    subject = (item["summary"] or item["title"]).rstrip("。 ")
    body = (EDITORIAL if style == "editorial" else PHOTO).format(subject=subject)
    return style, body + BASE.format(title=item["title"])


def main():
    date = sys.argv[1]
    show_all = "--all" in sys.argv
    as_md = "--md" in sys.argv

    data = json.load(open(os.path.join(ROOT, "data", f"{date}.json"), encoding="utf-8"))
    mpath = os.path.join(ROOT, "images", "manifest.json")
    manifest = json.load(open(mpath, encoding="utf-8")) if os.path.exists(mpath) else {}

    items, seen = [], set()
    for grp in ("top3", "global", "twcn", "market"):
        for it in data.get(grp, []):
            if it["url"] in seen:
                continue
            seen.add(it["url"])
            if show_all or not manifest.get(it["url"]):
                items.append(it)

    if as_md:
        print(f"# 豬豬日報 {date}　配圖 prompt（{len(items)} 則）\n")
        print("生好的圖存成 `images/manual/<檔名>`，再跑 `python3 build.py "
              f"{date}` 即可換上。\n")
        for i, it in enumerate(items, 1):
            style, p = prompt_for(it)
            print(f"## {i}. {it['title']}")
            print(f"- 檔名：`{key_of(it['url'])}.jpg`")
            print(f"- 風格：`{style}`　來源：{it.get('source', it.get('market', '—'))}\n")
            print("```")
            print(p)
            print("```\n")
    else:
        n_ed = sum(1 for it in items if style_of(it) == "editorial")
        print(f"{date}　需要配圖 {len(items)} 則"
              f"（寫實 {len(items)-n_ed}／插畫 {n_ed}）\n")
        for it in items:
            print(f"  {key_of(it['url'])}.jpg  [{style_of(it):9s}] {it['title'][:44]}")
        print("\n完整 prompt：加上 --md")


if __name__ == "__main__":
    main()
