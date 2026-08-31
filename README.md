# 豬豬日報

每日全球熱門新聞彙整，產出一份發布用的 HTML，更新到固定的 Artifact 網址：

<https://claude.ai/code/artifact/8acb9762-5525-47ad-ba50-938b1b1d4d94>

每天都更新這個網址，不要另開新的，書籤才不用換。

## 自動更新

每天 07:30 / 13:00 / 19:00 各跑一次，執行內容見 [RUNBOOK.md](RUNBOOK.md)。
跑在 Anthropic 雲端的排程 routine 上（claude.ai/code/routines 管理），
不依賴這台電腦是否開機、Claude Code 是否在跑：

- `pig-daily-morning-cloud` —— 每天 07:30
- `pig-daily-midday-evening-cloud` —— 每天 13:00、19:00

雲端環境是全新的空機器，沒有持久化磁碟：程式碼靠 `curl` 從這個公開 repo
的 raw 檔案現抓，「今天已經更新過幾次」這件事則靠讀回目前已發布的
Artifact（頁尾嵌了一段 `<script id="pig-daily-meta">`）接續，不透過 git
（見 RUNBOOK 的「續接更新紀錄」）。

本機原本的兩個排程（`pig-daily-morning`、`pig-daily-midday-evening`）
已停用，避免跟雲端排程同時發布互相打架；程式碼與 RUNBOOK 仍然共用同一份，
本機手動跑或雲端排程跑，走的是同一條路徑。

**已知限制，不是待修的 bug：**

- **雲端排程抓不到配圖。** 這個沙盒的出網政策會擋掉對新聞網域的連線（網域白名單，
  非 HTTP client 問題，已實測確認），所以雲端自動發布的版本固定是純文字版面。
  想要有圖，得由人在本機補跑一次：讀回線上目前的內容、本機抓圖（本機沒有這道
  網路限制）或放手動生成的 AI 圖進 `images/manual/`、重新發布；或是接受純文字版，
  不強求每次都有圖。
- **雲端排程可能因帳號用量週上限被跳過。** 遇到時那次執行會立刻失敗
  （`rate_limit: rejected (seven_day)`），不會重試，等下一個排定時段才會恢復。
  三個時段中有一次被跳過屬於正常情況，不用特別處理。

頁面右上角會顯示更新時間與距今多久；超過 20 小時沒更新會轉成紅色提示，
一眼就知道排程是不是沒跑到。

## 手動跑一次

```bash
# 1. 產生當天資料（由 Claude 蒐集新聞後寫入）
#    data/YYYY-MM-DD.json

# 2. 抓各則新聞原始報導的配圖
python3 tools/fetch_images.py data/2026-08-26.json

# 3. 列出抓不到圖的，產生生圖用的 prompt
python3 tools/image_prompts.py 2026-08-26 --md > dist/2026-08-26-prompts.md

# 4. 到 claude.ai 依 prompt 生圖，存成 images/manual/<檔名>.jpg

# 5. 組版
python3 build.py 2026-08-26

# 6. 由 Claude 發布 dist/2026-08-26.html 到既有的 Artifact 網址
```

第 4 步可以跳過 —— 沒有 AI 圖的新聞會自動改用純文字卡，版面不會開天窗。
放進 `images/manual/` 的圖如果要讓雲端排程也看得到，記得 `git push`
（本機自己跑組版不需要）。

圖片處理靠 [Pillow](https://pypi.org/project/pillow/)，本機沒裝也沒關係，
會自動退回用 macOS 內建的 `sips`／`cwebp`；兩套後端輸出結果一致，
只是雲端環境沒有 `sips`，一定要 `pip install -r requirements.txt`。

## 資料格式

`data/YYYY-MM-DD.json`：

```jsonc
{
  "date": "2026-08-26",
  "top3":   [ /* 3 則，今日焦點 */ ],
  "global": [ /* 50 則，全球熱度排行 */ ],
  "twcn":   [ /* 30 則，台灣與中國大陸 */ ],
  "market": [ /* 股市影響分析 */ ]
}
```

新聞項目：

```jsonc
{
  "rank": 1,
  "category": "world",   // world war politics finance tech society disaster entertainment sports
  "title": "標題",
  "summary": "兩到三句摘要",
  "url": "https://原始報導網址",
  "source": "媒體名稱"
}
```

股市項目：

```jsonc
{
  "sentiment": "bull",           // bull 利多 / bear 利空 / neutral 中性
  "market": "台股",              // 台股 / 美股
  "industry": "半導體/AI",
  "title": "標題",
  "summary": "摘要",
  "reason": "為什麼判斷成這個方向",
  "tickers": ["台積電(2330)", "台灣加權指數"],
  "url": "https://原始報導網址"
}
```

## 配圖規則

優先序：`images/manual/`（手動放的 AI 圖）→ 原始報導的照片 → 純文字卡。

抓圖的命中率大約七成五。抓不到的主要是三類：Bloomberg、華盛頓郵報這種擋
自動抓取的站；中國媒體多半沒有 `og:image`；還有本來就沒配圖的稿件。

`tools/image_prompts.py` 會把每則標成 `photo` 或 `editorial` 兩種風格。這個分法
不是美感取捨：牽涉真實政治人物或具體軍事行動的新聞一律走插畫，因為把沒發生過的
事件畫成擬真新聞照，那張圖一旦單獨流出去就是現成的假新聞素材。所有配圖都掛
「豬豬日報」角標，不使用任何電視台識別或直播時間戳。

## 檔案

```
build.py                    組版；LITE=1 可產生無圖版本，方便檢查排版
tools/fetch_images.py       抓 og:image，裁切壓縮成四種尺寸的 WebP
tools/image_prompts.py      列出缺圖的新聞並產生 prompt
tools/extract_from_artifact.py   一次性：把舊版手寫 HTML 轉成 data JSON
data/                       每日內容
images/                     配圖成品與 manifest；cache/ 是原圖，manual/ 放手動圖
dist/                       產出的 HTML 與 prompt 清單
```

## 本地預覽

```bash
python3 -m http.server 8731 --directory dist
```
