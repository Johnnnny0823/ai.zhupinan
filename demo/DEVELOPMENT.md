# 竹聘安決賽示範系統

基線：`dc6e636cf74c70d633b54fdbf23aaa63ead044ba`，分支 `release/hackathon-2026`。
本版本只處理合成示範。沿用 FastAPI、原生 HTML/CSS/JS、既有 validation 規則／檢索，不需要 Node 打包。
法規與資安正式審查、真實資料處理及市府正式介接均不在本次範圍。

## Windows 11／PowerShell 啟動（目標20分鐘，尚待全新Windows實機計時）

先安裝 Python 3.12；從倉庫根目錄執行：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r demo/requirements.lock.txt
Copy-Item demo/.env.example demo/.env
notepad demo/.env
```

在 `.env` 保留 `DEMO_DATA=true`，將三個 `DEMO_LOGIN_*` 改成**不同且至少8字元**的登入碼。
本機使用 `PUBLIC_ORIGIN=http://127.0.0.1:8765`；用瀏覽器開啟同一來源，不能改用 localhost。
`.env`、LINE金鑰、SQLite、原件與本機log不進版控。

```powershell
.venv\Scripts\python -m demo.run seed
.venv\Scripts\python -m demo.run serve
```

瀏覽器開啟 <http://127.0.0.1:8765/>。帳號是 employer-a、employer-b、officer。
A是家庭看護雇主、B是產業雇主；officer同時是合成示範管理員，不可讀雇主案件。
每個登入碼24小時有效、使用一次後失效，Session有效8小時。登出後需重新發碼：

```powershell
.venv\Scripts\python -m demo.run codes
```

`codes` 只重新啟用環境中的登入碼，不輸出碼。展示者另外交付登入碼，避免截入畫面。
API修改請求必須帶正確Origin；命令列呼叫也一樣。所有個案回應no-store。

## macOS／Linux

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r demo/requirements.lock.txt
cp demo/.env.example demo/.env
# 修改 demo/.env 後：
.venv/bin/python -m demo.run seed
.venv/bin/python -m demo.run serve
```

本輪實際環境：Python 3.12.14，套件實際版本固定於 requirements.lock.txt。
測試依賴另在 requirements-dev.txt，主要流程不依賴Node或瀏覽器自動化套件。

## 初始化、清空與重建

```sh
python -m demo.run seed   # 不重複產生已有文件及待辦；啟用登入碼
python -m demo.run reset  # 清空並重建固定合成案件，所有session失效
python -m demo.run empty  # 清空案件／文件／證明／LINE／通知／暫存，不重建案件
```

reset在單一SQLite交易刪除；暫存刪除失敗會回滾資料庫。SQLite開啟foreign_keys，每次寫入有交易。
原件及遮蔽預覽不持久化。上傳由記憶體檢查，框架暫存UploadFile在讀取後關閉；模型提示及合成掃描轉存由TemporaryDirectory finally清理。
啟動時清除舊版uploads、cache、tmp殘留。非合成環境拒絕啟動或重置。
前端的確認草稿只在伺服器記憶體存必要欄位與digest，10分鐘過期；取消、登出、刪文件與重置會移除。
保留的SHA-256只是比對與去重，**不是個資匿名化證明**。

## 模型與故障備援

即時擷取與檢核需要在展示電腦安裝並登入Claude CLI（`claude auth login`）。
文字先執行既有privacy.mask；圖片／含圖PDF僅允許內建合成掃描檔案的完整digest，不能用勾選合成的方式放行真實掃描件。
模型失效會顯示可讀原因，不會暗中退回範例。選「預存示範結果」後只接受固定合成內容，畫面持續標示。
問答預設採工作包第7節允許的「已確認日期＋相關條文」文字模式；不保存聊天歷史。
即時模型說明可選，回傳未確認ISO日期時會被拒絕。
`/local-demo.html` 是獨立的公開固定預存展示；不讀取Session，不發LINE。

## LINE與Windows每日排程

在 `.env` 設定 `LINE_CHANNEL_ACCESS_TOKEN`、`LINE_CHANNEL_SECRET`。HTTPS對外入口與`PUBLIC_ORIGIN`必須一致，Webhook設為`https://展示來源/line/webhook`。
展示版不內建公開隧道、不部署真實資料；HTTPS反向代理由展示機管理者設定。
HTTPS來源會啟用Secure cookie，且Origin逐次檢查。

登入雇主→LINE提醒→取得配對碼→在指定官方帳號輸入→重新查詢→預覽→發送本帳號測試。
不查好友清單、不群發。每個待辦／類型／日期唯一；失敗以相同LINE retry key重試。
網路結果不明超過23小時停止自動重試，避免超出LINE的retry key有效期後重複發送。

Task Scheduler建立每日09:00工作：

- 程式：`C:\竹聘安\.venv\Scripts\python.exe`（換成展示機實際絕對路徑）
- 引數：`-m demo.run notify`
- 開始位置：`C:\竹聘安`
- 每天一次；錯過可補執行；不要讓相同工作並行。

程式只在到期前7、3、1日及當日發送，時區Asia/Taipei。可手動重跑，已成功紀錄不重發。
本輪使用stub驗證Push/Reply、失敗、重試及隔離，**尚無兩支實體手機收訊證據**。

## 可重跑驗收

```sh
python -m pip install -r demo/requirements-dev.txt
python -m pytest demo/tests -q
python -m demo.verify_baseline
python validation/scripts/test_privacy.py
node --check demo/web/app.js
node --check demo/web/local-demo.js
node --test demo/tests/sw_test.cjs
```

前三項不需模型金鑰。verify_baseline重播已提交的33筆日期、10題問答與30份裁處書輸出，明確標記非即時模型回歸。
重新跑即時模型的原有指令（可能受登入與額度影響）：

```sh
# PowerShell用 $env:QSET="holdout"；其他shell用 QSET=holdout
QSET=holdout python validation/scripts/qa.py run --model haiku --cond rag2s
python validation/scripts/penalty.py run --model haiku
```

原腳本若已有runs會跳過，需用獨立備份目錄保留原結果後再跑，不能以「cached」當即時成功。
原驗證報告仍保留於validation/驗證報告.md。
瀏覽器操作、四尺寸截圖與待驗項目見[ACCEPTANCE.md](ACCEPTANCE.md)及[evidence](evidence/)。

## 舊state.json遷移

只允許既有**合成**資料，先預覽：

```sh
python -m demo.migrate_state demo/server/data/state.json --owner employer-a --case-id case-a --synthetic
python -m demo.migrate_state demo/server/data/state.json --owner employer-a --case-id case-a --synthetic --apply
```

執行前備份來源JSON及SQLite至被忽略的data/migration-backup；整批交易，失敗回滾。
只轉必要欄位，原件不轉，舊的AI「完成」判斷不轉done。工作包以外的真實資料遷移不開放。

## 版本與日曆

日期一律在`validation/scripts/rules.py`；release API使用`compute_traced`。
`compute`保留既有歷史驗證輸出；新API對範圍外期限回needs_review及null，不顯示週末推測。
2026／2027 CSV已與官方資料逐日比對，休假日120／121日全部一致，見evidence/calendar-check.json。
條文版本及hash由health回傳。來源連結與核對限制見[LEGAL_SOURCES.md](LEGAL_SOURCES.md)。

## 凍結與交接

依工作包，**2026-11-19晚間**完成實機及法規文案核對後才建立release標籤；現在不預先標記凍結。
此後只修P0／P1。未取得的實機、Windows計時及組內簽核不可勾選通過。
