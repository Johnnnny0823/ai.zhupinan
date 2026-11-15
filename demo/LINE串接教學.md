# LINE指定帳號提醒（決賽版）

舊版向全部好友發送的流程已停用。本版必須先在雇主網頁產生一次性配對碼，在LINE對話輸入後，只綁定該雇主的合成案件。

1. 由團隊管理者準備LINE官方帳號與Messaging API channel。
2. 將Channel access token及Channel secret寫入**本機、不提交的**`demo/.env`，欄位名為`LINE_CHANNEL_ACCESS_TOKEN`及`LINE_CHANNEL_SECRET`。
3. 設定展示機HTTPS來源；`PUBLIC_ORIGIN`必須與瀏覽器網址相同。Webhook為`<PUBLIC_ORIGIN>/line/webhook`。
4. 重啟伺服器，登入雇主→LINE提醒→取得6位配對碼，10分鐘內在指定官方帳號對話輸入。
5. 網頁按「已在LINE輸入，重新查詢」，先看預覽，再按「發送此帳號測試訊息」。
6. 手機輸入「待辦」驗Reply；輸入「取消綁定」或網頁解除後，之後不再接收。
7. 第二支手機配另一雇主，驗證查詢、Push都沒有對方案件代號。
8. 記下實收時間、手機系統、網路環境與LINE request ID，使用合成資料錄影／截圖。

排程命令：`python -m demo.run notify`。Windows Task Scheduler的程式、參數及開始位置見[DEVELOPMENT.md](DEVELOPMENT.md)。
到期前7、3、1日及當日提醒；相同任務／類型／日期成功紀錄不重發，API錯誤使用原retry key重試。
LINE接受請求不等於手機已實收；沒有兩手機證據時不得宣稱這項驗收完成。

服務未設定／網路失敗時，畫面保留未寄送說明。可用[預存展示頁](/local-demo.html)展示訊息樣式，收件人為0，不假裝已寄送。
Webhook以原始body先驗HMAC-SHA256簽章，才處理JSON。不儲存好友列表、不提供群發API。
