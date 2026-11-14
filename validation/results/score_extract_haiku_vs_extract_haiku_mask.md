# 公文期限判讀驗證結果

| 指標 | extract_haiku | extract_haiku_mask |
|---|---|---|
| 文件類型 | 39/50（78.0%） | 35/35（100.0%） |
| 日期欄位 | 68/127（53.5%） | 68/68（100.0%） |
| 應辦期限 | 133/217（61.3%） | 133/133（100.0%） |
| 整份文件全對 | 35/50（70.0%） | 35/35（100.0%） |
| 多餘/錯誤提醒數 | 32 | 0 |
| 平均每份秒數 | 19.6 | 12.9 |
| 已跑文件數 | 50 | 35 |

## extract_haiku 分組明細

| 分組 | 文件類型 | 日期欄位 | 應辦期限 | 整份文件全對 |
|---|---|---|---|---|
| 全部 | 39/50（78.0%） | 68/127（53.5%） | 133/217（61.3%） | 35/50（70.0%） |
| 圖片 | 4/15（26.7%） | 0/59（0.0%） | 0/84（0.0%） | 0/15（0.0%） |
| 日期格式:iso | 3/6（50.0%） | 4/14（28.6%） | 11/27（40.7%） | 3/6（50.0%） |
| 日期格式:roc | 14/18（77.8%） | 23/44（52.3%） | 42/67（62.7%） | 12/18（66.7%） |
| 日期格式:roc_cn | 9/10（90.0%） | 15/30（50.0%） | 37/62（59.7%） | 8/10（80.0%） |
| 日期格式:roc_dot | 8/9（88.9%） | 17/19（89.5%） | 27/32（84.4%） | 8/9（88.9%） |
| 日期格式:roc_fw | 5/7（71.4%） | 9/20（45.0%） | 16/29（55.2%） | 4/7（57.1%） |
| 純文字 | 35/35（100.0%） | 68/68（100.0%） | 133/133（100.0%） | 35/35（100.0%） |
| 類型:住宿地點變更 | 4/6（66.7%） | 8/27（29.6%） | 8/15（53.3%） | 3/6（50.0%） |
| 類型:入國通報受理證明書 | 7/10（70.0%） | 6/11（54.5%） | 30/50（60.0%） | 6/10（60.0%） |
| 類型:再檢查診斷證明書 | 6/7（85.7%） | 6/9（66.7%） | 6/7（85.7%） | 6/7（85.7%） |
| 類型:期滿續聘許可函 | 6/8（75.0%） | 14/20（70.0%） | 35/50（70.0%） | 6/8（75.0%） |
| 類型:聘僱許可函 | 12/14（85.7%） | 30/54（55.6%） | 50/90（55.6%） | 10/14（71.4%） |
| 類型:聘僱關係終止 | 4/5（80.0%） | 4/6（66.7%） | 4/5（80.0%） | 4/5（80.0%） |

### 錯誤清單（82）

- doc_09：文件類型判成「聘僱許可函」，應為「期滿續聘許可函」
- doc_09（doc_09.png，roc）MARIA CLARA REYES 許可起日：抽成 None，應為 2026-08-27
- doc_09（doc_09.png，roc）MARIA CLARA REYES 許可迄日：抽成 None，應為 2029-08-26
- doc_09（doc_09.png，roc）ROSALIE DELA CRUZ 許可起日：抽成 None，應為 2026-07-26
- doc_09（doc_09.png，roc）ROSALIE DELA CRUZ 許可迄日：抽成 None，應為 2029-07-25
- doc_12：文件類型判成「聘僱許可函」，應為「住宿地點變更」
- doc_12（doc_12.png，roc）FITRI PURNAMA 入國日：抽成 2021-11-28，應為 None
- doc_12（doc_12.png，roc）FITRI PURNAMA 許可起日：抽成 2022-08-23，應為 None
- doc_12（doc_12.png，roc）FITRI PURNAMA 許可迄日：抽成 2022-11-27，應為 None
- doc_12（doc_12.png，roc）FITRI PURNAMA 事件日：抽成 None，應為 2027-11-04
- doc_12（doc_12.png，roc）FITRI HANDAYANI 入國日：抽成 2021-11-28，應為 None
- doc_12（doc_12.png，roc）FITRI HANDAYANI 許可起日：抽成 2022-08-23，應為 None
- doc_12（doc_12.png，roc）FITRI HANDAYANI 許可迄日：抽成 2022-11-27，應為 None
- doc_12（doc_12.png，roc）FITRI HANDAYANI 事件日：抽成 None，應為 2027-11-04
- doc_13：文件類型判成「住宿地點變更」，應為「聘僱許可函」
- doc_13（doc_13.png，roc_cn）MARK ANTHONY SORIANO 入國日：抽成 None，應為 2026-09-06
- doc_13（doc_13.png，roc_cn）MARK ANTHONY SORIANO 許可起日：抽成 None，應為 2026-09-06
- doc_13（doc_13.png，roc_cn）MARK ANTHONY SORIANO 許可迄日：抽成 None，應為 2029-09-05
- doc_13（doc_13.png，roc_cn）LE THI MAI 入國日：抽成 None，應為 2026-10-04
- doc_13（doc_13.png，roc_cn）LE THI MAI 許可起日：抽成 None，應為 2026-10-04
- doc_13（doc_13.png，roc_cn）LE THI MAI 許可迄日：抽成 None，應為 2029-10-03
- doc_17（doc_17.png，roc）MARK ANTHONY SORIANO 入國日：抽成 None，應為 2027-01-20
- doc_17（doc_17.png，roc）MARK ANTHONY SORIANO 許可起日：抽成 None，應為 2027-01-20
- doc_17（doc_17.png，roc）MARK ANTHONY SORIANO 許可迄日：抽成 None，應為 2030-01-19
- doc_20：文件類型判成「聘僱許可函」，應為「期滿續聘許可函」
- doc_20（doc_20.png，roc_dot）ROSALIE DELA CRUZ 許可起日：抽成 2013-02-13，應為 2027-05-03
- doc_20（doc_20.png，roc_dot）ROSALIE DELA CRUZ 許可迄日：抽成 None，應為 2030-05-02
- doc_22：文件類型判成「再檢查診斷證明書」，應為「入國通報受理證明書」
- doc_22（doc_22.png，roc_fw）FITRI RAHAYU 入國日：抽成 None，應為 2027-07-06
- doc_26（doc_26.png，roc_fw）SOMCHAI PHROMMA 入國日：抽成 2026-01-05，應為 2026-08-14
- doc_26 期限 apply_permit：輸出 (None, '2026-01-20')，應為 (None, '2026-08-31')
- doc_26 期限 health_entry：輸出 (None, '2026-01-08')，應為 (None, '2026-08-19')
- doc_26 期限 health_6m：輸出 ('2026-06-05', '2026-08-04')，應為 ('2027-01-15', '2027-03-16')
- doc_26 期限 health_18m：輸出 ('2027-06-05', '2027-08-04')，應為 ('2028-01-15', '2028-03-15')
- doc_26 期限 health_30m：輸出 ('2028-06-05', '2028-08-04')，應為 ('2029-01-15', '2029-03-16')
- doc_29：文件類型判成「None」，應為「入國通報受理證明書」
- doc_29（doc_29.png，roc）HOANG THI HOA 入國日：抽成 None，應為 2026-11-30
- doc_33：文件類型判成「入國通報受理證明書」，應為「聘僱許可函」
- doc_33（doc_33.png，iso）JOY ANN BAUTISTA 入國日：抽成 2020-09-21，應為 2026-08-14
- doc_33（doc_33.png，iso）JOY ANN BAUTISTA 許可起日：抽成 None，應為 2026-08-14
- doc_33（doc_33.png，iso）JOY ANN BAUTISTA 許可迄日：抽成 None，應為 2029-08-13
- doc_33（doc_33.png，iso）ANAN KAEWDEE 入國日：抽成 None，應為 2026-08-29
- doc_33（doc_33.png，iso）ANAN KAEWDEE 許可起日：抽成 None，應為 2026-08-29
- doc_33（doc_33.png，iso）ANAN KAEWDEE 許可迄日：抽成 None，應為 2029-08-28
- doc_33 期限 health_6m：輸出 ('2021-02-19', '2021-04-20')，應為 ('2027-01-15', '2027-03-16')
- doc_33 期限 health_18m：輸出 ('2022-02-19', '2022-04-20')，應為 ('2028-01-15', '2028-03-15')
- doc_33 期限 health_30m：輸出 ('2023-02-19', '2023-04-20')，應為 ('2029-01-15', '2029-03-16')
- doc_34：文件類型判成「聘僱許可函」，應為「聘僱關係終止」
- doc_34（doc_34.png，iso）SOMCHAI PHROMMA 許可起日：抽成 2026-10-02，應為 None
- doc_34（doc_34.png，iso）SOMCHAI PHROMMA 事件日：抽成 None，應為 2027-10-26
- doc_37（doc_37.png，roc）HOANG THI HOA 事件日：抽成 None，應為 2026-03-20
- doc_37（doc_37.png，roc）DEWI PURNAMA 事件日：抽成 None，應為 2026-03-20
- doc_39：文件類型判成「聘僱許可函」，應為「入國通報受理證明書」
- doc_39（doc_39.png，iso）SOMCHAI PHROMMA 入國日：抽成 None，應為 2027-08-06
- doc_39（doc_39.png，iso）SOMCHAI PHROMMA 許可起日：抽成 2027-08-06，應為 None
- doc_40：文件類型判成「聘僱許可函」，應為「住宿地點變更」
- doc_40（doc_40.png，roc_fw）WULAN HANDAYANI 許可起日：抽成 2021-11-07，應為 None
- doc_40（doc_40.png，roc_fw）WULAN HANDAYANI 許可迄日：抽成 2022-01-27，應為 None
- doc_40（doc_40.png，roc_fw）WULAN HANDAYANI 事件日：抽成 None，應為 2027-11-27
- doc_40（doc_40.png，roc_fw）MARK ANTHONY SORIANO 許可起日：抽成 2021-11-07，應為 None
- doc_40（doc_40.png，roc_fw）MARK ANTHONY SORIANO 許可迄日：抽成 2022-01-27，應為 None
- doc_40（doc_40.png，roc_fw）MARK ANTHONY SORIANO 事件日：抽成 None，應為 2027-11-27
- doc_40（doc_40.png，roc_fw）JOY ANN BAUTISTA 許可起日：抽成 2021-11-07，應為 None
- doc_40（doc_40.png，roc_fw）JOY ANN BAUTISTA 許可迄日：抽成 2022-01-27，應為 None
- doc_40（doc_40.png，roc_fw）JOY ANN BAUTISTA 事件日：抽成 None，應為 2027-11-27
- doc_44：文件類型判成「聘僱許可函」，應為「再檢查診斷證明書」
- doc_44（doc_44.png，roc）LE THI MAI 許可起日：抽成 2026-06-01，應為 None
- doc_44（doc_44.png，roc）LE THI MAI 許可迄日：抽成 2026-07-21，應為 None
- doc_44（doc_44.png，roc）LE THI MAI 事件日：抽成 None，應為 2026-07-12
- doc_49（doc_49.png，roc_cn）MARK ANTHONY SORIANO 入國日：抽成 None，應為 2026-07-09
- doc_49（doc_49.png，roc_cn）MARK ANTHONY SORIANO 許可起日：抽成 None，應為 2026-07-09
- doc_49（doc_49.png，roc_cn）MARK ANTHONY SORIANO 許可迄日：抽成 2024-08-03，應為 2029-07-08
- doc_49（doc_49.png，roc_cn）INDAH PURNAMA 入國日：抽成 None，應為 2026-07-15
- doc_49（doc_49.png，roc_cn）INDAH PURNAMA 許可起日：抽成 None，應為 2026-07-15
- doc_49（doc_49.png，roc_cn）INDAH PURNAMA 許可迄日：抽成 2023-09-06，應為 2029-07-14
- doc_49（doc_49.png，roc_cn）DO THI THU 入國日：抽成 None，應為 2026-07-20
- doc_49（doc_49.png，roc_cn）DO THI THU 許可起日：抽成 None，應為 2026-07-20
- doc_49（doc_49.png，roc_cn）DO THI THU 許可迄日：抽成 None，應為 2029-07-19
- doc_49 期限 renewal_window：輸出 ('2024-04-03', '2024-06-03')，應為 ('2029-03-08', '2029-05-08')
- doc_49 期限 permit_expiry：輸出 (None, '2024-08-03')，應為 (None, '2029-07-08')
- doc_49 期限 renewal_window：輸出 ('2023-05-06', '2023-07-06')，應為 ('2029-03-14', '2029-05-14')
- doc_49 期限 permit_expiry：輸出 (None, '2023-09-06')，應為 (None, '2029-07-14')

## extract_haiku_mask 分組明細

| 分組 | 文件類型 | 日期欄位 | 應辦期限 | 整份文件全對 |
|---|---|---|---|---|
| 全部 | 35/35（100.0%） | 68/68（100.0%） | 133/133（100.0%） | 35/35（100.0%） |
| 日期格式:iso | 3/3（100.0%） | 4/4（100.0%） | 11/11（100.0%） | 3/3（100.0%） |
| 日期格式:roc | 12/12（100.0%） | 23/23（100.0%） | 42/42（100.0%） | 12/12（100.0%） |
| 日期格式:roc_cn | 8/8（100.0%） | 15/15（100.0%） | 37/37（100.0%） | 8/8（100.0%） |
| 日期格式:roc_dot | 8/8（100.0%） | 17/17（100.0%） | 27/27（100.0%） | 8/8（100.0%） |
| 日期格式:roc_fw | 4/4（100.0%） | 9/9（100.0%） | 16/16（100.0%） | 4/4（100.0%） |
| 純文字 | 35/35（100.0%） | 68/68（100.0%） | 133/133（100.0%） | 35/35（100.0%） |
| 類型:住宿地點變更 | 3/3（100.0%） | 8/8（100.0%） | 8/8（100.0%） | 3/3（100.0%） |
| 類型:入國通報受理證明書 | 6/6（100.0%） | 6/6（100.0%） | 30/30（100.0%） | 6/6（100.0%） |
| 類型:再檢查診斷證明書 | 6/6（100.0%） | 6/6（100.0%） | 6/6（100.0%） | 6/6（100.0%） |
| 類型:期滿續聘許可函 | 6/6（100.0%） | 14/14（100.0%） | 35/35（100.0%） | 6/6（100.0%） |
| 類型:聘僱許可函 | 10/10（100.0%） | 30/30（100.0%） | 50/50（100.0%） | 10/10（100.0%） |
| 類型:聘僱關係終止 | 4/4（100.0%） | 4/4（100.0%） | 4/4（100.0%） | 4/4（100.0%） |

### 錯誤清單（0）


未跑：doc_09, doc_12, doc_13, doc_17, doc_20, doc_22, doc_26, doc_29, doc_33, doc_34, doc_37, doc_39, doc_40, doc_44, doc_49