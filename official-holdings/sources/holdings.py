"""讀取申報持股 CSV，合併同一官員同一檔股票（本人＋配偶＋子女）。

CSV 欄位：
  issue          廉政專刊期別，例如 第 290 期
  declare_date   申報日 YYYY-MM-DD
  official       官員姓名
  title          職稱，例如 立法委員
  committee      所屬委員會（經濟／財政／交通…，對應 config.COMMITTEE_INDUSTRIES）
  owner          所有人：本人／配偶／子女
  stock_name     申報表上的股票名稱
  stock_code     股票代號（可留空，會用名稱自動比對）
  shares         股數
"""
import csv
from collections import defaultdict


def load(path, name_to_code):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    merged = defaultdict(lambda: {"shares": 0, "owners": defaultdict(int)})
    unmatched = set()
    for r in rows:
        code = (r.get("stock_code") or "").strip() or name_to_code.get(r["stock_name"].strip())
        if not code:
            unmatched.add(r["stock_name"])
            continue
        key = (r["official"].strip(), code)
        m = merged[key]
        m.update(official=key[0], code=code, title=r["title"], committee=r["committee"],
                 issue=r["issue"], declare_date=r["declare_date"])
        shares = int(float(r["shares"]))
        m["shares"] += shares
        m["owners"][r["owner"]] += shares
    for m in merged.values():
        m["owners"] = dict(m["owners"])
    return list(merged.values()), sorted(unmatched)
