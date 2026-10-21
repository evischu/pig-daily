# 設定教學：從示範版變成每天自動更新的真實版

整件事分三段：**A 開放網路** → **B 放入申報資料** → **C 每天自動跑並更新豬豬日報**。
做完 A、B 之後，C 才有意義。

---

## A. 開放雲端環境的網路（約 3 分鐘）

目前雲端沙盒擋掉了證交所與櫃買的網址，所以抓不到真實報價。

1. 在 claude.ai/code 打開這個 session，點視窗上方標題列的 **雲端環境選單**，選 **Edit**。
2. 找到 **Network access**，把等級改成 **Limited**（或 Custom）。
3. 在 **Allowed domains** 加入這四個網域，每行一個：
   ```
   openapi.twse.com.tw
   www.tpex.org.tw
   mis.twse.com.tw
   www.twse.com.tw
   ```
4. 勾選「Allow package managers」維持開啟。
5. 存檔。**要開新的 session，新設定才會生效**（舊 session 不會套用）。

官方說明：<https://code.claude.com/docs/en/cloud-environments#network-access>

驗證是否成功，在新 session 跑：

```bash
curl -s "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL" | head -c 300
```

看到 `[{"Date":"...","Code":"0050",...` 就成功。

> 這個 session 的 WebFetch 與網頁搜尋也連不到監察院（`cy.gov.tw`）和 ToAlpha，
> 所以我沒辦法替你抓到申報資料本身。

## B. 放入申報資料（`data/holdings.csv`）

### B-1 資料從哪來

| 來源 | 內容 | 取得方式 |
|---|---|---|
| 監察院「廉政專刊」 | 每期刊登的公職人員財產申報公報，含立委股票明細 | 監察院網站（cy.gov.tw）→ 廉政專刊，下載各期 PDF。每年定期申報（11/1–12/31）後的那幾期最重要 |
| 監察院財產申報查閱 | 同上，可依姓名查 | 需實名申請 |
| ToAlpha 政治人物持股 | 第三方整理的持股與估算市值，搜尋結果顯示 2026 年 10 月仍在更新 | 網頁瀏覽。**第三方整理，只能拿來交叉核對，不要當原始來源** |

### B-2 轉成 CSV

用 OCR 或手動整理成下面格式，存成 `official-holdings/data/holdings.csv`（UTF-8）：

```csv
issue,declare_date,official,title,committee,owner,stock_name,stock_code,shares
第 291 期,2026-03-31,王小明,立法委員,財政,本人,台積電,2330,45000
第 291 期,2026-03-31,王小明,立法委員,財政,配偶,國泰金,,120000
```

- `stock_code` 可留空，程式用證交所公司簡稱自動比對；比對不到的名稱會列在頁尾。
- `committee` 必須是這幾個之一：經濟、財政、交通、內政、社福衛環、外交國防、教育文化、司法法制。
- 同一人、同一檔股票的本人／配偶／子女會自動合併。
- 申報表上的單位若是「股」就直接填；若是「張」，請乘以 1000。

### B-3 實驗跑一次

```bash
cd official-holdings
python run.py            # 沒有 --demo
```

終端機最後會印「已更新豬豬日報區塊」，並產生 `data/official-holdings-section.html`。

## C. 每天自動更新到豬豬日報最下面

`build.py` 組版時，只要 `data/official-holdings-section.html` 存在，就會把榜單接在
「產業與股市影響」下方。沒有這個檔案就不顯示，所以資料沒備齊之前日報不受影響。

### C-1 在豬豬日報的排程步驟加一行

編輯 `RUNBOOK.md`，在第 6 步「組版」之前加：

```bash
(cd official-holdings && python3 run.py)   # 更新官員持股榜
```

> 排程是從 GitHub 的 `main` 分支抓程式碼。目前這些改動在
> `claude/official-holdings` 分支，**要先合併進 `main`，排程才拿得到**。
> 另外 `data/holdings.csv` 也要一併進 repo。

### C-2 雲端排程需要的網路

豬豬日報的雲端排程跑在另一個環境，它也要在 Allowed domains 加入 A 節的四個網域，
並且確認抓新聞用的網域沒被擋掉（既有的限制不變）。

### C-3 兩種更穩的做法（擇一）

- **只在你的電腦跑榜單**：每天收盤後 14:30 執行 `python run.py`，再 `git push`
  `data/official-holdings-section.html`，雲端日報只負責把它接上去。不必動雲端網路設定。
- **全部在雲端**：照 C-1、C-2。報價每天更新，申報資料一年只需要換幾次。

## 常見問題

- **榜單區塊沒出現**：確認 `data/official-holdings-section.html` 存在，且不是用 `--demo` 產的（示範模式刻意不寫入日報）。
- **名次沒有「新上榜」**：第一天沒有前一日快照，隔天才會有。快照在 `official-holdings/data/snapshots/`，雲端環境重開會消失，需要一併 commit。
- **某檔股票沒有股權比例**：該公司已發行股數沒抓到（上櫃公司偶爾欄位改名），不影響市值與張數榜。
