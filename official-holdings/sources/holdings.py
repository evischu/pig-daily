"""讀取申報持股 CSV。本人、配偶、子女的持股分開列，不合併。

CSV 欄位：
  issue          廉政專刊期別，例如 第 290 期
  declare_date   申報日 YYYY-MM-DD
  official       官員姓名
  title          職稱，例如 立法委員
  committee      所屬委員會（經濟／財政／交通…，對應 config.COMMITTEE_INDUSTRIES）
  owner          所有人：本人／配偶／子女
  owner_name     （選填）配偶、子女的姓名
  stock_name     申報表上的股票名稱
  stock_code     股票代號（可留空，會用名稱自動比對）
  shares         股數
"""
import csv


def load(path, name_to_code):
    """每個「官員 × 持有人（本人／配偶／子女）× 個股」各一列，不合併。
    同一持有人同一檔股票若在申報表分成多筆，才會加總成一列。"""
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    merged = {}
    unmatched = set()
    for r in rows:
        code = (r.get("stock_code") or "").strip() or name_to_code.get(r["stock_name"].strip())
        if not code:
            unmatched.add(r["stock_name"])
            continue
        key = (r["official"].strip(), r["owner"].strip(), code)
        if key not in merged:
            merged[key] = {"official": key[0], "owner": key[1], "code": code,
                           "owner_name": (r.get("owner_name") or "").strip(),
                           "title": r["title"], "committee": r["committee"],
                           "issue": r["issue"], "declare_date": r["declare_date"], "shares": 0}
        merged[key]["shares"] += int(float(r["shares"]))
    return list(merged.values()), sorted(unmatched)
