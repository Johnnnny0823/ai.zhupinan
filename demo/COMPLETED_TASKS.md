# 已完成任務與本輪交付

整理日期：2026-11-15（Asia/Taipei）。分支：`release/hackathon-2026`。
本輪依使用者確認交付程式與證據，實機驗收稍後補。此處列已實作及已有證據的子項目，**不表示S00–S10整包最終驗收完成**。
待驗項目另列於[PENDING_VALIDATION.md](PENDING_VALIDATION.md)；完整對照見[ACCEPTANCE.md](ACCEPTANCE.md)。

## 程式與文件

| 工作包 | 已完成的任務 | 程式／文件與證據 |
|---|---|---|
| S00 基線與環境 | 記錄基線commit、建立release分支；Python3.12鎖定依賴；啟動、環境變數、重置、API文件及示範標記 | [DEVELOPMENT.md](DEVELOPMENT.md)、[API.md](API.md)、requirements.lock.txt、run.py、啟動DEMO.bat；[乾淨macOS環境安裝與測試](evidence/clean-install.txt) |
| S01 資料模型與權限 | SQLite取代共用state；兩雇主案件隔離、承辦人角色、一次性登入碼、Session雜湊／過期／登出、Origin檢查與錯碼限流；重置交易；舊合成state的預覽、備份、遷移與回滾 | server/schema.sql、db.py、auth.py、migrate_state.py；[API驗收測試](tests/test_acceptance.py) |
| S02 文件與隱私 | 檢查內容及MIME、15MB／PDF10頁；阻止非內建合成掃描件出站；文字先遮蔽；暫存原件清理；擷取與確認分離、取消草稿、改日期後重新計算、刪文件 | server/storage.py、llm.py、app.py；[模型失效備援畫面](evidence/model-failure.jpg)、[文件確認畫面](evidence/confirmation-390.jpg) |
| S03 期限、待辦與證明 | 沿用確定性rules.compute；新增可追溯計算與法規／日曆版本；範圍外needs_review；文件去重；證明判讀不自動done、人工確認完成、保留逾期事實與操作紀錄 | validation/scripts/rules.py、server/domain.py；[待辦詳情](evidence/detail-390.jpg)、[人工確認完成](evidence/proof-confirmed.jpg) |
| S04 手機介面 | 原生HTML/CSS/JS接實際API；待辦、文件確認、詳情、聯絡、LINE等畫面；篩選、來源邊註、載入／空資料／失敗畫面；鍵盤勾選及Enter確認完成已操作 | web/index.html、app.css、app.js；[24組尺寸檢查](evidence/browser-layout.json)、[320像素畫面](evidence/tasks-320.jpg) |
| S05 LINE程式 | 六位一次性10分鐘配對碼；原始body先驗簽；按雇主綁定查待辦／Push／Reply；解除；去識別化預覽；7／3／1／0日通知命令；冪等、並行防重與失敗重試 | server/notifications.py；[LINE預覽與未寄送說明](evidence/line-390.jpg)；API測試使用stub，真實手機實收仍待驗 |
| S06 聯絡確認 | 依實際應工作日、出勤、有無正當理由、聯絡及可核實住宿資訊給指引；週末值班納入、休息日不納入；1955求助不自動排除；特殊期間轉主管機關；不宣告已行蹤不明 | server/missing.py；六例及跨週末測試；[操作畫面](evidence/missing-390.jpg) |
| S07 個案問答 | CaseContext只讀有權限且已確認的日期；四段文字模式、既有條文檢索、條文ID／版本／時間紀錄；新增5題個案測試與惡意指令測試；拒絕模型補未確認ISO日期 | server/app.py；[問答畫面](evidence/qa.jpg)；文字模式依工作包第7節允許的縮減，不保存聊天歷史 |
| S08 承辦人 | officer獨立入口；七項結果轉為已找到／可能缺漏／需人工判斷，附草稿片段、法條與補查方向；合成草稿、耗時、失敗重試／明示預存備援；不保存草稿原文 | server/app.py、web/app.js；[七項檢核畫面](evidence/penalty-1280.jpg)；30份歷史預存結果轉譯測試 |
| S09 PWA與離線 | Manifest、192／512圖示、只快取公開白名單的Service Worker、版本更新清舊快取、公開離線頁與獨立固定預存展示頁、iOS文字指引 | web/sw.js、app.webmanifest、offline.html、local-demo.html；[公開離線頁](evidence/offline-public.jpg)、[離線預存互動](evidence/offline-local-proof.jpg) |
| S10 種子與整合 | A／B雇主及承辦人種子、三份固定合成文字範例、兩案已確認資料與待確認入口、合成草稿；reset後再走API五段流程；故障備援、3–4分鐘操作路線及截圖索引 | seed.py、reset.py、[DEMO_SCRIPT.md](DEMO_SCRIPT.md)、[重置後登入畫面](evidence/reset-login.jpg) |

## 已取得的驗證結果

| 驗證 | 結果 | 證據／限制 |
|---|---|---|
| 後端及整合驗收 | 95項通過 | [pytest.txt](evidence/pytest.txt)；涵蓋權限、檔案、狀態、範圍外日曆、LINE stub、遷移／回滾、HTTPS Cookie及五段流程重置後重走 |
| Service Worker邊界 | 9項通過 | [service-worker-tests.txt](evidence/service-worker-tests.txt)；不是手機安裝或DevTools實機檢查 |
| 歷史日期結果 | 33/33一致 | [baseline-replay.json](evidence/baseline-replay.json)；保留舊compute結果，新API對範圍外不顯示推測日期 |
| 歷史問答保留題 | 10/10通過 | 同上；重播既有輸出，**不是本輪即時模型回歸** |
| 歷史裁處書結果 | 30份草稿，缺漏偵測29/30 | 同上；**不是本輪即時模型重跑** |
| 文字遮蔽 | 77份文件、266筆個資，0洩漏、日期／條文0誤遮 | [遮蔽報告](../validation/results/privacy_leak_test.md)；**不含掃描圖** |
| 官方日曆比對 | 2026／2027休假日差異0 | [calendar-check.json](evidence/calendar-check.json) |
| 畫面尺寸 | 六畫面×四尺寸，共24組無水平溢出 | [browser-layout.json](evidence/browser-layout.json)；不是實體手機觸控驗收 |
| 瀏覽器主流程 | 文件確認、改日期、待辦、證明人工確認、聯絡指引、七項檢核及重置後再登入已操作 | [截圖目錄](evidence/)；即時模型不可用時明確切預存模式 |
| 服務不可達備援 | 停止後端後可重新開啟公開離線頁，預存展示仍可完成證明確認 | offline-public.jpg、offline-local-proof.jpg；尚非手機飛航模式 |

## 重跑方式

先依[DEVELOPMENT.md](DEVELOPMENT.md)建立Python3.12環境及本機demo/.env，再於倉庫根目錄執行：

```sh
python -m pip install -r demo/requirements-dev.txt
python -m pytest demo/tests -q
python -m demo.verify_baseline
node --test demo/tests/sw_test.cjs
```

原件、金鑰、demo/.env、SQLite及本機runtime資料不隨程式上傳。固定合成種子與截圖證據保留在倉庫。
