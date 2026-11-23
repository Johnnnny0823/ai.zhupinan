# 決賽API契約

版本 `hackathon-2026.11.17`。Base URL同站；Swagger `/docs`、機器契約 `/openapi.json`。
僅合成示範，所有JSON個案回應 `Cache-Control: no-store`。沒有舊版`/api/todos`、`/api/line/send`等無權限相容入口。

## 共通規則

- POST／PATCH／DELETE `/api/*` 必須帶 `Origin: <PUBLIC_ORIGIN>`，缺少或不符403；不開CORS。
- 登入成功設HttpOnly、SameSite=Lax cookie；HTTPS加Secure。cookie只放隨機憑證，DB存SHA-256。
- 匿名401，角色錯誤403；不存在及其他雇主的案件、待辦、文件、證明一律404。
- 一般格式錯誤422，檔案內容／MIME不符415，超過15MB為413，壞PDF415、超頁或加密400。
- 伺服器錯誤500、模型不可用502、LINE未設定Webhook密鑰503；回應`{"detail":"可理解的繁體中文錯誤"}`，不回傳原始模型輸出。
- 角色由Session決定，客戶端不可指定。承辦人不能讀雇主案件。
- 所有ISO日期為YYYY-MM-DD；計算及提醒以Asia/Taipei為今天，期限不由模型計算。

## 端點

| 方法／路徑 | 權限 | 請求／回應重點 |
|---|---|---|
| GET `/api/health` | 公開 | service、rules_version、calendar_years、demo_data、law_versions、law_retrieval；不含金鑰 |
| POST `/api/session` | 公開＋Origin | account_id、code；成功回account並設cookie；401錯碼／過期／已用、相同帳號＋來源五次失敗後429鎖五分鐘；另有帳號跨來源10分鐘50次總上限 |
| GET `/api/session` | 已登入 | account、synthetic |
| DELETE `/api/session` | 已登入＋Origin | Session即失效；清除cookie及記憶體草稿 |
| GET `/api/cases` | employer | items，僅owner本人 |
| GET `/api/cases/{id}` | employer owner | case、tasks、documents、synthetic |
| GET `/api/demo/samples` | employer | 三份固定合成文字及label；供選樣及明示備援 |
| GET `/api/demo/replay` | 公開，唯讀 | 開場案例重播：依公開訴願決定日期，以`compute_traced`重算第18個月健檢期間、依`REMINDER_DAYS`列LINE提醒時點、以`proof_verdict`判讀實際日期；不讀資料庫，不含任何帳號或案件資料 |
| POST `/api/documents/extract` | employer＋Origin | multipart file、mode=live或stored；合成掃描圖的即時模式使用 PaddleOCR；回draft_id、document_kind、workers、fields、masked_preview、mode、warning；不寫案件 |
| DELETE `/api/documents/drafts/{id}` | employer＋Origin | 取消記憶體草稿；相同呼叫可重跑 |
| POST `/api/documents/confirm` | employer owner＋Origin | 見下例；回task_ids、duplicate、warnings；preview_only不寫入 |
| DELETE `/api/documents/{id}` | employer owner＋Origin | 刪文件、相關待辦／證明／通知，清除草稿；不保存原件 |
| GET `/api/tasks/{id}` | employer owner | task、proofs、document、audit_events；含calc_trace及依今天推導的overdue |
| PATCH `/api/tasks/{id}` | employer owner＋Origin | 僅`{"status":"delegated"}`，其他轉移用證明／確認端點；不合法409 |
| POST `/api/tasks/{id}/worker-notice` | employer owner＋Origin | lang=id／vi／en、mode=stored或live；回lang_name、text、zh（中文對照）、mode、notice。只含事項種類與日期、1955專線，不含姓名、證號、地址；純雇主手續（如申請聘僱許可）或期限未確認回409；live模式由模型翻譯，日期與1955缺漏或多出日期即回422，模型失效回502 |
| GET `/api/tasks/{id}/proof-sample` | employer owner | 此待辦固定合成證明text；不適用未確認期限409 |
| POST `/api/tasks/{id}/proof` | employer owner＋Origin | multipart file、mode；回proof、status=proof_submitted及mode；不自動done |
| POST `/api/tasks/{id}/confirm` | employer owner＋Origin | proof_id、confirmed=true、matches_task=true、observed_date；早於期間需明示outside_window_acknowledged；回status=done及verdict |
| DELETE `/api/tasks/{id}/proof/{proof_id}` | employer owner＋Origin | 刪未完成之證明；無剩餘證明回todo；done不可刪409 |
| POST `/api/line/pair-code` | employer＋Origin | code、expires_at、instruction；六位、一次性、10分鐘 |
| DELETE `/api/line/binding` | employer＋Origin | 撤銷此帳號綁定及配對碼 |
| POST `/api/line/preview` | employer＋Origin | count（範圍內總數）、bound、configured、text、reminder_days、upcoming_days。只列本帳號今天起至 30 天後共最多 8 項近期待辦，無全名／地址等 |
| POST `/api/line/send-demo` | employer＋Origin | 只選本帳號最近一項待辦；status、recipients、reason、request_id；當日冪等 |
| POST `/line/webhook` | LINE HMAC簽章 | **原始body先驗簽才parse JSON**；配對、待辦、取消綁定／unfollow；事件去重 |
| POST `/api/missing/guide` | employer＋Origin | 班表與聯絡事實，見下例；回status、missing_facts、next_step、law_ref、official_url；不新增失聯待辦 |
| POST `/api/qa` | 已登入＋Origin | question、case_id（雇主必填）、mode=text或live；四段sections、citations、case_context、data_version、answered_at、retrieval（qdrant_bm25 或 bm25） |
| GET `/api/penalty/sample` | officer | 固定合成text |
| POST `/api/penalty/check` | officer＋Origin | text、mode=live或stored；七項items及耗時；不保留草稿原文 |
| POST `/api/demo/reset` | officer且is_admin＋Origin | `{"rebuild":true}`清空重建，false只清空；Session全失效 |

## 範例：登入、讀取、確認

```http
POST /api/session
Origin: http://127.0.0.1:8765
Content-Type: application/json

{"account_id":"employer-a","code":"展示者提供的一次性碼"}
```

```json
{"account":{"id":"employer-a","role":"employer","display_name":"家庭看護雇主 A｜合成示範","is_admin":0},"synthetic":true}
```

上傳multipart：file=合成公文、mode=stored（明確選用固定結果；任意文件不允許stored）。
回應節錄：

```json
{"draft_id":"隨機暫時憑證","expires_in":600,"document_kind":"入國通報受理證明書","mode":"預存示範結果","fields":[{"worker_index":0,"field":"entry_date","value":"2026-11-13","source_excerpt":"入國日期：2026-11-13","warning":"需核對：日期與文件種類均須人工確認"}],"synthetic":true}
```

```http
POST /api/documents/confirm
Content-Type: application/json
Origin: http://127.0.0.1:8765
Cookie: zpa_session=隨機憑證

{"case_id":"case-a","draft_id":"上一步的暫時憑證","document_kind":"入國通報受理證明書","fields":[{"entry_date":"2026-11-14","name":"移工代號01"}],"confirmed":true,"preview_only":false}
```

```json
{"task_ids":["待辦ID"],"duplicate":false,"warnings":["超出日曆範圍的日期不推算，請於待辦詳情核對"],"synthetic":true}
```

同一文件digest＋案件重傳回原task_ids，順序不作保證；不修改既有人工確認的紀錄。
預覽用`preview_only=true, confirmed=false`回`task_count`。正式確認false為422；draft過期／非本人為410。

calc_trace含event、event_date、start_date、rule、original_due_date、holiday_adjustment、final_due_date、law_versions、calendar_version、calendar_years、rules_version、source_excerpts。
每項task另有rule_key、law_ref、office、官方白名單official_url、status。
日曆範圍外`due_date=null, status=needs_review`，沒有推測日期可被LINE誤用。

## 證明兩步

上傳回`proof.verdict=on_time`仍是`status=proof_submitted`。確認請求：

```json
{"proof_id":"已上傳證明ID","observed_date":"2026-11-25","matches_task":true,"confirmed":true,"outside_window_acknowledged":false}
```

完成回`{"status":"done","verdict":"on_time"}`；晚於原期限仍能完成，但保留late及原due_date。
`PATCH status=done`拒絕422。不得省略人工核對；相同確認重按回duplicate=true。

## 聯絡流程

```json
{
 "today":"2026-11-15","today_scheduled":true,"last_attendance":"2026-11-12",
 "work_days":[
  {"day":"2026-11-13","scheduled":true,"absent":true,"justified":false},
  {"day":"2026-11-14","scheduled":true,"absent":true,"justified":false},
  {"day":"2026-11-15","scheduled":true,"absent":true,"justified":false}
 ],
 "contact_attempted":true,"contact_result":"unreachable",
 "location_verified":false,"accommodation_period_verified":false,"contact_method_verified":false,
 "sought_1955":false,"relationship_active":true,"special_period":false
}
```

`contact_result`只接受unreachable／uncertain／recovered。特殊期間或聘僱已終止轉主管機關確認，不套普通應工作日計數。
回應狀態僅「先聯繫及確認」「可能符合要件，請核對」「需盡速向主管機關確認」。不得當成行政認定。

## LINE發送結果

```json
{"status":"sent","recipients":1,"reason":null,"request_id":"LINE回傳ID"}
```

其他status：duplicate、skipped、failed、uncertain。sent表示LINE接受請求，**不等於已在手機實收**。
未綁定recipients=0；不包含收件人LINE ID。失敗只記錯誤分類，不記訊息全文或金鑰。

## 問答與裁處書

問答的CaseContext由owner查詢後組裝，不接收客戶端提供的個案事實；未確認草稿不帶入。
模型不得補日期，條文文字模式不作模型推論；audit僅保存條文ID、版本與時間。
處分書每項回name、status、reason、source_excerpt、law_ref、next_step；狀態只為「已找到／可能缺漏／需人工判斷」。
草稿明顯標示僅輔助，不送出處分。

登入來源使用X-Forwarded-For第一個有效IP，沒有可用值時使用連線來源。來源可偽造，因此仍以帳號總上限限制猜碼；不把其他帳號或其他來源一起鎖住。既有login_attempts表存雜湊鍵，帳號總計的updated_at用作10分鐘視窗起點，未新增資料表。

文件確認新增`checked: ["0:entry_date"]`，鍵為「移工索引:欄位」。擷取的`fields[].warning`依個別日期的掃描／國字／民國年／缺原文狀態回傳string或null。需核對且維持擷取原值的日期未列入checked時，正式確認回422及`unchecked`清單，不寫案件；自行修改日期視為人工確認。preview_only只預覽數量，不要求checked，也不寫入。`confirmed=true`仍為整份確認的必要條件。

TXT在MIME與實際內容檢查後，依UTF-8（含BOM）、具BOM的UTF-16、CP950解碼；可列印字元（含換行／Tab）須超過97%，含NUL或不符則415並提示另存UTF-8。固定文字預存結果及證明按解碼文字統一CRLF後比對，不以編碼差異拒絕同一合成內容；圖片白名單仍使用原始bytes的digest。

## 靜態資料（市府視角地圖）

- `/city.html`：公開頁，three.js（`/vendor/three.module.min.js`，0.160.0，MIT）畫新竹市三區立體地圖。
- `/data/hsinchu-districts.json`：東區、北區、香山區界線，取自內政部國土測繪中心鄉鎮市區界線（經 taiwan-atlas 2021.9.20 轉檔，政府資料開放授權）。
- `/data/hsinchu-age.json`：各區總人口、65 歲以上、80 歲以上人口與里數，取自內政部戶政司開放資料 ODRP052（113 年 12 月底），由各里加總為區；全市合計 457,242 人，與新竹市民政處簡表一致。
