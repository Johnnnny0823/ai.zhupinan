# Brief: 竹聘安 AI — UI mockup (static HTML)

Build a polished, static, clickable UI mockup for a hackathon finals demo. Output files in THIS folder only:
- `index.html` (single page app feel; tabs switch views with a few lines of vanilla JS; no build step, no external CDNs, no web fonts download — use system fonts: "Microsoft JhengHei", "Noto Sans TC", sans-serif)
- `styles.css`
All UI text in Traditional Chinese (Taiwan). Desktop width 1440px primary; must not break at 1280px.

## Product
竹聘安 AI helps (1) family / small-business employers of migrant workers in Hsinchu City keep legal deadlines, and (2) Hsinchu City Government case officers check penalty-decision drafts for missing legal elements. Core idea shown in UI: "AI 只讀日期，期限由規則依法條計算，每一項都附條號".

## Visual style (match the team's slide deck)
- Background warm off-white #FAF8F3; cards white with 1px #E6E2D8 border, radius 12px, subtle shadow
- Primary teal #2A8A7A (employer side), accent terracotta #C0754A (government side), dark text #1F2A33, muted #6B7280
- Status colors: overdue/defect red #C2412D, due soon amber #D69E2E, ok green #2F855A
- Clean, government-trustworthy, generous whitespace. No emoji icons; use simple inline SVG icons or text badges.

## Layout
Top bar: logo text "竹聘安 AI" + subtitle "移工聘僱合規助手｜新竹市" + role switch pills: 「雇主」「市府承辦人」. Small badge on right: "原型展示・資料為合成測試資料".

Left nav (changes with role):
- 雇主: 「上傳公文」「我的待辦」「法規問答」「LINE 提醒」
- 承辦人: 「處分書檢核」「法規問答」

### View 1 雇主 › 上傳公文 (3-step flow shown side by side or as stepper)
1. Upload box (drag & drop look) with an uploaded thumbnail labelled 「聘僱許可函.jpg」.
2. 「AI 讀到的資訊 — 請確認」: editable fields table for 2 workers: 姓名 NGUYEN THI LAN / DEWI LESTARI, 入國日 2026-03-10 / 2026-03-18, 聘僱許可期間 2026-03-10～2029-03-09 / 2026-03-18～2029-03-17. Each date field shows the original text snippet it came from in small grey (e.g. 原文：「一一五年三月十日」) and a confidence chip; one field flagged amber 「國字日期，請再確認」. Primary button 「確認無誤，產生待辦」.
3. Result preview: list of generated obligations, each row: task, deadline/window, countdown chip, legal basis in small text. Use these real rules:
   - 申請聘僱許可｜入國後15日內｜雇主聘僱外國人許可及管理辦法第36條
   - 入國三日內健康檢查｜入國後3個工作日內｜受聘僱外國人健康檢查管理辦法第3條
   - 第6個月定期健康檢查｜2026-08-11～2026-10-10｜健檢辦法第3條、就業服務法第57條第5款
   - 申請期滿續聘或期滿轉換｜屆滿前2～4個月（2028-11-09～2029-01-09）｜管理辦法第39、40條
   Footer note: 「期限依行政程序法第48條計算，遇假日順延；國定假日依人事行政總處辦公日曆」.

### View 2 雇主 › 我的待辦
Calendar-ish timeline + table of upcoming obligations for all workers, with filters (全部／7天內／已逾期). Summary cards: 「移工 2 位」「30 天內待辦 3 項」「已逾期 0 項」. Include a 「住宿地點變更」 quick action button that opens nothing (just looks clickable) with helper text 「搬宿舍後 7 日內須通知市府（管理辦法第33條）」.

### View 3 法規問答 (both roles)
Chat UI. Example exchange:
- User: 「我們工廠要把移工搬到新宿舍，搬完之後多久內要通知？」
- AI: answer 「搬遷（變更）後 7 日內，通知外國人工作所在地或住宿地點的當地主管機關（新竹市政府）。」 then a collapsible 「引用條文」 card quoting 雇主聘僱外國人許可及管理辦法第33條第5項: 「雇主於第二項第五款規定事項有變更時，應於變更後七日內，通知外國人工作所在地或住宿地點之當地主管機關。」 and a disclaimer line 「本回答依法條原文產生，非正式法律意見」.
Suggested question chips above input.

### View 4 雇主 › LINE 提醒
A phone frame mock showing a LINE-style chat from 「竹聘安 AI」 official account with 2 reminder bubbles (e.g. 「提醒：DEWI LESTARI 第6個月定期健康檢查期間 8/19 開始，請於 10/18 前完成。依據：健檢辦法第3條」 with buttons 「已完成」「查看說明」), and a settings panel next to it (提前提醒天數 7/3/1 天, 接收語言 中文/Bahasa Indonesia/Tiếng Việt).

### View 5 市府承辦人 › 處分書檢核 (terracotta theme)
Two columns: left = pasted draft 裁處書 text (use a realistic synthetic draft: 新竹市政府 裁處書（草稿）, 受處分人 竹塹電子材料股份有限公司, 事實: 外國人連續曠職三日失去聯繫未於三日內通報, 依就業服務法第56條第1項、第68條第1項, 罰鍰新臺幣30,000元, but 救濟教示 missing). Highlight the problematic area in the text.
Right = 7-item checklist with status: ①處分相對人 ✔ ②事實 ✔ ③違反條文 ✔ ④處罰條文對應 ✔ ⑤罰鍰在法定範圍（3萬～15萬）✔ ⑥陳述意見 ✔ ⑦救濟教示 ✘ with reason 「未載明救濟方法、期間及受理機關（行政程序法第96條第1項第6款；訴願法第14條、第58條）」 and suggested text 「如不服本處分，應自本處分書送達之次日起30日內，繕具訴願書經由本府向勞動部提起訴願。」 with copy button. Banner at top: 「是否裁罰、如何裁量，由承辦人決定；本工具僅提示缺漏」.

## Also
- Add a small "驗證數據" strip somewhere unobtrusive on the employer upload view or a footer: 「期限判讀正確率 91.7%（合成公文 217 項）｜法規問答 73%｜處分書缺漏偵測 97%」.
- Default view on load: 雇主 › 上傳公文. Make all tabs/role switches work with JS.
- Keep it to these two files; no frameworks. When done, print a short summary of files written.
