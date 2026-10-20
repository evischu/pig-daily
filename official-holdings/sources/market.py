"""收盤價與已發行股數：證交所／櫃買中心 OpenAPI，抓不到時退回示範資料。"""
import json
import ssl
import urllib.request

from config import DEMO_MARKET_DIR, TWSE_INDUSTRY

TWSE_QUOTES = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
TWSE_BASIC = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
TPEX_QUOTES = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"
TPEX_BASIC = "https://www.tpex.org.tw/openapi/v1/mopsfe_company_basic"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
        return json.loads(r.read().decode("utf-8-sig"))


def _num(s):
    try:
        return float(str(s).replace(",", "").replace("+", "").strip())
    except ValueError:
        return None


def fetch_live():
    """回傳 {code: {name, market, close, prev_close, issued, industry}}。"""
    out = {}
    for r in _get(TWSE_QUOTES):
        close, chg = _num(r.get("ClosingPrice")), _num(r.get("Change"))
        if close:
            out[r["Code"]] = {"name": r["Name"], "market": "上市", "close": close,
                              "prev_close": close - (chg or 0)}
    for r in _get(TWSE_BASIC):
        c = out.get(r.get("公司代號"))
        if c:
            c["issued"] = _num(r.get("已發行普通股數或TDR原股發行股數"))
            c["industry"] = TWSE_INDUSTRY.get(r.get("產業別"), r.get("產業別"))
    for r in _get(TPEX_QUOTES):
        close, chg = _num(r.get("Close")), _num(r.get("Change"))
        if close:
            out[r["SecuritiesCompanyCode"]] = {"name": r["CompanyName"], "market": "上櫃",
                                               "close": close, "prev_close": close - (chg or 0)}
    try:  # 櫃買基本資料欄位名稱偶有變動，失敗只影響上櫃股的股權比例
        for r in _get(TPEX_BASIC):
            c = out.get(r.get("SecuritiesCompanyCode") or r.get("公司代號"))
            if c:
                c["issued"] = _num(r.get("IssueShares") or r.get("已發行普通股數或TDR原股發行股數"))
    except Exception as e:
        print(f"[market] 櫃買基本資料抓取失敗，上櫃股權比例將留空：{e}")
    return out


def load_demo(date):
    return json.load(open(DEMO_MARKET_DIR / f"{date}.json", encoding="utf-8"))


def get(date, demo=False):
    """回傳 (market, source_label)。"""
    if not demo:
        try:
            return fetch_live(), "證交所／櫃買中心 OpenAPI"
        except Exception as e:
            print(f"[market] 即時報價抓取失敗，改用示範資料：{e}")
    return load_demo(date), "示範報價（非真實行情）"
