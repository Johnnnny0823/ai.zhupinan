# 竹聘安 AI － LINE 推播串接教學

完成後的效果：
- 評審用手機掃 QR code 加「竹聘安 AI」好友 → 自動收到歡迎訊息
- 傳「待辦」→ 官方帳號回覆近期待辦（附法條依據）
- 在 DEMO 網頁「LINE 提醒」按「產生提醒並推播」→ 所有好友手機收到提醒（可選中文／印尼文／越南文）

預計時間：第一次約 30～40 分鐘。需要：一個 LINE 帳號、這台電腦。

> ⚠️ 安全提醒：Channel secret 和 Channel access token 等同密碼。**不要貼到聊天、簡報、截圖或 GitHub**，只寫進 `line.env` 檔案。萬一外流，到 LINE Developers 重新發行（Reissue）即可讓舊的失效。

---

## 第 1 步：建立 LINE 官方帳號（約 10 分鐘）

1. 用瀏覽器開 <https://entry.line.biz/start/tw/>，選「建立 LINE 官方帳號」。
2. 用你的個人 LINE 帳號登入（會建立 LINE Business ID）。
3. 填寫資料：
   - 帳號名稱：`竹聘安 AI`
   - 業種：可選「教育・學校」或「其他」
   - 其他欄位照實填寫即可
4. 建立完成後，進入 **LINE Official Account Manager**（<https://manager.line.biz/>）。

## 第 2 步：啟用 Messaging API（約 5 分鐘）

1. 在 Official Account Manager 選剛建立的帳號 → 右上角「**設定**」。
2. 左側選「**Messaging API**」→ 按「**啟用 Messaging API**」。
3. 建立「提供者（Provider）」，名稱可填 `竹聘安團隊` → 同意條款 → 確定。

## 第 3 步：關閉自動回應（約 2 分鐘）

在 Official Account Manager →「設定」→「**回應設定**」：

| 項目 | 設定 |
|---|---|
| 聊天 | 關閉 |
| 加入好友的歡迎訊息 | 關閉（我們的程式會自己發） |
| 自動回應訊息 | **關閉**（否則會蓋掉我們的回覆） |
| Webhook | 先跳過——要等第 8 步填好 Webhook 網址後才能開啟（此時會顯示「如需操作Webhook，請在Messaging API的設定畫面中設定Webhook網址」，屬正常） |

## 第 4 步：取得兩把金鑰（約 5 分鐘）

1. 開 <https://developers.line.biz/console/>，用同一個 LINE 帳號登入。
2. 點進剛剛的 Provider → 點「竹聘安 AI」這個 channel。
3. 「**Basic settings**」分頁 → 往下找 **Channel secret** → 複製。
4. 「**Messaging API**」分頁 → 最下面 **Channel access token (long-lived)** → 按「**Issue**」→ 複製。

## 第 5 步：寫進設定檔（約 2 分鐘）

1. 打開資料夾 `D:\竹聘安\demo\server\`
2. 複製 `line.env.example`，改名為 **`line.env`**（注意不要留下 `.example`；若看不到副檔名，在檔案總管「檢視」勾選「副檔名」）
3. 用記事本打開 `line.env`，把兩行等號右邊換成剛剛複製的值，存檔：
   ```
   LINE_CHANNEL_SECRET=（貼上 Channel secret）
   LINE_CHANNEL_ACCESS_TOKEN=（貼上 Channel access token）
   ```
   不用加引號、等號前後不要有空格。存檔後伺服器會自動讀到，不用重開。

## 第 6 步：安裝 cloudflared（一次就好，約 3 分鐘）

LINE 只能連到「公開的 https 網址」，但 DEMO 跑在你的電腦上（localhost）。cloudflared 是 Cloudflare 的免費工具，會給你一個暫時的公開網址，免註冊。

在 PowerShell 執行：

```bash
winget install --id Cloudflare.cloudflared
```

裝好後**關掉 PowerShell 再重開一個**，讓系統找得到它。

## 第 7 步：啟動並取得公開網址

1. 雙擊 `D:\竹聘安\啟動DEMO.bat`（DEMO 伺服器，視窗不要關）
2. 另外開一個 PowerShell 視窗，輸入下面這行並按 Enter（這會把你電腦上的 DEMO 暫時開放到網路上，關掉視窗就會停止）：
   ```
   cloudflared tunnel --url http://127.0.0.1:8765
   ```
3. 畫面會出現類似這行：
   ```
   https://random-words-1234.trycloudflare.com
   ```
   把它複製下來。

## 第 8 步：設定 Webhook URL

1. 回到 LINE Developers →「**Messaging API**」分頁 →「**Webhook settings**」
2. Webhook URL 填：`https://（剛剛的網址）/line/webhook`
   例：`https://random-words-1234.trycloudflare.com/line/webhook`
   （也可在 Official Account Manager →「設定」→「Messaging API」→「Webhook 網址」填寫，兩處是同一個設定）
3. 按「**Update**」→ 再按「**Verify**」→ 應該顯示 **Success**
4. 確認「**Use webhook**」是開啟的；並回到 Official Account Manager「回應設定」把 **Webhook 開啟**

## 第 9 步：測試

1. 「Messaging API」分頁上方有 **QR code**，用手機 LINE 掃描加好友 → 應收到「歡迎使用竹聘安 AI！」
2. 在 LINE 對話傳「**待辦**」→ 應收到近期待辦提醒
3. 打開 DEMO 網頁 <http://localhost:8765> →「上傳公文」先產生幾項待辦 →「LINE 提醒」→ 按「**產生提醒並推播到 LINE**」→ 手機應收到提醒
4. 試著把語言切成 Bahasa Indonesia 再推播一次

---

## 常見問題

| 狀況 | 原因與解法 |
|---|---|
| 開網址出現 502 Bad gateway | DEMO 伺服器沒在跑：先雙擊「啟動DEMO.bat」，再開 cloudflared；指令要用 `127.0.0.1` 不要用 `localhost` |
| Verify 顯示失敗 | ① DEMO 視窗和 cloudflared 視窗都還開著嗎？② 網址後面有加 `/line/webhook` 嗎？③ `line.env` 的 Channel secret 有貼對嗎？ |
| 加好友沒收到歡迎訊息 | 第 3 步「Webhook」沒開啟，或「自動回應訊息」沒關 |
| 網頁顯示「還沒有人加入官方帳號好友」 | 加好友時 webhook 還沒設好。到 LINE 對話隨便傳一句話，系統就會記下你，再推播一次 |
| 推播顯示失敗 401 | Channel access token 貼錯或已重新發行過，重新複製貼上 |
| 重開電腦後 LINE 沒反應 | trycloudflare 網址每次都會變，要重新做第 7、8 步 |
| 推播顯示失敗 429 | 免費方案的每月訊息則數用完了（可在 Official Account Manager 查看用量）；DEMO 網頁的預覽畫面仍可展示 |

## 決賽當天建議

- **提早 30 分鐘**到場測網路：啟動 DEMO、執行 cloudflared → 更新 Webhook URL → Verify → 手機傳「待辦」確認
- 會場網路若擋 cloudflared，DEMO 網頁的「LINE 提醒」會自動退回**預覽模式**（手機畫面模擬），流程照樣能講
- 可以準備一張 QR code 投影片，請評審現場加好友、傳「待辦」——這是最有記憶點的互動

## 技術說明（給評審問到時用）

- 我們用 LINE Messaging API 的 **Push**（主動推播）與 **Reply**（回覆）兩種訊息
- Webhook 以 **HMAC-SHA256 驗證 LINE 簽章**，偽造的請求會被拒絕（403）
- 好友名單只存 LINE 提供的匿名 userId，不存姓名或電話
- 提醒內容由規則引擎依法條計算，不是 AI 生成，因此不會「幻覺」出錯誤期限
