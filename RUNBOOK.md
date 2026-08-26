# 豬豬日報　每日產出流程

排程任務執行時完全照這份做。每次執行都是全新的 session，沒有前一次的記憶，
需要的資訊這份文件都有。

發布目標（固定，每次都更新這一個，不要另開新的）：
`https://claude.ai/code/artifact/8acb9762-5525-47ad-ba50-938b1b1d4d94`

這份流程在兩種環境都會執行到：
- **本機**（`~/Desktop/Claude專用/pig-daily`）—— 手動跑，或本機排程觸發，
  有持久化磁碟，`data/`、`images/` 都會留著給下一次用。
- **雲端**（CCR routine）—— 每次都是全新的空環境、沒有 git，程式碼靠
  `curl` 從公開 repo 的 raw 檔案現抓，跑完整個環境就銷毀，什麼都不會留下。
  第 0 步是雲端專屬、本機可略過；第 3 步的「續接更新紀錄」對雲端尤其重要
  （見該步說明）。

---

## 0. 環境準備（僅雲端；本機已裝好可略過）

程式碼與 `RUNBOOK.md` 本身應該已經由排程指令 curl 下來了。若還沒有：

```bash
mkdir -p pig-daily/tools && cd pig-daily
for f in build.py requirements.txt tools/fetch_images.py tools/image_prompts.py RUNBOOK.md; do
  curl -sL "https://raw.githubusercontent.com/evischu/pig-daily/main/$f" -o "$f"
done
pip install -q -r requirements.txt
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

**續接更新紀錄（雲端環境必做，本機通常已經有現成的可略過）**

雲端每次都是空環境，`data/<DATE>.json` 不會帶著先前的 `updates` 歷史。
但頁面本身有留一手：每次組版都會在 HTML 最後嵌一段
`<script type="application/json" id="pig-daily-meta">`，
裡面是 `{"date", "updates", "fingerprint"}`。續接方式：

1. 用 Artifact 工具 `action: "read"` 讀一次固定發布網址（上面第 6 行那個），
   拿到目前線上版本存檔的本機路徑。
2. 從那份存檔裡找到 `id="pig-daily-meta"` 那段 `<script>`，解析出的 JSON
   若 `date` 等於 `<DATE>`，就把它的 `updates` 和 `fingerprint`
   填進即將寫入的 `data/<DATE>.json`（在你動筆寫新聞內容之前先填好這兩欄，
   `build.py` 的 `stamp()` 會自動接著算）。
3. 若讀不到（今天第一次發布、或 `date` 對不上），略過即可，
   `build.py` 會當作今天第一次更新處理，不是錯誤。

## 4. 抓配圖

```bash
python3 tools/fetch_images.py data/<DATE>.json
```

（在專案根目錄下執行 —— 本機是 `~/Desktop/Claude專用/pig-daily`，
雲端則是 git clone 下來的工作目錄，指令本身不用改。）

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

## 8. 存回 repo（只有在這個環境本來就有 git 遠端時才做；否則略過）

雲端目前用的是 curl 抓檔案，沒有 git，這一步通常無法執行、也不需要——
第 3 步的「續接更新紀錄」已經取代了原本靠 git push 保留狀態的用途。
只有在偵測到 `.git/` 且已設定好可寫入的遠端時才做這步（`git remote -v`
確認），不確定或沒有權限就直接跳到第 9 步，不要為了這步卡住整個流程。

```bash
git add data/ images/manifest.json
git commit -m "豬豬日報 <DATE> <當次時段，如 07:30>"
git push
```

`images/cache/`、`images/*.webp`、`dist/` 已在 `.gitignore`，不需要也不應該
commit。

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
