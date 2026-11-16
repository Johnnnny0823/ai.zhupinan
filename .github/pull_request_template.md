## 這張 PR 是什麼

- 誰：<A／B／C／核心組>（GitHub 帳號）
- 工作包：<S0X｜名稱>
- 分支：<feature/…>
- 依賴：<需要先合併的 PR，沒有就寫「無」>

## 使用者看得到的變化

-

## 變更

- 檔案：
- API／資料表更動（已同步 `demo/API.md`）：

## 驗收證據

- [ ] `.venv\Scripts\python -m pytest demo\tests -q` → 結果：
- [ ] 動到規則／擷取／問答／處分書：跑過 `python -m demo.verify_baseline` 離線基準，`git status` 無差異
- [ ] 介面：附 320／390／1280 px 截圖，沒有橫向捲動
- 工作包驗收情境逐條結果：

## 狀態（分開寫）

- 已進 Git：
- 畫面看得到：
- 實際操作驗證過：
- 尚未驗證：

## 已知限制與交接

-

- [ ] 只用合成資料；沒有提交 `.env`、`line.env`、`*.db`、上傳檔或 Token
