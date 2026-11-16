# 竹聘安開發規則（給 AI 助手）

Codex 會自動讀這個檔；Claude Code 讀 `CLAUDE.md`，兩份內容相同。完整流程見 `AI_WORKFLOW.md`、`CONTRIBUTING.md`。

- 這是 2026 新竹政策黑客松的**決賽示範系統**，只能使用合成資料（`DEMO_DATA=true`）。不得讀寫、上傳或提交真實公文、真實移工資料、訪談紀錄或個資；不可宣稱是正式政府服務。
- 核心原則：**模型只讀文件，法定期限一律由 `validation/scripts/rules.py` 依條文計算，由人確認與決定。** 不讓模型猜日期或補法條；規則無法判斷時顯示「需人工確認」。
- 工作範圍以 `docs/竹聘安_決賽系統開發_130人時.md` 的 S00–S10 為準；只做使用者指定的工作包。
- 技術棧固定：Python 3.12、FastAPI、Pydantic 2、SQLite、原生 HTML／CSS／JavaScript。不改用 React 或其他框架，不重寫規則引擎。
- 每個查詢案件、待辦、證明的 SQL 都要依 `owner_id` 限制；新端點沿用 `auth.employer`／`auth.officer` 與 `domain.owned_case()`、`owned_task()`，並在 `demo/tests/` 補越權測試。
- 上傳原件不得落地；文字送模型前先 `privacy.mask`；真實圖片不得送外部模型（只放行合成範例）。
- 從最新 `main` 開自己的分支（`<類型>/<誰>-sXX-<主題>`），不直接推 `main`、不強制推送；用使用者自己的 GitHub 登入，不讀取、不分享 Token。
- 每項變更都要跑 `.venv\Scripts\python -m pytest demo\tests -q`；動到規則、擷取、問答或處分書時另跑 `python -m demo.verify_baseline` 離線基準，結果不可退步。
- 不提交 `.env`、`line.env`、`*.db`、`demo/server/data/`、`uploads/`、`cache/`、`.venv/`。
- 回報時分清楚：已寫進 Git、已在畫面上看得到、已實際操作驗證、尚未驗證，四種狀態不可混用。不要把規劃或靜態畫面說成已完成。
- 保留使用者與其他協作者的修改；不覆寫別人的分支。
