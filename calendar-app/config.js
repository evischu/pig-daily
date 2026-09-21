/* ============================================================
   Dayline 設定檔 —— 整個 App 只有這一行需要改。

   把引號中間換成你的 Google 用戶端 ID（結尾是
   .apps.googleusercontent.com），使用者就能一鍵登入。

   怎麼拿到這串 ID：照著 SETUP.md 做，大約五分鐘。

   留空也沒關係：App 照樣能用，只是登入按鈕會改成
   「匯入行事曆檔案」與「先看看」兩條免登入的路。
   ============================================================ */

window.DAYLINE_CONFIG = {
  googleClientId: "689127092407-stcdd9i9a582ao0fjsr06mvh1en7cpcb.apps.googleusercontent.com",

  // 天氣用 Open-Meteo，免費、不需要任何金鑰，留著就好。
  weather: true
};
