# 上架 App Store —— 這裡已經做好的，跟只有你能做的

## 這個資料夾是什麼

`calendar-app/` 是原本的網頁版（已經上線：<https://evischu.github.io/pig-daily/>），
`app-shell/` 是把同一份網頁包裝成**真正的 iOS App** 的專案——用業界常見的
Capacitor 做法，Instagram、Uber 早期都是這樣起家的。網頁那邊每次更新，
這邊的 App 只要重新打包一次就會同步。

## ✅ 我已經做好的部分

- Capacitor 專案骨架、Xcode 專案檔（`app-shell/ios/`）
- App 圖示（1024×1024，符合 App Store 規格，無透明背景）
- 權限說明文字（例如「為什麼要問你的位置」——iOS 規定要寫清楚，不寫審核會被退）
- 手機直式鎖定（這個 App 的版面是直式手機設計的，橫向會跑版，已經在系統層級擋掉）
- 一支 GitHub 自動化流程（`.github/workflows/ios-build.yml`），每次改動都會在
  雲端的 Mac 上**真的編譯一次**，確保專案沒有壞掉——完全免費，你不用自己買 Mac。

## ❌ 只有你能做的部分（沒有人能代替你）

這不是我偷懶，是 Apple 的規定：**身分認證跟付費，任何 AI 或代理人都無法代替本人完成。**

### 1. 申請 Apple Developer Program —— US$99／年

網址：<https://developer.apple.com/programs/>

需要：你的 Apple ID、信用卡、身分驗證（大約 1～2 天審核）。

### 2. 在 App Store Connect 建立這個 App 的資料

網址：<https://appstoreconnect.apple.com/>

- App 名稱：`Dayline`（或你想要的名字）
- Bundle ID：`com.evischu.dayline`（已經在專案裡設好，這裡要填一樣的）
- 上架分類：生產力工具
- **隱私權政策網址**：這個一定要有，因為 App 會讀 Google 帳號資料。
  可以直接把 `calendar-app/SETUP.md` 裡那段「不會做的事」擴充成一頁，
  用 GitHub Pages 掛上去就有網址了——需要的話跟我說，我可以幫你寫。
- 截圖：至少要 6.7 吋（iPhone 15 Pro Max 那個尺寸）跟 6.5 吋各一組，
  審核時要用。

### 3. 產生簽署憑證，把它接進自動化流程

這一步需要 Apple Developer 帳號才能做，等你申請下來我可以繼續幫你把
`ios-build.yml` 升級成會自動簽署、自動上傳到 TestFlight 的版本
（做法是把憑證存成 GitHub 的加密 Secrets，讓雲端 Mac 幫你簽），
到時候只要在手機上打開 TestFlight App 就能測試，不用再透過 Safari。

### 4. Google OAuth 正式審核（如果要開放給 100 人以上）

跟網頁版是同一件事，做法寫在 `calendar-app/SETUP.md` 最下面那段。
上架 App Store 前，這個最好先送出去審（Google 那邊約 2～6 週），
避免使用者裝了 App 卻因為「測試名單沒登記」登入失敗。

### 5. 送審

填完 App Store Connect 的所有欄位、上傳建置版本、按「送出審核」，
Apple 通常 1～3 天內會有結果。

---

## 費用總覽

| 項目 | 費用 | 誰要付 |
|---|---|---|
| Apple Developer Program | US$99／年 | 你 |
| GitHub Actions（雲端 Mac 編譯） | 免費（公開 repo 無限額度；私有 repo 每月有免費額度） | — |
| Google OAuth 驗證 | 免費 | — |

## 我能繼續幫你做的事

- 把 `ios-build.yml` 升級成自動簽署 + 自動上傳 TestFlight（需要你先申請好帳號、把憑證丟給我存進 Secrets）
- 寫隱私權政策頁面
- 準備 App Store 需要的截圖文案
- 之後想加 iOS 原生功能（鎖屏通知、Siri 捷徑、主畫面 Widget）也是在這個
  `app-shell` 專案裡做，網頁版做不到的東西，包成 App 之後才有辦法
