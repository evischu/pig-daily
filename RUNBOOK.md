# 豬豬日報　每日產出流程

排程任務執行時完全照這份做。每次執行都是全新的 session，沒有前一次的記憶，
需要的資訊這份文件都有。

發布目標（固定，每次都更新這一個，不要另開新的）：
`https://claude.ai/code/artifact/8acb9762-5525-47ad-ba50-938b1b1d4d94`

這份流程在兩種環境都會執行到：
- **本機**（`~/Desktop/Claude專用/pig-daily`）—— 手動跑，或本機排程觸發。
- **雲端**（CCR routine）—— 每次都是全新 `git clone`，跑完即銷毀，
  所以第 0 步與第 8 步是雲端專屬、本機可略過。

---

## 0. 環境準備（僅雲端；本機已裝好可略過）

```bash
pip install -r requirements.txt
```

確認 `python3 -c "import PIL; print(PIL.__version__)"`能印出版本號再繼續，
圖片處理全靠 Pillow，這一步沒做完後面會整批失敗。

## 1. 確認日期

用本機時間取今天的日期（格式 `YYYY-MM-DD`）。以下用 `<DATE>` 代表。

一天會跑三次（07:30 / 13:00 / 19:00）。第二、三次跑的時候 `data/<DATE>.json`
已經存在 —— 直接覆蓋內容重寫即可，不要另存新檔。`build.py` 會自己比對內容雜湊，
內容真的變了才會多記一次更新時間，所以不用擔心重跑會讓次數灌水。

## 2. 蒐集新聞

用網路搜尋整理出四個區塊，全部用**繁體中文**撰寫（標題與摘要都要重寫成中文，
不要直接貼原文）：

| 區塊 | 數量 | 內容 |
|---|---|---|
| `top3` | 3 則 | 當下影響力最大的三則，可與其他區塊重複 |
| `global` | 50 則 | 全球熱度排行，依報導量、社群討論度、搜尋趨勢排序 |
| `twcn` | 30 則 | 台灣與中國大陸在地熱度排行，與全球榜分開計算 |
| `market` | 8–12 則 | 今日新聞中可能牽動台股或美股的消息 |

要求：

- **每則都要有可點的原始報導網址**，而且是真實存在、當天或近幾天的報導。
  不確定的連結不要放，寧可少一則。
- 摘要兩到三句，寫出「發生什麼」與「為什麼重要」，不要只是標題的改寫。
- 分類從這九個選：`world` `war` `politics` `finance` `tech` `society`
  `disaster` `entertainment` `sports`。
- 來源用媒體的通用名稱（`CNN`、`Al Jazeera`、`中央社`），不要放網域。
- `rank` 從 1 開始連號，`global` 到 50、`twcn` 到 30。

股市區塊每則還要有：`sentiment`（`bull` 利多／`bear` 利空／`neutral` 中性）、
`market`（`台股` 或 `美股`）、`industry`、`reason`（為什麼判斷成這個方向）、
`tickers`（相關個股或指數）。判斷要保守：資訊不足就給 `neutral`，
不要為了畫面好看硬分多空。

## 3. 寫入資料檔

存成 `data/<DATE>.json`。完整欄位定義見 `README.md`，格式：

```jsonc
{
  "date": "<DATE>",
  "top3":   [ {"rank":1, "category":"war", "title":"…", "summary":"…",
               "url":"https://…", "source":"…"} ],
  "global": [ … 50 則 … ],
  "twcn":   [ … 30 則 … ],
  "market": [ {"sentiment":"bull", "market":"台股", "industry":"半導體/AI",
               "title":"…", "summary":"…", "reason":"…",
               "tickers":["台積電(2330)"], "url":"https://…"} ]
}
```

檔案裡如果已經有 `updates` 和 `fingerprint` 兩個欄位，**保留不要刪**，
那是更新時間的紀錄。

## 4. 抓配圖

```bash
cd /Users/evis/Desktop/Claude專用/pig-daily
python3 tools/fetch_images.py data/<DATE>.json
```

命中率大約七成五。抓不到很正常（付費牆、擋機器人、中國媒體多半沒有
`og:image`），版面對無圖有對應處理，不會開天窗。已經抓過的圖會沿用快取。

## 5. 產生缺圖清單

```bash
python3 tools/image_prompts.py <DATE> --md > dist/<DATE>-prompts.md
```

**這一步只是產出清單，不要自己生圖** —— Claude Code 沒有圖片生成工具。
清單留給使用者需要時到 claude.ai 生，生好的圖丟進 `images/manual/`，
下次組版會自動接上。

## 6. 組版

```bash
python3 build.py <DATE>
```

產出 `dist/<DATE>.html`。留意輸出的統計行（真實照片幾則、無圖幾則）。

## 7. 發布

用 Artifact 工具發布 `dist/<DATE>.html`，**必須帶上 `url` 參數**指向上面那個
固定網址，否則會變成一個新的 artifact，使用者的書籤就失效了。

- `favicon`：🐷（固定不變）
- `description`：一句話描述當天內容
- `label`：`<DATE>` 加上當次時段，例如 `2026-08-27-morning`

## 8. 存回 repo（僅雲端；本機略過）

雲端這份跑完就銷毀，`data/<DATE>.json`（含 `updates`／`fingerprint`）與
`images/manifest.json` 不 push 回去就會憑空消失，下次又要從零開始重蒐集。

```bash
git add data/ images/manifest.json
git commit -m "豬豬日報 <DATE> <當次時段，如 07:30>"
git push
```

`images/cache/`、`images/*.webp`、`dist/` 已在 `.gitignore`，不需要也不應該
commit —— 那些每次都會重新產生。`images/manual/` 裡使用者放的 AI 圖如果本地
已經 push 過，clone 下來就會自動接上；雲端本身不生圖。

## 9. 回報

簡短說明：更新時間、各區塊則數、配圖命中幾則、有沒有失敗的步驟。
不要重述新聞內容。

---

## 界線

配圖若之後由使用者補上 AI 生成圖，一律掛「豬豬日報」角標並標示「示意圖」。
**不使用任何虛構或真實的電視台識別、`LIVE` 字樣、直播時間戳** —— 那會讓虛構
畫面看起來像真實新聞直播截圖。牽涉真實政治人物或具體軍事行動的新聞走編輯插畫，
不做擬真攝影。`tools/image_prompts.py` 已經內建這個分流。

## 出錯時

- 抓圖整批失敗 → 照常組版發布，無圖版面本來就成立，在回報裡註明。
- 新聞蒐集不足量 → 有多少放多少，不要編造連結或內容湊數，在回報裡說明短缺。
- 發布失敗 → 保留 `dist/<DATE>.html`，在回報裡說明，不要重試超過兩次。
