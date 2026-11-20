# Roy PR4 整合修正交付紀錄

日期：2026-11-17（Asia/Taipei）。依據：同日「Roy_PR4_整合修正工作包.md」及參考 ZIP。
執行帳號：RoyLin0905。PR：[z1nnz/zhupinan #7](https://github.com/z1nnz/zhupinan/pull/7)。
分支：`fix/c-final-windows-and-ports`，從整合後 `main` 的 `71de6bcc9849bc0b74799f2b97f55d290631760a` 建立。
任務 1–9 已實作；審查與合併由 z1nnz 處理。任務 10 **未做完整整理**，不列為完成。

## 任務與測試

| 任務 | 已完成行為 | 回歸測試／證據 |
|---|---|---|
| 1／時區 | 鎖定 `tzdata==2026.6`；沒有系統 IANA 資料庫時仍能取得台灣日期 | `tests/test_pr4_windows.py`，子程序清空 `PYTHONTZPATH`，驗 `config.today()` 與安裝版本；Windows 案件、待辦詳情皆回 200 |
| 2／換行 | 預存裁處書雙方解碼後統一 CRLF→LF 再雜湊；固定合成文字以 `.gitattributes` 強制 LF | 同上，四種換行組合通過，變動內文仍拒絕；既有 30 份預存裁處書與整合流程仍通過 |
| 3／編碼 | demo 程式、基準重播與測試文字讀取明確指定 UTF-8；batch 留 UTF-8 保險 | 同上，AST 掃描與模擬 CP950 預設編碼；Windows 完整測試不設 `PYTHONUTF8` |
| 4／期限 | 新增獨立日期算法，只依實際檢查的日曆日期判斷涵蓋範圍；期間與許可屆滿保留日期；更新固定離線資料及版本 | `tests/test_pr4_deadlines.py`：250 筆逐筆相同、獨立算法不一致時轉人工確認、只有 doc_H12 的 termination_notice 因日曆跨 2028 被標記 |
| 5／登入 | 依帳號＋第一個有效 X-Forwarded-For IP 鎖定；帳號另有 10 分鐘 50 次失敗上限 | `tests/test_pr4_auth.py`：其他來源可登入、60 個輪換來源仍被擋、帳號隔離及時間到期 |
| 6／日期核對 | 日期逐欄判定掃描／國字／民國年與分隔格式／缺原文；未改原值須列在 checked；改值即視為已核對；未勾回 422＋unchecked，畫面逐欄紅框 | `tests/test_pr4_field_checks.py`：未勾、已勾、修改日期重算、多移工、來源片段及日期格式；Windows 瀏覽器實際操作 |
| 7／文字檔 | UTF-8 含 BOM、有 BOM 的 UTF-16、CP950 依序解碼，要求可列印比例 >97%；二進位回 415 與另存 UTF-8 提示 | `tests/test_pr4_encoding.py`：三種編碼、雙端序 UTF-16、門檻邊界、二進位及擷取／證明端點 |
| 8／發碼 | 選 (a) 維持一次性碼；DEVELOPMENT 與 DEMO_SCRIPT 說明 seed 首次發碼、每次重新登入前 codes，以及操作者私下發給評審 | 避免新增另一套長效團隊登入機制；只由操作者在本機管理設定，不公開登入碼 |
| 9／CI | Ubuntu／Windows matrix、完整 pytest／基準／SW；保留原 required status `tests`；Windows 另 seed、serve 與 Chromium 操作留圖 | 下列真實 CI 輸出、環境報告、截圖；明確不設 `PYTHONUTF8` |

任務 1–7 各先加失敗測試再修正，原始 red／green 輸出見 [red-green/](evidence/pr4-2026-11-17/red-green/)。歷史失敗輸出是修正前證據，不代表目前仍失敗。每項提交以任務編號開頭，保留逐項提交歷史。

`rules.compute()` 的 AST 與整合後 main 完全相同；另寫 `validation/scripts/deadline_trace.py` 驗算，沒有改引擎。見 [rules-preservation.json](evidence/pr4-2026-11-17/rules-preservation.json)。

範例入國日 2026-03-05、許可到 2029-03-04 的結果：

| 期限 | 到期日 | 狀態 | 日曆檢查 |
|---|---|---|---|
| 聘僱許可屆滿 | 2029-03-04 | todo | 不需辦公日曆 |
| 期滿續聘申請末日 | 2029-01-04 | todo | 不需辦公日曆 |
| 第 30 個月健檢末日 | 2028-10-05 | todo | 不需辦公日曆 |

## 實際 CI 證據

程式提交 `5064ffd531c87522d404e0a67bc0c382f13534a0` 的 [Actions #17](https://github.com/z1nnz/zhupinan/actions/runs/44085129504) 已完成：Linux、Windows 與彙總 `tests` 全綠。Windows Server 2025／Python 3.12.10，預設編碼 CP1252，`sys.flags.utf8_mode=0`、`PYTHONUTF8` 未設定。這一輪使用全新 hosted runner 的 Python，之後另補全新 venv 的完整重跑，見下方保存的環境紀錄。

全新 venv 重跑：[Actions #18](https://github.com/z1nnz/zhupinan/actions/runs/44085938666)，提交 `3a0428e474b184867a0859e4353d53611047c07e`。Linux、Windows 與 `tests` 全數成功。兩平台環境紀錄均確認 `fresh_venv=true`、未設定 `PYTHONUTF8`、`utf8_mode=0`。

| 平台 | pytest | 基準重播 | Service Worker | 證據 |
|---|---|---|---|---|
| Windows Server 2025／Python 3.12.10／CP1252 | 138 passed，1 個套件棄用警告 | 期限 33/33、歷史 QA 10/10、歷史裁處書 29/30、遮蔽 266 筆零洩漏 | 9/9 | [環境](evidence/pr4-2026-11-17/windows/environment.json)、[實際 pytest 輸出](evidence/pr4-2026-11-17/windows/pytest.txt)、[基準 JSON](evidence/pr4-2026-11-17/windows/baseline.json)、[SW 輸出](evidence/pr4-2026-11-17/windows/service-worker.txt) |
| Ubuntu／Python 3.12.16／UTF-8 | 138 passed，1 個套件棄用警告 | 同上 | 9/9 | [環境](evidence/pr4-2026-11-17/ubuntu/environment.json)、[實際 pytest 輸出](evidence/pr4-2026-11-17/ubuntu/pytest.txt)、[基準 JSON](evidence/pr4-2026-11-17/ubuntu/baseline.json)、[SW 輸出](evidence/pr4-2026-11-17/ubuntu/service-worker.txt) |

Windows 實際 seed／serve 後操作共 11 組畫面，瀏覽器錯誤與 HTTP 5xx 都是 0。案件與待辦詳情 API 回 200；修改事件日為 2026-03-21 後，待辦重算為 2026-03-30。這是固定合成預存模式；不是本輪即時模型結果。

| Windows 畫面 | 320 px | 390 px | 1280 px |
|---|---|---|---|
| 未勾日期，兩欄紅框拒絕 | [截圖](evidence/pr4-2026-11-17/windows/unchecked-date-errors-320.png) | [截圖](evidence/pr4-2026-11-17/windows/unchecked-date-errors-390.png) | [截圖](evidence/pr4-2026-11-17/windows/unchecked-date-errors-1280.png) |
| 修改第一欄並勾選第二欄 | [截圖](evidence/pr4-2026-11-17/windows/edited-and-checked-dates-320.png) | [截圖](evidence/pr4-2026-11-17/windows/edited-and-checked-dates-390.png) | [截圖](evidence/pr4-2026-11-17/windows/edited-and-checked-dates-1280.png) |
| 承辦人預存七項檢核 | [截圖](evidence/pr4-2026-11-17/windows/officer-stored-penalty-320.png) | [截圖](evidence/pr4-2026-11-17/windows/officer-stored-penalty-390.png) | [截圖](evidence/pr4-2026-11-17/windows/officer-stored-penalty-1280.png) |

另有 [雇主登入後的案件待辦](evidence/pr4-2026-11-17/windows/employer-tasks-1280.png)、[待辦詳情](evidence/pr4-2026-11-17/windows/task-detail-1280.png)。[browser-report.json](evidence/pr4-2026-11-17/windows/browser-report.json) 記錄實際步驟及各寬度；[ci-provenance.json](evidence/pr4-2026-11-17/ci-provenance.json) 保存 Actions 提交、原 artifact ID 與檔案 SHA-256。證據提交在上述程式提交之後，避免將不同 SHA 混稱同一輪輸出；最新 PR head 的 CI 狀態以 PR Checks 為準。

共同執行命令：

```sh
python -m pip install -r demo/requirements-dev.txt
python -m pytest demo/tests -q
python -m demo.verify_baseline
node --test demo/tests/sw_test.cjs
```

Windows 瀏覽器另外安裝 CI 專用 `demo/requirements-browser.txt` 與 Chromium，執行 `python -m demo.ci_smoke`。使用臨時 SQLite、臨時合成登入碼及固定合成資料，依文件執行 seed／serve；沒有連線即時模型、LINE，也不讀本機 demo/.env。

## API 與相容性

已同步 [API.md](API.md)：confirm 新增可選 `checked` 清單；對未修改的需核對日期，正式確認時必須填 `0:entry_date` 等欄位鍵。422 回傳 `unchecked`；預覽不寫入，修改值仍須通過日期／來源檢查。擷取的逐欄 warnings 保留原欄位鍵，沒有改資料表。

登入碼仍為一次性；重新登入前由操作者執行 `python -m demo.run codes`。已存在資料庫中的舊 calc_trace 不會自動改寫，展示前依 [DEVELOPMENT.md](DEVELOPMENT.md) 的升級段落重置合成資料，再取得新碼；reset 會失效原 Session。

## 狀態與保留待驗

- **已進 Git**：任務 1–9、回歸測試、API／操作文件、雙平台 CI 及證據。
- **畫面看得到、實際操作已驗**：Windows CI 的雇主登入、案件與待辦詳情、掃描日期紅框、逐欄勾選／修改重算、承辦人預存七項檢核；320／390／1280 px 有對應截圖與寬度檢查。
- **尚未驗證**：實體 Windows 11 展示機完整新裝與 20 分鐘計時、Task Scheduler、真實 LINE 兩手機收訊、即時模型擷取／裁處書／問答回歸、Android／iPhone 安裝與飛航模式、完整真人操作／鍵盤／觸控、法規負責人簽核、官方入口現場可達性。
- **尚未交付**：任務 10 的完整分號整理、真人備援影片、指定 concept 原稿比對、11/19 凍結標籤及團隊責任人／實際人時。任務 10 非本包合併阻擋項。

上列 CI Windows 是 Windows Server，瀏覽器尺寸是自動化視窗；不宣稱為實體 Windows 11 或手機。CP950 預設編碼另有模擬測試，CI Windows 真實預設是 CP1252。詳細原待驗清單 [PENDING_VALIDATION.md](PENDING_VALIDATION.md) 保留，沒有將外部驗收改寫為通過。

只用合成資料。未提交 .env、登入碼、Token、SQLite 或使用者上傳原件；本機外來的 `* 2.*` 重複檔原樣保留、排除提交。未直接更新 main 或已合併的 release 分支，未強制推送。
