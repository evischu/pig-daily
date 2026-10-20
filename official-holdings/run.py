"""每日執行：抓報價 → 計算三榜 → 比對前一日 → 產出 output/index.html。

  python run.py                 # 真實資料：data/holdings.csv + 即時報價
  python run.py --demo          # 示範資料
  python run.py --demo --date 2026-10-19
"""
import argparse
import datetime as dt

import rank
import render
from config import DEMO_HOLDINGS_CSV, HOLDINGS_CSV, OUTPUT
from sources import holdings as holdings_src
from sources import market as market_src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()

    market, quote_source = market_src.get(args.date, demo=args.demo)
    name_to_code = {q["name"]: c for c, q in market.items()}
    csv_path = DEMO_HOLDINGS_CSV if args.demo else HOLDINGS_CSV
    raw, unmatched = holdings_src.load(csv_path, name_to_code)
    # 示範資料以「申報日 <= 今天」模擬新一期廉政專刊公開
    raw = [h for h in raw if h["declare_date"] <= args.date]
    rows, missing = rank.enrich(raw, market)

    boards, snapshot, prev_date = rank.build(rows, args.date)
    conc = rank.concentration(rows)
    rank.save_snapshot(args.date, snapshot)

    OUTPUT.mkdir(exist_ok=True)
    html = render.page(args.date, prev_date, boards, conc, rows,
                       quote_source=quote_source, demo=args.demo,
                       warnings={"unmatched": unmatched, "missing": missing})
    (OUTPUT / "index.html").write_text(html, encoding="utf-8")
    new = {b["label"]: sum(e["is_new"] for e in b["entries"]) for b in boards.values()}
    print(f"[{args.date}] {len(rows)} 筆持股，集中持股 {len(conc)} 檔，新上榜 {new}")
    if unmatched:
        print(f"  名稱無法對應代號：{unmatched}")


if __name__ == "__main__":
    main()
