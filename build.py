#!/usr/bin/env python3
"""把 data/YYYY-MM-DD.json 組成一份可發布的豬豬日報 HTML。

用法：
    python3 build.py 2026-08-26

流程：
    data/<date>.json  ── 當日內容（新聞、摘要、來源、股市判斷）
    images/manifest.json ── fetch_images.py 抓到的真實照片
    images/manual/    ── 手動放進來的 AI 生成圖，檔名用 <hash>.jpg，優先於真實照片
                         hash 由 tools/image_prompts.py 產出的清單提供
    ↓
    dist/<date>.html  ── 發布用檔案（圖片以 data URI 內嵌，單檔即可上線）
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from html import escape

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from fetch_images import SIZES, derive, key_of, normalize  # noqa: E402

# ── 分類：代號 + 中文名。刻意不做顏色編碼 ────────────────────────────────
# 九種分類要做到色盲可辨的九個色相是做不到的，硬做只會變成看不出差別的調色盤。
# 分類改由文字承載（代號 + 中文），顏色留給真正需要編碼狀態的地方（多空）。
CATS = {
    "world":         ("INT", "國際"),
    "war":           ("WAR", "戰事"),
    "politics":      ("POL", "政治"),
    "finance":       ("FIN", "財經"),
    "tech":          ("TEC", "科技"),
    "society":       ("SOC", "社會"),
    "disaster":      ("DIS", "天災"),
    "entertainment": ("ENT", "娛樂"),
    "sports":        ("SPT", "體育"),
}
SENT = {
    "bull":    ("▲", "利多"),
    "bear":    ("▼", "利空"),
    "neutral": ("■", "中性"),
}
WEEKDAY = "一二三四五六日"


def e(s):
    return escape(str(s or ""), quote=True)


# ── 圖片 ────────────────────────────────────────────────────────────────
def load_manifest():
    p = os.path.join(ROOT, "images", "manifest.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def ingest_manual():
    """把 images/manual/ 裡手動放的圖，跑同一套裁切壓縮，蓋掉抓來的照片。"""
    src = os.path.join(ROOT, "images", "manual")
    if not os.path.isdir(src):
        return {}
    over = {}
    for fn in sorted(os.listdir(src)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        key = stem.split(".")[0]
        work = normalize(os.path.join(src, fn), "manual-" + key)
        if not work:
            print(f"  ! 讀不到 {fn}")
            continue
        made = {}
        for name, (tw, th) in SIZES.items():
            out = derive(work, "m" + key, name, tw, th)
            if out:
                made[name] = out
        if made:
            over[key] = made
    return over


_cache = {}


LITE = os.environ.get("LITE") == "1"  # 版面檢查用：不內嵌圖片，畫面才截得到


def data_uri(fname):
    if LITE:
        return None
    if fname in _cache:
        return _cache[fname]
    path = os.path.join(ROOT, "images", fname)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        uri = "data:image/webp;base64," + base64.b64encode(f.read()).decode()
    _cache[fname] = uri
    return uri


class Images:
    def __init__(self):
        self.manifest = load_manifest()
        self.manual = ingest_manual()
        self.stats = {"manual": 0, "photo": 0, "none": 0}

    def get(self, url, size):
        key = key_of(url)
        made = self.manual.get(key)
        kind = "manual"
        if not made:
            made = self.manifest.get(url)
            kind = "photo"
        if not made or size not in made:
            return None, None
        return data_uri(made[size]), kind

    def tally(self, url):
        key = key_of(url)
        if self.manual.get(key):
            self.stats["manual"] += 1
        elif self.manifest.get(url):
            self.stats["photo"] += 1
        else:
            self.stats["none"] += 1


# ── 版面元件 ─────────────────────────────────────────────────────────────
def frame(item, size, imgs, rank=None):
    """圖框。沒有圖就回傳空字串 —— 卡片改走純文字版型。

    留一個掛「豬豬日報」的角標：畫面來源標示清楚，
    但不做虛構電視台識別加直播時間戳那種會被誤認成真實新聞截圖的處理。
    """
    uri, kind = imgs.get(item["url"], size)
    if not uri:
        return ""
    rk = f'<span class="rk">{rank}</span>' if rank else ""
    art = '<span class="bug art">示意圖</span>' if kind == "manual" else '<span class="bug">豬豬日報</span>'
    return (
        f'<span class="frame"><img src="{uri}" alt="{e(item["title"])}" '
        f'loading="lazy" decoding="async">{rk}{art}<span class="lower"></span></span>'
    )


def source_link(item):
    return (
        f'<a class="src" href="{e(item["url"])}" target="_blank" rel="noopener">'
        f'{e(item["source"])}<span class="ext" aria-hidden="true">↗</span></a>'
    )


def attrs(item):
    code, name = CATS.get(item.get("category", "world"), ("INT", "國際"))
    hay = f'{item["title"]} {item["summary"]} {item["source"]} {name} {code}'.lower()
    return f' data-cat="{item.get("category","world")}" data-q="{e(hay)}"'


def big_card(item, imgs, size="lg", cls="card", rank=None):
    imgs.tally(item["url"])
    code, name = CATS.get(item.get("category", "world"), ("INT", "國際"))
    pic = frame(item, size, imgs, rank)
    # 沒有配圖就不留空框：改成純文字卡，排名移到分類列。報紙本來就有無圖稿。
    if not pic:
        cls += " textonly"
        num = f'<span class="inline-rk">{rank}</span>' if rank else ""
    else:
        num = ""
    return f"""<article class="{cls}"{attrs(item)}>
  {pic}
  <div class="body">
    <p class="tag">{num}<span class="code">{code}</span>{e(name)}</p>
    <h3>{e(item["title"])}</h3>
    <p class="dek">{e(item["summary"])}</p>
    {source_link(item)}
  </div>
</article>"""


def row(item, imgs):
    imgs.tally(item["url"])
    code, name = CATS.get(item.get("category", "world"), ("INT", "國際"))
    uri, _ = imgs.get(item["url"], "sq")
    thumb = (
        f'<img src="{uri}" alt="" loading="lazy" decoding="async">'
        if uri else f'<span class="blank sm" aria-hidden="true">{code}</span>'
    )
    return f"""<a class="row" href="{e(item["url"])}" target="_blank" rel="noopener"{attrs(item)}>
  <span class="n">{item["rank"]}</span>
  <span class="rthumb">{thumb}</span>
  <span class="rtext">
    <span class="rtitle">{e(item["title"])}</span>
    <span class="rdek">{e(item["summary"])}</span>
    <span class="rmeta"><span class="code">{code}</span>{e(name)}<i>·</i>{e(item["source"])}</span>
  </span>
</a>"""


def market_card(item, imgs):
    imgs.tally(item["url"])
    glyph, label = SENT.get(item["sentiment"], SENT["neutral"])
    uri, _ = imgs.get(item["url"], "md")
    pic = (
        f'<span class="mpic"><img src="{uri}" alt="" loading="lazy" decoding="async"></span>'
        if uri else ""
    )
    chips = "".join(f'<span class="tick">{e(t)}</span>' for t in item["tickers"])
    return f"""<article class="mcard s-{e(item["sentiment"])}"{' data-cat="market" data-q="' + e((item["title"] + item["summary"] + " ".join(item["tickers"])).lower()) + '"'}>
  {pic}
  <div class="mbody">
    <p class="mtop">
      <span class="sent"><i aria-hidden="true">{glyph}</i>{label}</span>
      <span class="mkt">{e(item["market"])}</span>
      <span class="ind">{e(item["industry"])}</span>
    </p>
    <h3>{e(item["title"])}</h3>
    <p class="dek">{e(item["summary"])}</p>
    <p class="why"><span>判斷依據</span>{e(item["reason"])}</p>
    <p class="ticks">{chips}</p>
    <a class="src" href="{e(item["url"])}" target="_blank" rel="noopener">原始報導<span class="ext" aria-hidden="true">↗</span></a>
  </div>
</article>"""


def cascade(items, imgs, label, n_lead=3, n_mid=7):
    lead, mid, rest = items[:n_lead], items[n_lead:n_lead + n_mid], items[n_lead + n_mid:]
    out = [f'<h3 class="tier">頭條<span>#1–{n_lead}</span></h3>',
           '<div class="grid-3">',
           *[big_card(i, imgs, "lg", "card feature", i["rank"]) for i in lead],
           "</div>"]
    if mid:
        out += [f'<h3 class="tier">重點<span>#{n_lead+1}–{n_lead+len(mid)}</span></h3>',
                '<div class="grid-auto">',
                *[big_card(i, imgs, "lg", "card", i["rank"]) for i in mid],
                "</div>"]
    if rest:
        out += [f'<h3 class="tier">其餘<span>#{rest[0]["rank"]}–{rest[-1]["rank"]}</span></h3>',
                '<div class="rows">', *[row(i, imgs) for i in rest], "</div>"]
    return "\n".join(out)


# ── 樣式 ────────────────────────────────────────────────────────────────
CSS = """
:root{
  --paper:#F1F2F5; --card:#FFFFFF; --sunk:#E7E9EE;
  --ink:#131A26; --ink2:#5A6373; --ink3:#8892A3;
  --rule:#DCDFE6; --rule-hard:#131A26;
  --accent:#D81E5B; --accent-soft:rgba(216,30,91,.10);
  --bull:#0E7A5A; --bear:#C0392E; --flat:#6B7280;
  --shadow:0 1px 1px rgba(19,26,38,.05), 0 12px 24px -18px rgba(19,26,38,.35);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#0E131C; --card:#161C28; --sunk:#1D2532;
    --ink:#EDEFF3; --ink2:#97A1B2; --ink3:#6E7889;
    --rule:#2A3242; --rule-hard:#4A5568;
    --accent:#FF5C8A; --accent-soft:rgba(255,92,138,.14);
    --bull:#269C77; --bear:#D95346; --flat:#8A94A6;
    --shadow:0 1px 1px rgba(0,0,0,.5), 0 14px 28px -20px rgba(0,0,0,.8);
  }
}
:root[data-theme="dark"]{
  --paper:#0E131C; --card:#161C28; --sunk:#1D2532;
  --ink:#EDEFF3; --ink2:#97A1B2; --ink3:#6E7889;
  --rule:#2A3242; --rule-hard:#4A5568;
  --accent:#FF5C8A; --accent-soft:rgba(255,92,138,.14);
  --bull:#269C77; --bear:#D95346; --flat:#8A94A6;
  --shadow:0 1px 1px rgba(0,0,0,.5), 0 14px 28px -20px rgba(0,0,0,.8);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif;
  font-size:16px; line-height:1.62; -webkit-font-smoothing:antialiased;
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
h1,h2,h3,h4{margin:0; text-wrap:balance; font-weight:700}
a{color:inherit; text-decoration:none}
:focus-visible{outline:2.5px solid var(--accent); outline-offset:3px; border-radius:3px}
img{display:block; max-width:100%}

.wrap{max-width:1240px; margin:0 auto; padding:0 clamp(16px,3vw,32px)}
.mono{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,monospace; font-variant-numeric:tabular-nums}

/* ── 報頭 ── */
.masthead{background:var(--card); border-bottom:3px solid var(--rule-hard)}
.mh{display:flex; align-items:flex-end; justify-content:space-between; gap:20px;
    flex-wrap:wrap; padding:clamp(18px,3vw,30px) 0 14px}
.brand{display:flex; align-items:center; gap:14px}
.brand svg{width:46px; height:46px; flex:none; color:var(--accent)}
.brand h1{font-family:"Noto Serif TC",serif; font-weight:900;
          font-size:clamp(1.9rem,5vw,2.9rem); letter-spacing:.04em; line-height:1}
.brand .latin{display:block; font-family:"Archivo",system-ui,sans-serif; font-weight:700;
  font-stretch:82%; font-size:.62rem; letter-spacing:.34em; color:var(--ink3);
  text-transform:uppercase; margin-top:7px}
.dateline{text-align:right; font-size:.78rem; color:var(--ink2); line-height:1.7}
.dateline b{display:block; color:var(--ink); font-size:.95rem; font-weight:600}
.stamp{display:flex; align-items:center; justify-content:flex-end; gap:7px; flex-wrap:wrap;
       margin:3px 0 1px}
.stamp time{color:var(--ink); font-weight:600}
.ago{display:inline-flex; align-items:center; gap:5px; padding:1px 8px; border-radius:999px;
  font-size:.72rem; font-weight:600; color:var(--bull);
  background:color-mix(in srgb, var(--bull) 13%, transparent)}
.ago::before{content:""; width:6px; height:6px; border-radius:50%; background:currentColor}
.ago.stale{color:var(--bear); background:color-mix(in srgb, var(--bear) 13%, transparent)}
.ago:empty{display:none}
.nth{font-size:.72rem; color:var(--ink3); cursor:help}

/* ── 工具列 ── */
.bar{position:sticky; top:0; z-index:40; background:var(--card);
     border-bottom:1px solid var(--rule); box-shadow:0 1px 0 rgba(0,0,0,.02)}
.bar .wrap{display:flex; align-items:center; gap:10px; padding-top:9px; padding-bottom:9px;
           overflow-x:auto; scrollbar-width:none}
.bar .wrap::-webkit-scrollbar{display:none}
.bar a{font-size:.83rem; font-weight:600; white-space:nowrap; padding:6px 12px;
       border-radius:999px; color:var(--ink2)}
.bar a:hover{background:var(--sunk); color:var(--ink)}
.bar form{margin-left:auto; display:flex; align-items:center; gap:7px; flex:none}
.bar input{
  width:min(30vw,190px); padding:6px 11px; font:inherit; font-size:.83rem;
  color:var(--ink); background:var(--paper);
  border:1px solid var(--rule); border-radius:999px;
}
.bar input::placeholder{color:var(--ink3)}
.hit{font-size:.75rem; color:var(--ink3); white-space:nowrap}

/* ── 段落 ── */
main{padding:clamp(26px,4vw,44px) 0 80px}
section{margin-bottom:clamp(44px,6vw,72px); scroll-margin-top:64px}
.shead{display:flex; align-items:flex-end; justify-content:space-between; gap:18px;
       flex-wrap:wrap; padding-bottom:11px; border-bottom:2.5px solid var(--rule-hard); margin-bottom:22px}
.shead h2{font-family:"Noto Serif TC",serif; font-size:clamp(1.4rem,3.2vw,1.95rem); font-weight:900}
.eyebrow{display:block; font-family:"Archivo",system-ui,sans-serif; font-weight:700;
  font-stretch:82%; font-size:.66rem; letter-spacing:.26em; text-transform:uppercase;
  color:var(--accent); margin-bottom:6px}
.shead p{margin:0; font-size:.86rem; color:var(--ink2); max-width:46ch}
.tier{display:flex; align-items:center; gap:11px; margin:30px 0 15px;
      font-size:.95rem; font-weight:700; color:var(--ink)}
.tier::after{content:""; flex:1; height:1px; background:var(--rule)}
.tier span{font-family:"IBM Plex Mono",monospace; font-size:.72rem; font-weight:500;
           color:var(--ink3); font-variant-numeric:tabular-nums}
.tier:first-child{margin-top:0}

/* ── 圖框（含字幕條） ── */
.frame{position:relative; display:block; aspect-ratio:16/9; overflow:hidden;
       background:var(--sunk); border-radius:3px}
.frame img{width:100%; height:100%; object-fit:cover}
/* 排名數字壓在照片左上角，底下墊一小塊漸層才讀得到，不蓋住畫面主體 */
.frame .lower{position:absolute; inset:0 auto auto 0; width:38%; height:34%;
  background:linear-gradient(135deg, rgba(8,12,20,.55), rgba(8,12,20,0) 78%);
  pointer-events:none}
.bug{position:absolute; top:8px; right:8px; z-index:2; font-size:.62rem; font-weight:700;
  letter-spacing:.06em; color:#fff; background:var(--accent); padding:3px 7px; border-radius:2px}
.bug.art{background:rgba(8,12,20,.7); backdrop-filter:blur(2px)}
.rk{position:absolute; top:6px; left:11px; z-index:2;
  font-family:"Noto Serif TC",serif; font-weight:900;
  font-size:2.1rem; line-height:1; color:#fff; -webkit-text-stroke:1.5px rgba(8,12,20,.85);
  paint-order:stroke fill; font-variant-numeric:tabular-nums}
.blank{position:absolute; inset:0; display:grid; place-items:center;
  font-family:"Archivo",system-ui,sans-serif; font-weight:700; font-stretch:82%;
  font-size:.7rem; letter-spacing:.08em; color:var(--ink3); opacity:.55}

/* 無圖稿：不留空框，改用粗上緣線 + 放大的標題 */
.card.textonly{border-top:3px solid var(--accent)}
.card.textonly .body{padding-top:14px}
.card.textonly h3{font-family:"Noto Serif TC",serif; font-weight:700; font-size:1.1rem; line-height:1.5}
.card.hero.textonly h3{font-size:clamp(1.25rem,2.2vw,1.55rem)}
.inline-rk{font-family:"IBM Plex Mono",monospace; font-size:.72rem; font-weight:600;
  color:var(--ink3); font-variant-numeric:tabular-nums}
.inline-rk::after{content:"／"; opacity:.4; margin-left:3px}

/* ── 卡片 ── */
.grid-3{display:grid; grid-template-columns:repeat(3,1fr); gap:20px}
.grid-auto{display:grid; grid-template-columns:repeat(auto-fill,minmax(228px,1fr)); gap:18px}
.lead-grid{display:grid; grid-template-columns:1.55fr 1fr; gap:22px; align-items:start}
.lead-side{display:grid; gap:22px}
@media (max-width:880px){
  .grid-3,.lead-grid{grid-template-columns:1fr}
}
.card{background:var(--card); border:1px solid var(--rule); border-radius:4px;
      overflow:hidden; box-shadow:var(--shadow); display:flex; flex-direction:column}
.card .body{padding:15px 17px 17px; display:flex; flex-direction:column; gap:7px; flex:1}
.card h3{font-size:1.02rem; line-height:1.45}
.card.feature h3{font-size:1.14rem}
.card .dek{margin:0; font-size:.865rem; color:var(--ink2); line-height:1.6}
.tag{display:flex; align-items:center; gap:7px; margin:0;
     font-size:.72rem; font-weight:600; color:var(--ink2); letter-spacing:.02em}
.code{font-family:"IBM Plex Mono",monospace; font-size:.66rem; font-weight:600;
  letter-spacing:.08em; color:var(--accent); background:var(--accent-soft);
  padding:2px 6px; border-radius:2px}
.src{margin-top:auto; padding-top:9px; font-size:.79rem; font-weight:600; color:var(--ink2)}
.src:hover{color:var(--accent)}
.ext{margin-left:3px; font-size:.7em; opacity:.7}

/* 今日焦點：一大兩小 */
.card.hero{border-width:1px}
.card.hero h3{font-family:"Noto Serif TC",serif; font-weight:900;
  font-size:clamp(1.35rem,2.5vw,1.75rem); line-height:1.38}
.card.hero .body{padding:20px 24px 24px; gap:9px}
.card.hero .dek{font-size:.95rem}
.card.hero .rk{font-size:3.2rem}

/* ── 清單 ── */
.rows{display:grid; grid-template-columns:repeat(2,1fr); gap:0 34px}
@media (max-width:760px){.rows{grid-template-columns:1fr}}
.row{display:flex; gap:13px; padding:13px 6px; border-bottom:1px solid var(--rule); align-items:flex-start}
.row:hover{background:var(--card)}
.row:hover .rtitle{color:var(--accent)}
.n{flex:none; width:26px; padding-top:2px; font-family:"IBM Plex Mono",monospace;
   font-size:.82rem; font-weight:600; color:var(--ink3); font-variant-numeric:tabular-nums}
.rthumb{position:relative; flex:none; width:58px; height:58px; border-radius:3px;
        overflow:hidden; background:var(--sunk)}
.rthumb img{width:100%; height:100%; object-fit:cover}
.rtext{display:flex; flex-direction:column; gap:3px; min-width:0}
.rtitle{font-size:.92rem; font-weight:600; line-height:1.45}
.rdek{font-size:.8rem; color:var(--ink2); line-height:1.5;
      display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden}
.rmeta{display:flex; align-items:center; gap:6px; font-size:.71rem; color:var(--ink3); flex-wrap:wrap}
.rmeta i{font-style:normal; opacity:.5}

/* ── 股市 ── */
.msum{display:flex; align-items:center; gap:16px; flex-wrap:wrap; margin-bottom:20px;
      padding:12px 16px; background:var(--card); border:1px solid var(--rule); border-radius:4px}
.msum b{font-size:.8rem; font-weight:600; color:var(--ink2)}
.msum .item{display:flex; align-items:center; gap:6px; font-size:.82rem; font-weight:600}
.msum .item i{font-style:normal; font-size:.75rem}
.msum .n2{font-family:"IBM Plex Mono",monospace; color:var(--ink2); font-weight:500}
.mlist{display:grid; gap:16px}
.mcard{display:grid; grid-template-columns:210px 1fr; gap:0;
  background:var(--card); border:1px solid var(--rule); border-left-width:6px;
  border-radius:4px; overflow:hidden; box-shadow:var(--shadow)}
.mcard:not(:has(.mpic)){grid-template-columns:1fr}
@media (max-width:700px){.mcard{grid-template-columns:1fr}}
.mpic{display:block; position:relative; background:var(--sunk)}
.mpic img{width:100%; height:100%; object-fit:cover; min-height:150px}
.mbody{padding:15px 19px 17px; display:flex; flex-direction:column; gap:7px}
.mbody h3{font-size:1.04rem; line-height:1.45}
.mtop{display:flex; align-items:center; gap:9px; margin:0; flex-wrap:wrap}
.sent{display:inline-flex; align-items:center; gap:5px; font-size:.76rem; font-weight:700;
      padding:2px 9px; border-radius:2px}
.sent i{font-style:normal; font-size:.68rem}
.mkt{font-size:.72rem; font-weight:700; color:var(--ink); background:var(--sunk);
     padding:2px 8px; border-radius:2px}
.ind{font-size:.74rem; color:var(--ink3)}
.s-bull{border-left-color:var(--bull)}
.s-bear{border-left-color:var(--bear)}
.s-neutral{border-left-color:var(--flat)}
.s-bull .sent{color:var(--bull); background:color-mix(in srgb, var(--bull) 12%, transparent)}
.s-bear .sent{color:var(--bear); background:color-mix(in srgb, var(--bear) 12%, transparent)}
.s-neutral .sent{color:var(--flat); background:color-mix(in srgb, var(--flat) 14%, transparent)}
.why{margin:0; font-size:.83rem; color:var(--ink2); line-height:1.6;
     padding:9px 12px; background:var(--paper); border-radius:3px}
.why span{display:block; font-family:"IBM Plex Mono",monospace; font-size:.64rem;
  font-weight:600; letter-spacing:.12em; color:var(--ink3); margin-bottom:2px}
.ticks{display:flex; flex-wrap:wrap; gap:6px; margin:0}
.tick{font-family:"IBM Plex Mono",monospace; font-size:.71rem; color:var(--ink2);
  border:1px solid var(--rule); padding:2px 7px; border-radius:2px}

/* ── 篩選 ── */
[hidden]{display:none!important}
.empty{padding:40px 0; text-align:center; color:var(--ink3); font-size:.9rem}

footer{border-top:2.5px solid var(--rule-hard); padding:22px 0 44px; background:var(--card)}
footer .wrap{display:grid; gap:8px; font-size:.78rem; color:var(--ink2); line-height:1.65}
footer b{color:var(--ink); font-weight:600}
"""

JS = """
(function(){
  // 更新時間離現在多久 —— 一開電腦就知道這頁是不是今天的
  var t = document.getElementById('upd'), ago = document.getElementById('ago');
  function freshness(){
    if(!t || !ago) return;
    var mins = Math.round((Date.now() - new Date(t.dateTime).getTime()) / 60000);
    var txt;
    if(mins < 2) txt = '剛剛';
    else if(mins < 60) txt = mins + ' 分鐘前';
    else if(mins < 1440) txt = Math.round(mins / 60) + ' 小時前';
    else txt = Math.round(mins / 1440) + ' 天前';
    if(mins > 20*60) txt += '，可能不是最新的';
    ago.textContent = txt;
    ago.classList.toggle('stale', mins > 20 * 60);   // 超過 20 小時就標紅
    ago.title = mins > 20 * 60 ? '這份內容已經超過 20 小時沒更新' : '';
  }
  freshness();
  setInterval(freshness, 60000);
  document.addEventListener('visibilitychange', freshness);  // 從睡眠喚醒後立刻重算

  var q = document.getElementById('q');
  var hit = document.getElementById('hit');
  if(!q) return;
  var items = Array.prototype.slice.call(document.querySelectorAll('[data-q]'));
  var total = items.length;
  function apply(){
    var t = q.value.trim().toLowerCase();
    var n = 0;
    items.forEach(function(el){
      var show = !t || el.getAttribute('data-q').indexOf(t) !== -1;
      el.hidden = !show;
      if(show) n++;
    });
    document.querySelectorAll('section').forEach(function(s){
      var any = s.querySelector('[data-q]:not([hidden])');
      s.hidden = t ? !any : false;
    });
    hit.textContent = t ? n + ' / ' + total + ' 則' : total + ' 則';
  }
  q.addEventListener('input', apply);
  q.addEventListener('keydown', function(ev){ if(ev.key === 'Escape'){ q.value=''; apply(); } });
  apply();
})();
"""

PIG = ('<svg viewBox="0 0 64 64" aria-hidden="true">'
       '<path d="M13 20 L11 8 L24 15 Z" fill="currentColor"/>'
       '<path d="M51 20 L53 8 L40 15 Z" fill="currentColor"/>'
       '<ellipse cx="32" cy="35" rx="25" ry="22" fill="currentColor"/>'
       '<ellipse cx="32" cy="41" rx="10" ry="8" fill="rgba(0,0,0,.32)"/>'
       '<ellipse cx="28.4" cy="41" rx="2.3" ry="3" fill="rgba(0,0,0,.55)"/>'
       '<ellipse cx="35.6" cy="41" rx="2.3" ry="3" fill="rgba(0,0,0,.55)"/>'
       '<ellipse cx="22" cy="27" rx="3.4" ry="4" fill="rgba(0,0,0,.55)"/>'
       '<ellipse cx="42" cy="27" rx="3.4" ry="4" fill="rgba(0,0,0,.55)"/></svg>')


def stamp(date, path):
    """記下這次更新的時間，並回傳（資料, 本次時間, 當天累計更新次數）。

    只有內容真的變了才算一次更新 —— 重跑組版、調版面不該讓次數灌水，
    不然「今日第 5 次」就失去意義了。LITE 排版檢查更是完全不寫入。
    """
    data = json.load(open(path, encoding="utf-8"))
    body = {k: v for k, v in data.items() if k not in ("updates", "fingerprint")}
    fp = hashlib.sha1(
        json.dumps(body, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()

    now = datetime.now().astimezone()
    changed = fp != data.get("fingerprint")
    if changed and not LITE:
        data.setdefault("updates", []).append(now.isoformat(timespec="seconds"))
        data["fingerprint"] = fp
        json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    elif data.get("updates"):
        # 內容沒變，時間就沿用上次真正更新的時間，不要謊報新鮮度
        now = datetime.fromisoformat(data["updates"][-1])
    return data, now, max(len(data.get("updates", [])), 1)


def build(date):
    path = os.path.join(ROOT, "data", f"{date}.json")
    data, now, nth = stamp(date, path)
    imgs = Images()
    d = datetime.strptime(date, "%Y-%m-%d")
    pretty = f"{d.year}年{d.month}月{d.day}日（星期{WEEKDAY[d.weekday()]}）"
    times = [t[11:16] for t in data.get("updates", [])]
    log = "　".join(times[-8:])
    nth_html = (f'<span class="nth" title="今日更新時間：{e(log)}">今日第 {nth} 次</span>'
                if nth > 1 else "")

    top = data["top3"]
    top_html = f"""<div class="lead-grid">
  {big_card(top[0], imgs, "xl", "card hero", 1)}
  <div class="lead-side">
    {big_card(top[1], imgs, "lg", "card hero", 2)}
    {big_card(top[2], imgs, "lg", "card hero", 3)}
  </div>
</div>"""

    counts = {"bull": 0, "bear": 0, "neutral": 0}
    for m in data["market"]:
        counts[m["sentiment"]] = counts.get(m["sentiment"], 0) + 1
    msum = "".join(
        f'<span class="item s-{k}" style="color:var(--{ {"bull":"bull","bear":"bear","neutral":"flat"}[k] })">'
        f'<i aria-hidden="true">{SENT[k][0]}</i>{SENT[k][1]}'
        f'<span class="n2">{counts.get(k,0)}</span></span>'
        for k in ("bull", "bear", "neutral")
    )

    total = len(data["top3"]) + len(data["global"]) + len(data["twcn"]) + len(data["market"])

    html = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>豬豬日報</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@700;900&family=Noto+Sans+TC:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Archivo:wdth,wght@75..100,600;700&display=swap">
<style>{CSS}</style>

<header class="masthead">
  <div class="wrap mh">
    <div class="brand">
      {PIG}
      <h1>豬豬日報<span class="latin">Pig Daily · Global Wire</span></h1>
    </div>
    <div class="dateline mono">
      <b>{pretty}</b>
      <span class="stamp">
        <time id="upd" datetime="{now.isoformat(timespec="seconds")}">{now:%H:%M}</time> 更新
        <span class="ago" id="ago"></span>{nth_html}
      </span>
      共 {total} 則
    </div>
  </div>
</header>

<nav class="bar">
  <div class="wrap">
    <a href="#top3">今日焦點</a>
    <a href="#global">全球 50</a>
    <a href="#twcn">台灣・中國 30</a>
    <a href="#market">股市影響</a>
    <form onsubmit="return false">
      <input id="q" type="search" placeholder="搜尋標題、來源…" aria-label="搜尋今日新聞">
      <span class="hit mono" id="hit"></span>
    </form>
  </div>
</nav>

<main class="wrap">
  <section id="top3">
    <div class="shead">
      <div><span class="eyebrow">Top Stories</span><h2>今日焦點</h2></div>
      <p>當下影響力最大的三則，優先掌握。</p>
    </div>
    {top_html}
  </section>

  <section id="global">
    <div class="shead">
      <div><span class="eyebrow">Global · Top 50</span><h2>全球熱度前 50</h2></div>
      <p>依報導量、社群討論度與搜尋趨勢排序，涵蓋國際、財經、科技、社會各領域。</p>
    </div>
    {cascade(data["global"], imgs, "global")}
  </section>

  <section id="twcn">
    <div class="shead">
      <div><span class="eyebrow">Taiwan · Mainland China</span><h2>台灣・中國大陸前 30</h2></div>
      <p>兩岸在地熱度排行，與全球榜分開計算。</p>
    </div>
    {cascade(data["twcn"], imgs, "twcn")}
  </section>

  <section id="market">
    <div class="shead">
      <div><span class="eyebrow">Markets · 台股／美股</span><h2>產業與股市影響</h2></div>
      <p>從今日新聞中篩出可能牽動台股或美股的消息，標示多空傾向與判斷依據。</p>
    </div>
    <div class="msum"><b>今日多空分布</b>{msum}</div>
    <div class="mlist">
      {"".join(market_card(m, imgs) for m in data["market"])}
    </div>
  </section>
</main>

<footer>
  <div class="wrap">
    <div><b>關於配圖</b>　優先採用各則新聞原始報導所附的照片；原站無圖或擋抓取者，改用依標題製作的示意圖並標註「示意圖」，兩者皆非本站拍攝。所有畫面均掛「豬豬日報」標記，不使用任何電視台識別或直播時間戳。</div>
    <div><b>關於內容</b>　由 AI 彙整自各大新聞媒體公開報導，以摘要呈現，完整內容請點擊各則連結查看原始報導。</div>
    <div><b>關於股市段落</b>　僅為新聞面觀察整理，非投資建議，盈虧請自行判斷並承擔。</div>
  </div>
</footer>
<script>{JS}</script>
"""
    out = os.path.join(ROOT, "dist", f"{date}{'-lite' if LITE else ''}.html")
    open(out, "w", encoding="utf-8").write(html)
    kb = os.path.getsize(out) / 1024
    s = imgs.stats
    print(f"→ {out}  {kb:,.0f} KB")
    print(f"   配圖：AI 圖 {s['manual']}　真實照片 {s['photo']}　無圖 {s['none']}")
    return out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d"))
