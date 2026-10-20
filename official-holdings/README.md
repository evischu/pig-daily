# 官員持股動態榜

每日產出一份 HTML：依「估計市值／持有張數／佔公司股權」三個指標列出前 40 名官員持股，
標記 5 人以上共同持有的個股與職掌相關持股，並與前一日比較，顯示新上榜、跌出與名次升降。

## 執行

```bash
python make_demo.py            # 產生示範資料（匿名官員、隨機報價）
python run.py --demo           # 用示範資料跑
python run.py                  # 真實版：data/holdings.csv + 證交所／櫃買即時報價
```

每天收盤後（14:30 以後）跑一次 `python run.py`。結果在 `output/index.html`，
名次快照存在 `data/snapshots/日期.json`，隔天用來比對。

## 換上真實資料

1. 到監察院財產申報資料網站申請查閱，下載廉政專刊 PDF。
2. OCR 後整理成 `data/holdings.csv`，欄位見 `sources/holdings.py` 開頭說明。
   `stock_code` 可留空，會用證交所公司簡稱自動比對；比對不到的名稱會列在頁尾。
3. `committee` 欄填委員會簡稱，需與 `config.COMMITTEE_INDUSTRIES` 的鍵一致。

## 參數（config.py）

- `TOP_N`：每榜名次數，預設 40
- `CONCENTRATION_MIN`：幾人以上共同持有算集中持股，預設 5
- `COMMITTEE_INDUSTRIES`：委員會對應產業，決定「職掌相關」標記

## 限制

- 申報沒有買進成本，「估計市值」是股數 × 收盤價。
- 股數一年申報一次，每日名次變化主要來自股價；新一期廉政專刊公開時張數榜才會變動。
- 公開呈現時建議只顯示官員本人，配偶、子女持股以合併數字呈現（本程式即如此）。
