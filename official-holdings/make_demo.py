"""產生示範資料：113 位匿名委員的持股、兩個交易日的報價。

官員一律匿名（委員 A001…），持股與報價皆為隨機產生，不代表任何真實人物或行情。
"""
import csv
import json
import random

from config import DEMO_HOLDINGS_CSV, DEMO_MARKET_DIR

random.seed(20261020)

# 代號, 名稱, 市場, 產業, 參考價, 已發行股數(億股), 熱門度權重
STOCKS = [
    ("2330", "台積電", "上市", "半導體", 1450, 259.3, 10), ("2317", "鴻海", "上市", "電子代工", 230, 138.6, 6),
    ("2454", "聯發科", "上市", "半導體", 1400, 16.0, 4), ("2308", "台達電", "上市", "電子零組件", 900, 26.0, 3),
    ("2382", "廣達", "上市", "電腦週邊", 290, 38.6, 3), ("3711", "日月光投控", "上市", "半導體", 180, 44.0, 2),
    ("2412", "中華電", "上市", "電信", 130, 77.6, 6), ("2881", "富邦金", "上市", "金融", 90, 136.0, 7),
    ("2882", "國泰金", "上市", "金融", 70, 146.7, 7), ("2891", "中信金", "上市", "金融", 45, 195.0, 6),
    ("2886", "兆豐金", "上市", "金融", 40, 144.0, 8), ("2884", "玉山金", "上市", "金融", 30, 160.0, 6),
    ("2892", "第一金", "上市", "金融", 30, 139.0, 6), ("5880", "合庫金", "上市", "金融", 24, 149.0, 5),
    ("2603", "長榮", "上市", "航運", 200, 21.6, 4), ("2609", "陽明", "上市", "航運", 65, 34.9, 3),
    ("2615", "萬海", "上市", "航運", 90, 28.0, 2), ("2002", "中鋼", "上市", "鋼鐵", 22, 157.0, 6),
    ("1301", "台塑", "上市", "塑化", 45, 63.7, 4), ("1303", "南亞", "上市", "塑化", 40, 79.3, 3),
    ("1216", "統一", "上市", "食品", 80, 56.8, 3), ("2303", "聯電", "上市", "半導體", 45, 125.0, 4),
    ("2357", "華碩", "上市", "電腦週邊", 650, 7.4, 1), ("2379", "瑞昱", "上市", "半導體", 550, 5.1, 1),
    ("3008", "大立光", "上市", "光電", 2400, 1.3, 1), ("2345", "智邦", "上市", "通信網路", 1200, 5.6, 1),
    ("3231", "緯創", "上市", "電腦週邊", 120, 29.0, 2), ("6669", "緯穎", "上市", "電腦週邊", 3000, 1.8, 1),
    ("1519", "華城", "上市", "重電", 750, 2.1, 2), ("1513", "中興電", "上市", "重電", 160, 4.9, 2),
    ("1503", "士電", "上市", "重電", 200, 5.2, 2), ("2207", "和泰車", "上市", "汽車", 450, 5.5, 1),
    ("1101", "台泥", "上市", "水泥", 28, 75.0, 3), ("6505", "台塑化", "上市", "塑化", 30, 95.0, 2),
    ("2801", "彰銀", "上市", "金融", 20, 110.0, 4), ("4938", "和碩", "上市", "電子代工", 70, 26.5, 2),
    ("3443", "創意", "上市", "半導體", 1700, 1.34, 1), ("8299", "群聯", "上櫃", "半導體", 900, 2.0, 1),
    ("6488", "環球晶", "上櫃", "半導體", 400, 4.8, 1), ("3529", "力旺", "上櫃", "半導體", 2000, 0.75, 1),
    ("1795", "美時", "上市", "生技醫療", 300, 2.6, 1), ("2634", "漢翔", "上市", "航太軍工", 50, 9.4, 2),
    ("2501", "國建", "上市", "營建", 25, 12.0, 1), ("5522", "遠雄", "上市", "營建", 50, 5.6, 1),
]
COMMITTEES = ["經濟", "財政", "交通", "內政", "社福衛環", "外交國防", "教育文化", "司法法制"]
OWNERS = ["本人"] * 6 + ["配偶"] * 3 + ["子女"]
DAYS = ["2026-10-19", "2026-10-20"]
NEW_ISSUE_DAY = DAYS[1]   # 第二天模擬新一期廉政專刊公開


def holdings():
    rows, weights = [], [s[6] for s in STOCKS]
    for i in range(1, 114):
        official, committee = f"委員 A{i:03d}", random.choice(COMMITTEES)
        late = i in (17, 58, 91)   # 這三位的申報在第二天才公開
        issue, date = ("第 291 期", NEW_ISSUE_DAY) if late else ("第 290 期", "2026-03-31")
        n = 0 if random.random() < 0.25 else random.randint(1, 9)
        picked = {random.choices(STOCKS, weights)[0] for _ in range(n)}
        big = random.choice(STOCKS[:20]) if late else None   # 讓新公開的申報有一筆直接上榜
        if big:
            picked.add(big)
        for s in picked:
            base = random.lognormvariate(10.3, 1.4)          # 中位數約 3 萬股
            if random.random() < 0.04 or s == big:
                base *= random.uniform(20, 120)             # 少數家族持股
            shares = int(round(base / 1000) * 1000) or 1000
            rows.append([issue, date, official, "立法委員", committee,
                         random.choice(OWNERS), s[1], "", shares])
    with open(DEMO_HOLDINGS_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue", "declare_date", "official", "title", "committee",
                    "owner", "stock_name", "stock_code", "shares"])
        w.writerows(rows)
    return len(rows)


def market():
    DEMO_MARKET_DIR.mkdir(parents=True, exist_ok=True)
    prev = {s[0]: s[4] for s in STOCKS}
    for day in DAYS:
        out = {}
        for code, name, mkt, ind, _, issued, _ in STOCKS:
            close = round(prev[code] * (1 + random.gauss(0, 0.035)), 1)
            out[code] = {"name": name, "market": mkt, "industry": ind, "close": close,
                         "prev_close": prev[code], "issued": issued * 1e8}
            prev[code] = close
        json.dump(out, open(DEMO_MARKET_DIR / f"{day}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)


if __name__ == "__main__":
    print(f"示範持股 {holdings()} 筆")
    market()
