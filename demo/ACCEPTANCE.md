# S00–S10 驗收與自評

日期：2026-11-15（Asia/Taipei）。來源工作包：[WORK_PACKAGE.txt](WORK_PACKAGE.txt)。
基線`dc6e636cf74c70d633b54fdbf23aaa63ead044ba`，本機分支`release/hackathon-2026`。
**程式與本機驗證已交付；整包仍待外部實機及組內簽核，不標記全部完成。**
沿用nudge逐項核對與保留驗證證據的方法，不把未驗證事項當通過。驗收條件以S00–S10工作包為準；不另加85分、建立PR或CI全數通過的門檻。工作包對合併請求內容的規定，在實際需要合併請求時適用，依使用者最新指示，本輪上傳方式為推送程式與證據至GitHub的release分支，不另行建立PR或合併。

## 本輪交付安排（使用者已確認）

2026-11-15使用者確認：「本輪先交付程式與證據，實機驗收稍後補」。本輪交付程式碼、可重跑的本機測試結果、瀏覽器截圖、API與啟動文件及展示腳本。
LINE兩手機實收、Windows展示機與排程、Android／iPhone安裝及手機飛航模式等實機項目，依此安排保留待驗，稍後補證據；延期不代表通過或刪除工作包要求。即時模型回歸及組內法規簽核亦維持原表的待驗狀態。
本輪交付不以補完實機證據作為前提；整包最終驗收仍依下列指標逐項完成。

交接索引：[已完成任務](COMPLETED_TASKS.md)／[尚未完成的驗證](PENDING_VALIDATION.md)。

## 可重跑結果

- Python API／權限／規則／隱私邊界：**95項通過**，`python -m pytest demo/tests -q`，見[evidence/pytest.txt](evidence/pytest.txt)。
- Service Worker：**9項通過**，`node --test demo/tests/sw_test.cjs`；只快取公開白名單，API／LINE／未知路徑／原圖均不攔截。見[evidence/service-worker-tests.txt](evidence/service-worker-tests.txt)。
- 歷史輸出重播：33/33期限一致、問答10/10、原30份裁處書缺漏偵測29/30。見[evidence/baseline-replay.json](evidence/baseline-replay.json)。**不是本輪即時模型重跑**。
- 純文字遮蔽：77份文件、266筆個資，0洩漏、關鍵日期／條文0誤遮；**不含掃描圖**。見[既有測試報告](../validation/results/privacy_leak_test.md)。
- 官方日曆逐日比對：2026、2027休假120／121日，差異0。見[evidence/calendar-check.json](evidence/calendar-check.json)。
- 六個主要畫面×320／390／768／1280尺寸，共**24組無水平溢出**。見[evidence/browser-layout.json](evidence/browser-layout.json)與各尺寸jpg。不是Android／iPhone實機證據。
- 瀏覽器：選文件→模型失效→明確切預存→修改日期→預覽5項→確認→詳情→固定合成證明→鍵盤勾選／Enter完成，已走通。
- 一鍵重置後回登入，原Session失效，重新登入顯示固定案件；API五段流程→reset→再走一次測試通過。
- **停止後端服務後**重新載入local-demo仍可互動，完成固定證明確認；再開根目錄顯示公開離線說明、不含個案。見offline-public.jpg、offline-local-proof.jpg。這是本機服務不可達測試，尚非手機飛航模式驗收。
- 全新macOS虛擬環境的鎖定依賴安裝、pip check及測試結果見[evidence/clean-install.txt](evidence/clean-install.txt)。Windows未實機計時。

## 各工作包任務卡與指標

實作責任：Codex本機交付；團隊整合負責人、LINE手機保管人及法規核對人仍待組長指定。
下列「預估」沿用工作包人時，**不將模型運作時間偽報為人時**。實際人時欄保留未登錄。

| 包／預估 | 檔案與API變更 | 已達指標與證據 | 尚未完成／阻塞 | 實際人時 |
|---|---|---|---|---|
| S00／5 | DEVELOPMENT.md、API.md、requirements.lock.txt、run.py、啟動DEMO.bat；health | 分支、基線、Python3.12、鎖版、示範標記、啟動重置與基準重播 | 全新Windows20分鐘計時；缺少指定D:\concept草稿，本輪依工作包案件手帖視覺實作 | 未登錄 |
| S01／22 | schema.sql、db.py、auth.py、migrate_state.py；session／cases／tasks | 兩雇主越權404、匿名401、角色403、Origin、hash Session、錯碼限流、登出、reset回滾；95項測試內；migration預覽、備份、成功遷移與整批回滾通過 | 無已知本機阻斷 | 未登錄 |
| S02／15 | storage.py、llm.py；documents extract／confirm／delete | MIME＋內容、15MB、PDF10頁、真實掃描不出站、草稿未寫案件、改日期、266遮蔽、錯誤不留原件 | 本機無Claude CLI；即時掃描／文字模型實測未驗，只驗stub與固定範例 | 未登錄 |
| S03／13 | rules.compute_traced、domain.py；task／proof／confirm | 33規則不退步、原文與計算、越界needs_review、上傳不done、人工確認、late留存、重複確認不新增 | 無已知本機阻斷；新增年份仍須更新官方日曆 | 未登錄 |
| S04／26 | web index／css／js；真實API | 今日待辦、文件確認、詳情、聯絡及LINE五頁；24組尺寸、鍵盤確認完成、載入／空／失敗 | 實體手機點擊與無口頭提示使用者測試；完整純鍵盤流程尚待真人驗收 | 未登錄 |
| S05／14 | notifications.py、LINE教學；pair／preview／send-demo／webhook | 原始body驗簽、雙帳號Reply隔離stub、10分鐘一次碼、失效解除、Push指定對象、排程冪等、並行只送一次、失敗重試 | LINE金鑰及兩手機真實Push／Reply證據、Windows Task Scheduler每日執行紀錄 | 未登錄 |
| S06／8 | missing.py、前端、LEGAL_SOURCES.md；missing/guide | 6例＋跨週末休息橋接、值班納入、聯絡恢復、1955不足、核實安置、特殊期間轉介 | 組內法規負責人對照PDF簽名，尚未取得 | 未登錄 |
| S07／8 | app.qa；qa | 已確認CaseContext、四段文字模式、引用條文／版本／時間、5題個案及惡意指令、拒絕模型補ISO日期；歷史10題保留 | 即時模型白話模式未重跑；文字模式為工作包第7節允許的縮減 | 未登錄 |
| S08／6 | officer頁及penalty/check | 7狀態／來源片段／條號／補查、耗時、重試、固定草稿、officer角色、草稿不保存；30份預存轉譯回歸 | 保留Haiku原配置，但本輪即時30份回歸未跑；歷史29/30不可當作新模型成功 | 未登錄 |
| S09／7 | manifest、192／512圖示、sw、offline／local-demo | 公開白名單、9測試、停止後端的離線說明與預存互動、舊版cache清理、iOS文字指引 | Android Chrome安裝、iPhone加入主畫面、飛航模式、DevTools實際Cache Storage逐項核對未完成 | 未登錄 |
| S10／6 | seed／reset、DEMO_SCRIPT、evidence | 3份固定合成文字範例、2案已確認種子與第三份待確認入口、草稿、雙輪API全流程、reset後重走、失敗／替代畫面、截圖索引 | 每段實體手機截圖／備援影片、11/19晚間凍結tag；尚未到凍結時間，不提前偽造 | 未登錄 |

本輪開發測試曾抓到超大multipart請求被框架轉成英文400，已改為在解析前限制總body並回繁體中文413；保留17MB拒絕案例。初次重複匯入測試也修正為比較ID集合，API不保證列表順序，待辦數量仍嚴格驗證。

## P0與P1逐項

| 指標 | 結果 | 證據與界線 |
|---|---|---|
| 跨帳號可見 | 本機測試通過 | cases／tasks／proofs／documents／QA越權拒絕；officer無雇主讀權 |
| 推播誤投 | stub通過、真機待驗 | 兩個LINE user對應兩個owner，不群發；真實兩手機未驗，不可宣稱整體P0全過 |
| 真實掃描出站 | 本機通過 | 未列入digest的圖片及含圖PDF在呼叫模型前拒絕；不靠checkbox放行 |
| 日期無來源／算錯 | 本機通過 | 舊33/33、source_excerpts、法條／日曆hash與計算；越界null |
| 原件刪除失敗 | 本機通過 | 記憶體／UploadFile.close／TemporaryDirectory、模型例外、取消、刪除及reset；清理失敗DB回滾 |
| 五段Demo主流程 | 本機通過、外部服務待驗 | 預存／文字模式可連續；實收LINE及即時模型需補外部證據 |
| 手機主按鈕遮蔽／白屏 | 瀏覽器尺寸通過、實機待驗 | 截圖無水平溢出；實體安裝與點擊仍開放 |
| 承辦人無回應且無備援 | 本機通過 | 模型故障明示、固定草稿stored、離線固定七項頁 |

## 參考自評（100分，未驗證不算通過；不作額外驗收門檻）

| 類別 | 得分 | 扣分理由 |
|---|---:|---|
| 內容與交付完整性 | 23/25 | 核心程式、文件與截圖已備；指定concept原檔未取得、實體截圖／影片未交 |
| 每項任務指標 | 26/35 | LINE真機、Windows啟動／排程、Android／iOS安裝、真人主流程與法規簽核未達；不刪掉這些必達項 |
| 測試、驗證與證據可信度 | 20/25 | 本機與負面測試、舊結果重播、實際瀏覽器尺寸／斷服務完成；即時模型回歸與實體裝置未有結果；CI不列為驗收或扣分條件 |
| 可審查性、範圍與交接 | 14/15 | API／依賴／法源／重置／備援路線明確；團隊責任人與正式現場交接待指定 |
| **總分** | **83/100** | **僅作參考。整包仍有工作包明列的實機驗收及簽核待完成；不因分數或CI額外阻擋交付。** |

本機測試通過不代表可以正式收真實公文。解除條件僅為原工作包已要求的外部驗收，沒有新增功能或審查門檻。

## 仍需組長填寫

- 四位責任人／整合負責人：待填。
- 分支合併規則：release/hackathon-2026已建立；團隊審查規則待填。
- LINE官方帳號與兩手機保管人：待填。
- 11/19凍結與11/20展示電腦：待填。
- 法規核對人：待填。
