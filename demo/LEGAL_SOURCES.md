# 條文、工作日曆與官方入口

核對日期2026-11-15。本輪核對官方來源、版本日期及日曆，不代表已完成組內法規負責人簽核或專家審查。

| 資料 | 本機版本 | 官方來源 |
|---|---|---|
| 就業服務法 | 民國114-01-20 | https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0090001 |
| 雇主聘僱外國人許可及管理辦法 | 民國114-12-30 | https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=N0090027 |
| 行政程序法 | 民國110-01-20 | https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=A0030055 |
| 受聘僱外國人健康檢查管理辦法 | 民國114-12-31 | https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=L0050018 |
| 連續曠職三日失去聯繫認定基準 | WDA官方PDF；未擅自填入修正日 | https://fw.wda.gov.tw/wda-employer/home/download-file/2c95efb3882b4eb201882d403147023b.pdf |
| 2026／2027政府辦公日曆 | 2026休假120日、2027休假121日；完整比對一致 | https://data.gov.tw/dataset/14718 |
| LINE簽章驗證 | 原始body HMAC-SHA256 | https://developers.line.biz/en/docs/messaging-api/verify-webhook-signature/ |
| LINE重試 | 相同UUID retry key，成功記錄不重送 | https://developers.line.biz/en/docs/messaging-api/retrying-api-request/ |

日曆下載URL、sha256與逐日差異見evidence/calendar-check.json；法條本機hash見`GET /api/health`。
既有rules.compute保留歷史驗證。正式頁面只用compute_traced：範圍外期限不公開；待辦為needs_review。
此處的版本資訊不代表已逐字做完全部法律適用審查，展示不得宣稱可正式試辦。

## 聯絡流程核對

本輪程式依官方認定基準第二至四點問實際應工作日、未到工及有無正當理由、聯絡結果、可查認住宿地點／期間／方式。
休息日不加天數；週末值班照計。求助1955並不直接排除，仍看資訊是否查認屬實。
第六點特殊期間／已終止聘僱另轉主管機關確認，避免一般班表計數套用例外。
不自動產生失聯日期、不自動建立「已行蹤不明」結果或失聯通報待辦。

組內法規核對人：**待指定**。六例文字對照與簽核：**待完成，不得簽成已驗**。

## 辦理入口白名單

- 勞動部線上申辦：https://fwapply.wda.gov.tw/
- 移工一站式：https://fwots.wda.gov.tw/
- 新竹市政府勞工及青年處：https://dep-labor.hccg.gov.tw/ （本次自動查閱403，頁面可達性待展示機確認）
- 新竹市衛生局：https://dep.hcchb.gov.tw/
- 國內外國人健檢指定醫院名單：https://www.cdc.gov.tw/Category/Page/nU7y97g0GqJbB3kn5B-nPg

窗口及連結由伺服器固定映射，不接受模型生成URL。未取得特定線上表單者導向官方窗口，不自行編造申辦網址。
