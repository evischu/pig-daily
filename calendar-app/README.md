# Dayline — Google 行事曆的 iPhone 前台（原型）

單一檔案的 iPhone 網頁應用原型。資料留在 Google，這個 App 只負責**看得懂、加得快、提醒得準**。

- 原型網址（示範模式）：<https://claude.ai/artifact/4YuykYWcGs233PyqUyJt7s>
- 原始碼：`calendar-app/index.html`（無外部相依，只用 Google Fonts）

## 雙模式

同一份 `index.html` 會依執行環境自動切換：

| 模式 | 觸發條件 | 行為 |
|---|---|---|
| **DEMO** | 沒有 client id，或 Google 的登入腳本載不進來 | 依你裝置的**當天日期**即時生成一週示範行程，所有互動（新增、回覆邀請、隱私模式、搜尋）都真的會動 |
| **LIVE** | 部署到已註冊的網域，並帶入 `?client_id=…` | 走真正的 Google OAuth，讀取你的 `calendarList` 與前後各 30 天的事件 |

> Claude Artifact 的沙盒 CSP 只允許 cdnjs / jsdelivr 等少數來源的腳本，會擋掉
> `accounts.google.com` 與 `googleapis.com`。所以**在 Artifact 上永遠是 DEMO 模式**，
> 這是平台限制，不是程式問題。要真的連到你的行事曆，請用下面的自行部署步驟。

## 要真的連上你的 Google 行事曆

### 1. 建立 OAuth 用戶端

1. 進 [Google Cloud Console](https://console.cloud.google.com/) 建一個專案。
2. **APIs & Services → Library**：啟用 `Google Calendar API` 與 `Google Tasks API`。
3. **APIs & Services → OAuth consent screen**：選 External，填 App 名稱、支援信箱、隱私權政策網址；
   在 **Test users** 加入你自己的 Gmail（測試階段只有測試使用者能登入，上限 100 人）。
4. **Credentials → Create credentials → OAuth client ID → Web application**：
   - **Authorized JavaScript origins** 填入你要部署的來源，例如
     `https://<你的帳號>.github.io`
   - 這個流程用的是 GIS token client（隱含授權），**不需要** redirect URI。
5. 複製產生的 Client ID（長得像 `1234567890-abc.apps.googleusercontent.com`）。

### 2. 部署

任何靜態主機都可以，以 GitHub Pages 為例：

```bash
# 把 calendar-app/index.html 放到一個開啟 Pages 的 repo 根目錄
# Settings → Pages → Source: Deploy from a branch
```

### 3. 在 iPhone 上開啟

用 Safari 打開，網址後面帶上 client id：

```
https://<你的帳號>.github.io/?client_id=1234567890-abc.apps.googleusercontent.com
```

按**分享 → 加入主畫面**，就會變成一個全螢幕、有自己圖示的 App。
點「使用 Google 帳號連線」會跳出真正的 Google 授權畫面。

## 要求的權限範圍

| Scope | 對應功能 |
|---|---|
| `calendar.events` | 一句話新增、改期、回覆邀請 |
| `calendar.readonly` | 日曆清單、顏色、共享狀態、日／週視圖 |
| `tasks.readonly` | 把 Google Tasks 畫在同一條時間軸上 |

三個都是 Google 分類的 **sensitive scope**，不是 restricted scope。差別很重要：

- **sensitive** → 公開上架前需要通過 OAuth 驗證（隱私權政策、網域驗證、用途說明、示範影片），約 2–6 週，**免費**。
- **restricted** → 還要加上每年一次的第三方安全稽核（CASA），約 US$500–4,500。

這個 App 刻意採**零伺服器儲存**：access token 只存在記憶體，事件資料只在瀏覽器與
Google 之間往返，不經過任何中介伺服器——這正是留在 sensitive 這一側、避開 CASA 的關鍵。
如果之後要加推播（`events.watch` → Pub/Sub → APNs），伺服器只轉發「某個日曆變了」的通知，
不落地事件內容，才能維持同樣的分類。

## 已實作

- Google 授權流程（真實 + 沙盒下的授權預覽畫面）
- 今日簡報卡：行程數、時間衝突、待回覆，以及「該出門了」推算
- 情境切換（全部／工作／家庭／個人）＋ 共享日曆隱私模式（只顯示忙碌）
- 日視圖時間軸：重疊事件分欄、即時紅線、整天事件、Tasks 以虛線塊呈現
- 週概覽 ＋ 逐日清單，含可用空檔估算
- 容錯搜尋（Levenshtein 滑動視窗，打錯一兩個字也找得到）
- 一句話新增：中文日期／時間／時長／地點／對象／日曆歸類解析
- 提醒規則設定（該出門了、線上會議、整天事件、家庭彙整、每日簡報）
- 深／淺色主題，跟隨系統或手動指定

## 尚未實作（正式版需要）

- `syncToken` 增量同步與離線寫入佇列
- `events.watch` → Pub/Sub → APNs 推播
- 共享權限管理（`acl.*`）
- 事件範本、批次改期
- 找時間／約時間（`freebusy.query` 交集）
