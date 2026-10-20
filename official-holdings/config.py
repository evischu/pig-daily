"""官員持股動態榜：可調整的參數集中在這裡。"""
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
OUTPUT = ROOT / "output"

# 申報持股表（OCR 廉政專刊後整理成的 CSV，欄位見 README）
HOLDINGS_CSV = DATA / "holdings.csv"
DEMO_HOLDINGS_CSV = DATA / "demo_holdings.csv"
DEMO_MARKET_DIR = DATA / "demo_market"

TOP_N = 40                 # 每個排行榜取前幾名
CONCENTRATION_MIN = 5      # 幾位以上官員共同持有，標記為「集中持股」
LOT = 1000                 # 一張 = 1000 股

# 委員會職掌 → 相關產業，用來標記「職掌相關」持股
COMMITTEE_INDUSTRIES = {
    "經濟": {"半導體", "電子代工", "電腦週邊", "通信網路", "電子零組件", "重電", "鋼鐵", "塑化", "水泥", "光電"},
    "財政": {"金融"},
    "交通": {"航運", "電信", "汽車"},
    "內政": {"營建"},
    "社福衛環": {"生技醫療", "食品"},
    "外交國防": {"航太軍工"},
    "教育文化": set(),
    "司法法制": set(),
}

# 證交所產業別代碼 → 名稱（只列常用的，其餘顯示代碼）
TWSE_INDUSTRY = {
    "01": "水泥", "02": "食品", "03": "塑化", "10": "鋼鐵", "12": "汽車",
    "14": "營建", "15": "航運", "17": "金融", "18": "貿易百貨", "22": "生技醫療",
    "24": "半導體", "25": "電腦週邊", "26": "光電", "27": "通信網路",
    "28": "電子零組件", "31": "電子代工", "05": "重電",
}
