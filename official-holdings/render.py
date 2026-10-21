"""產出自給自足的單一 HTML 看板。"""
from html import escape as e

import re

from config import CONCENTRATION_MIN, TOP_N

TOKENS = """
/* 版面：上方今日異動摘要 → 三榜分頁表格 → 集中持股 → 方法說明 */
:root{
  --bg:#f4f5f7; --surface:#ffffff; --ink:#18202e; --muted:#5d6676; --line:#dfe2e8;
  --accent:#2f4b8f; --accent-soft:#e6ebf6;
  --up:#c8322b; --down:#1d7f4a; --flag:#a8670f; --flag-soft:#f8eedc; --warn-soft:#fbe9e7;
  --f-display:"Noto Serif TC","Songti TC",serif;
  --f-body:"Noto Sans TC","PingFang TC","Microsoft JhengHei",sans-serif;
  --f-num:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --bg:#11151c; --surface:#181e27; --ink:#e6e9ef; --muted:#9aa3b2; --line:#2a323f;
  --accent:#8fa8e6; --accent-soft:#1f2a40; --up:#ff6b5f; --down:#4fc58a;
  --flag:#e3a548; --flag-soft:#33281a; --warn-soft:#3a201e; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#11151c; --surface:#181e27; --ink:#e6e9ef; --muted:#9aa3b2; --line:#2a323f;
  --accent:#8fa8e6; --accent-soft:#1f2a40; --up:#ff6b5f; --down:#4fc58a;
  --flag:#e3a548; --flag-soft:#33281a; --warn-soft:#3a201e; color-scheme:dark}
body{background:var(--bg);color:var(--ink);font-family:var(--f-body);line-height:1.55}
"""

COMPONENTS = """.wrap{max-width:1180px;margin:0 auto;padding-block:28px 56px;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));
  display:grid;gap:28px}
header{display:grid;gap:6px}
h1{font-family:var(--f-display);font-weight:900;font-size:clamp(26px,4vw,36px);margin:0;letter-spacing:.02em;text-wrap:balance}
h2{font-size:18px;margin:0;text-wrap:balance}
.bh{font-size:17px;margin:0}
.meta{color:var(--muted);font-size:13px;display:flex;flex-wrap:wrap;gap:4px 16px}
.num{font-family:var(--f-num);font-variant-numeric:tabular-nums}
.demo{background:var(--warn-soft);border:1px solid var(--up);color:var(--ink);padding:10px 14px;border-radius:6px;font-size:13px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.kpi{background:var(--surface);padding:14px 16px;display:grid;gap:2px}
.kpi b{font-family:var(--f-num);font-size:24px;font-weight:600}
.kpi span{color:var(--muted);font-size:12px;letter-spacing:.04em}
.changes{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}
.chg{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:14px 16px;display:grid;gap:8px;min-width:0;align-content:start}
.wrap>*,.blk>*{min-width:0}
.chg h3{margin:0;font-size:14px;display:flex;justify-content:space-between;gap:8px}
.chg ul{margin:0;padding:0;list-style:none;display:grid;gap:4px;font-size:13px}
.chg li{display:flex;gap:6px;align-items:baseline;flex-wrap:wrap}
.chg .none{color:var(--muted);font-size:13px}
.pill{display:inline-block;font-size:11px;font-weight:700;padding:1px 7px;border-radius:999px;white-space:nowrap;letter-spacing:.03em}
.p-new{background:var(--accent);color:var(--surface)}
.p-out{background:var(--line);color:var(--muted)}
.p-conc{background:var(--flag-soft);color:var(--flag);text-decoration:none}
.p-conc:hover{outline:1px solid var(--flag)}
.p-rel{border:1px solid var(--accent);color:var(--accent)}
.up{color:var(--up)} .down{color:var(--down)} .flat{color:var(--muted)}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);flex-wrap:wrap}
.tabs button{font:inherit;font-size:14px;background:none;border:0;border-bottom:3px solid transparent;color:var(--muted);padding:10px 14px;cursor:pointer}
.tabs button[aria-selected="true"]{color:var(--ink);border-bottom-color:var(--accent);font-weight:700}
.tabs button:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.tabs small{font-family:var(--f-num);margin-left:6px;color:var(--accent)}
.tablebox{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-top:0;border-radius:0 0 8px 8px}
table{border-collapse:collapse;width:100%;min-width:900px;font-size:13.5px}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{font-size:12px;color:var(--muted);font-weight:600;letter-spacing:.04em;background:var(--surface);position:sticky;top:0}
td.r,th.r{text-align:right}
th.sort{color:var(--accent)} td.sort{font-weight:700;background:var(--accent-soft)}
tr.isnew td:first-child{box-shadow:inset 3px 0 0 var(--accent)}
.rank{font-family:var(--f-num);font-size:16px;font-weight:700}
.sub{display:block;color:var(--muted);font-size:12px}
.tags{display:flex;gap:4px;flex-wrap:wrap}
.dropped{padding:10px 12px;font-size:12.5px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px 14px}
.conc table{min-width:760px}
.who{display:flex;flex-wrap:wrap;gap:4px}
.nm b{font-size:15px}
.own{font-size:12px;border:1px solid var(--line);border-radius:4px;padding:1px 7px;white-space:nowrap}
.own.o-配偶,.own.o-子女{border-style:dashed}
.who span{font-size:12px;border:1px solid var(--line);border-radius:4px;padding:0 6px;white-space:nowrap}
.who span.rel{border-color:var(--accent);color:var(--accent)}
.bar{height:6px;background:var(--flag);border-radius:3px;margin-top:4px}
.blk{display:grid;gap:12px;min-width:0}
.note{color:var(--muted);font-size:12.5px;display:grid;gap:4px;max-width:75ch}
.note p{margin:0}
:target{scroll-margin-top:16px}
tr:target td{background:var(--flag-soft)}
"""


def scope(css, prefix=".oh"):
    """把元件樣式的每個選擇器加上前綴，避免嵌進豬豬日報時污染原本的樣式。"""
    def one(m):
        sels = ",".join(f"{prefix} {x.strip()}" for x in m.group(1).split(","))
        return f"{sels}{{{m.group(2)}}}"
    return re.sub(r"([^{}]+)\{([^{}]*)\}", one, css)


# 嵌入豬豬日報時，沿用日報的色票與字型
EMBED_TOKENS = """
.oh{min-width:0; max-width:100%; --surface:var(--card); --bg:var(--paper); --line:var(--rule); --muted:var(--ink2);
  --up:#C8322B; --down:#1D7F4A; --flag:#A8670F; --flag-soft:#F8EEDC; --warn-soft:#FBE9E7;
  --f-display:"Noto Serif TC",serif; --f-body:"Noto Sans TC",sans-serif; --f-num:"IBM Plex Mono",monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .oh{
  --up:#FF6B5F; --down:#4FC58A; --flag:#E3A548; --flag-soft:#33281A; --warn-soft:#3A201E}}
:root[data-theme="dark"] .oh{--up:#FF6B5F; --down:#4FC58A; --flag:#E3A548; --flag-soft:#33281A; --warn-soft:#3A201E}
"""

COMPONENTS_EMBED = "\n".join(
    l for l in COMPONENTS.splitlines()
    if not l.startswith((".wrap{", "header{", "h1{", ".wrap>*", "h2{")) and not l.startswith("  padding-left:max")
    and not l.startswith("  display:grid;gap:28px"))
COMPONENTS_EMBED += """
.bh{font-size:1.02rem;margin:0}
.blk>*{min-width:0}
"""

JS = """
(()=>{const tabs=[...document.querySelectorAll('.oh .tabs button')];
tabs.forEach(b=>b.addEventListener('click',()=>tabs.forEach(t=>{const on=t===b;t.setAttribute('aria-selected',on);
  document.getElementById('board-'+t.dataset.board).hidden=!on})));})();
"""


def money(v):
    if v >= 1e8:
        return f"{v / 1e8:,.2f} 億"
    return f"{v / 1e4:,.0f} 萬"


def lots(x):
    return f"{x:,.0f}" if x == int(x) else f"{x:,.1f}"


def stake(x):
    return "—" if x is None else (f"{x:.3f}%" if x >= 0.001 else "<0.001%")


def pct_change(close, prev):
    if not prev:
        return '<span class="flat">—</span>'
    p = (close - prev) / prev * 100
    cls = "up" if p > 0 else "down" if p < 0 else "flat"
    sign = "▲" if p > 0 else "▼" if p < 0 else ""
    return f'<span class="{cls} num">{sign}{abs(p):.2f}%</span>'


def move(entry):
    if entry["is_new"]:
        return '<span class="pill p-new">NEW</span>'
    p = entry["prev_rank"]
    if p is None:
        return '<span class="flat">—</span>'
    d = p - entry["rank"]
    if d > 0:
        return f'<span class="up num">▲{d}</span>'
    if d < 0:
        return f'<span class="down num">▼{-d}</span>'
    return '<span class="flat">—</span>'


def owner_label(x):
    name = x.get("owner_name")
    return f'{x["owner"]}（{name}）' if name else x["owner"]


def who(x):
    """「官員姓名・持有人」，用在異動摘要與跌出名單。"""
    return f'{x["official"]}（{owner_label(x)}）'


def board_table(bid, board):
    sort_col = {"value": "value", "lots": "lots", "stake": "stake"}[bid]

    def th(col, label):
        return f'<th class="r{" sort" if col == sort_col else ""}">{label}</th>'

    def td(col, html):
        return f'<td class="r num{" sort" if col == sort_col else ""}">{html}</td>'

    rows = []
    for x in board["entries"]:
        tags = []
        if x["co_holders"]:
            tags.append(f'<a class="pill p-conc" href="#c-{e(x["code"])}">{x["co_holders"]} 人共持</a>')
        if x["related"]:
            tags.append('<span class="pill p-rel">職掌相關</span>')
        rows.append(f"""<tr class="{'isnew' if x['is_new'] else ''}">
<td class="rank">{x['rank']}</td><td>{move(x)}</td>
<td class="nm"><b>{e(x['official'])}</b><span class="sub">{e(x['title'])}・{e(x['committee'])}委員會</span></td>
<td><span class="own o-{e(x['owner'])}">{e(owner_label(x))}</span></td>
<td><b>{e(x['code'])} {e(x['name'])}</b><span class="sub">{e(x['market'])}・{e(x['industry'])}</span></td>
{td('lots', lots(x['lots']))}{td('value', money(x['value']))}{td('stake', stake(x['stake']))}
<td class="r"><span class="num">{x['close']:,.1f}</span><span class="sub">{pct_change(x['close'], x['prev_close'])}</span></td>
<td><div class="tags">{''.join(tags)}</div></td></tr>""")
    dropped = "".join(
        f'<span><span class="pill p-out">跌出</span> {e(who(d))}・{e(d["code"])} {e(d.get("name", ""))}（原第 {d["prev_rank"]} 名）</span>'
        for d in board["dropped"])
    return f"""<div class="tablebox"><table>
<thead><tr><th>名次</th><th>變動</th><th>姓名</th><th>持有人</th><th>個股</th>
{th('lots', '張數')}{th('value', '估計市值')}{th('stake', '佔公司股權')}<th class="r">收盤</th><th>標記</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
{f'<div class="dropped">{dropped}</div>' if dropped else ''}</div>"""


def changes_card(board, has_prev):
    news = [x for x in board["entries"] if x["is_new"]]
    if not has_prev:
        body = '<p class="none">第一天執行，明天起顯示名次異動。</p>'
    elif not news and not board["dropped"]:
        body = '<p class="none">名單與前一日相同。</p>'
    else:
        items = [f'<li><span class="pill p-new">NEW</span> 第 <b class="num">{x["rank"]}</b> 名 <b>{e(x["official"])}</b>（{e(owner_label(x))}）・{e(x["code"])} {e(x["name"])}</li>' for x in news]
        items += [f'<li><span class="pill p-out">跌出</span> {e(who(d))}・{e(d["code"])} {e(d.get("name", ""))}（原第 {d["prev_rank"]} 名）</li>' for d in board["dropped"]]
        body = f"<ul>{''.join(items)}</ul>"
    return f"""<div class="chg"><h3><span>{board['label']}</span>
<span class="num">新上榜 {len(news)}・跌出 {len(board['dropped'])}</span></h3>{body}</div>"""


def conc_table(conc):
    if not conc:
        return f'<p class="note">目前沒有 {CONCENTRATION_MIN} 位以上官員共同持有的個股。</p>'
    top = conc[0]["holders"]
    rows = []
    for c in conc:
        who = "".join(f'<span class="{"rel" if o["related"] else ""}"><b>{e(o["official"])}</b> {e(o["owner"])} {lots(o["lots"])}張</span>'
                      for o in c["officials"])
        rel = f'<span class="pill p-rel">{c["related"]} 人職掌相關</span>' if c["related"] else ""
        rows.append(f"""<tr id="c-{e(c['code'])}">
<td><b>{e(c['code'])} {e(c['name'])}</b><span class="sub">{e(c['industry'])}</span></td>
<td class="r num"><b>{c['holders']}</b><div class="bar" style="width:{c['holders'] / top * 100:.0f}%"></div></td>
<td class="r num">{lots(c['lots'])}</td><td class="r num">{money(c['value'])}</td>
<td class="r"><span class="num">{c['close']:,.1f}</span><span class="sub">{pct_change(c['close'], c['prev_close'])}</span></td>
<td><div class="who">{who}</div>{rel}</td></tr>""")
    return f"""<div class="tablebox conc" style="border-top:1px solid var(--line);border-radius:8px"><table>
<thead><tr><th>個股</th><th class="r">持有官員數</th><th class="r">合計張數</th><th class="r">合計市值</th><th class="r">收盤</th><th>持有官員與持有人（框線為職掌相關）</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


def inner(prev_date, boards, conc, rows, warnings):
    """榜單本體（異動摘要、前 N 名分頁、集中持股、說明），獨立頁與嵌入日報共用。"""
    tabs = "".join(
        f'<button type="button" id="tab-{bid}" data-board="{bid}" aria-selected="{str(bid == "value").lower()}">'
        f'{b["label"]}<small>{sum(x["is_new"] for x in b["entries"]) or ""}</small></button>'
        for bid, b in boards.items())
    panels = "".join(
        f'<div id="board-{bid}"{"" if bid == "value" else " hidden"}>{board_table(bid, b)}</div>'
        for bid, b in boards.items())
    warn = ""
    if warnings["unmatched"] or warnings["missing"]:
        warn = f'<p>無法對應代號的股票名稱：{e("、".join(warnings["unmatched"]) or "無")}；查無報價的代號：{e("、".join(warnings["missing"]) or "無")}。</p>'
    return f"""<div class="blk"><h3 class="bh">今日名次異動</h3><div class="changes">{''.join(changes_card(b, prev_date is not None) for b in boards.values())}</div></div>
<div class="blk"><h3 class="bh">前 {TOP_N} 名持股</h3>
<div><div class="tabs" role="tablist">{tabs}</div>{panels}</div></div>
<div class="blk"><h3 class="bh">多人集中持有的個股</h3>
<p class="note">{CONCENTRATION_MIN} 位以上官員共同持有，依持有人數排序。排行榜上的「N 人共持」標籤可直接跳到這裡。</p>
{conc_table(conc)}</div>
<div class="blk note">
<p><b>估計市值</b>＝申報股數 × 當日收盤價。申報表沒有買進成本，這不是實際投入金額。</p>
<p><b>佔公司股權</b>＝申報股數 ÷ 公司已發行普通股數。<b>職掌相關</b>：委員會職掌涵蓋該股所屬產業。</p>
<p>持股張數一年申報一次，只在新一期廉政專刊公開時改變；每日名次變化主要來自股價漲跌。依法須強制信託的官員，申報持股為信託財產，任內不得自行交易。本人、配偶、子女的持股各自一列，不合併；「持有官員數」以官員人數計。</p>
{warn}
</div>"""


def fragment(date, prev_date, boards, conc, rows, quote_source, warnings):
    """嵌進豬豬日報最下方的區塊（沿用日報的 section / shead 版型與色票）。"""
    issues = "、".join(sorted({r["issue"] for r in rows}))
    return f"""<section id="holdings" class="oh">
<style>{EMBED_TOKENS}{scope(COMPONENTS_EMBED)}</style>
<div class="shead">
  <div><span class="eyebrow">Officials' Holdings · 官員持股</span><h2>官員持股動態榜</h2></div>
  <p>監察院廉政專刊 {e(issues)} 申報持股，乘上 {e(date)} 收盤價（{e(quote_source)}）。</p>
</div>
{inner(prev_date, boards, conc, rows, warnings)}
<script>{JS}</script>
</section>"""


def page(date, prev_date, boards, conc, rows, quote_source, demo, warnings):
    issues = sorted({r["issue"] for r in rows})
    officials = len({r["official"] for r in rows})
    total_new = sum(x["is_new"] for b in boards.values() for x in b["entries"])
    demo_banner = ('<div class="demo"><b>示範資料。</b>官員為匿名代號，持股與報價皆為隨機產生，'
                   '不代表任何真實人物或行情。換上 data/holdings.csv 後即為真實版本。</div>') if demo else ""
    return f"""<title>官員持股動態榜</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Noto+Sans+TC:wght@400;700&family=Noto+Serif+TC:wght@900&display=swap">
<style>{TOKENS}{scope(COMPONENTS)}</style>
<div class="oh"><div class="wrap">
<header>
  <h1>官員持股動態榜</h1>
  <div class="meta"><span>資料日 <b class="num">{date}</b></span><span>比較基準 <span class="num">{prev_date or '—'}</span></span>
  <span>申報來源 監察院廉政專刊 {e('、'.join(issues))}</span><span>報價 {e(quote_source)}</span></div>
</header>
{demo_banner}
<div class="kpis">
  <div class="kpi"><b>{officials}</b><span>有申報持股的官員</span></div>
  <div class="kpi"><b>{len(rows)}</b><span>持股筆數（官員 × 個股）</span></div>
  <div class="kpi"><b>{len(conc)}</b><span>{CONCENTRATION_MIN} 人以上共持個股</span></div>
  <div class="kpi"><b>{total_new}</b><span>今日三榜新上榜合計</span></div>
</div>
{inner(prev_date, boards, conc, rows, warnings)}
</div></div>
<script>{JS}</script>"""
