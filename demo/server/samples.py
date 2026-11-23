"""Fixed, public, synthetic examples. Stored results are never represented as live OCR."""
from . import config

SAMPLES = {
 'entry': {'label':'產業移工入國通報（合成）','kind':'入國通報受理證明書',
           'text':'【合成示範・非真實公文】\n入國通報受理證明書\n案件代號：DEMO-B01\n外國人姓名：DEMO WORKER\n入國日期：2026-11-13\n',
           'fields':[{'name':'移工代號01','entry_date':'2026-11-13','evidence':{'entry_date':'入國日期：2026-11-13'}}]},
 'dorm': {'label':'住宿地點變更（合成）','kind':'住宿地點變更',
          'text':'【合成示範・非真實公文】\n住宿地點變更\n案件代號：DEMO-B01\n變更日：2026-11-13\n',
          'fields':[{'name':'移工代號01','event_date':'2026-11-13','evidence':{'event_date':'變更日：2026-11-13'}}]},
 'recheck': {'label':'再檢查證明收受（合成）','kind':'再檢查診斷證明書',
             'text':'【合成示範・非真實公文】\n再檢查診斷證明書\n案件代號：DEMO-A01\n收文日期：2026-11-10\n',
             'fields':[{'name':'移工代號01','event_date':'2026-11-10','evidence':{'event_date':'收文日期：2026-11-10'}}]},
}
SCAN_SAMPLES = {
 '住宿地點變更_掃描.png': {'kind':'住宿地點變更','fields':[{'name':'移工代號01','event_date':'2026-03-20','evidence':{'event_date':'外國人遷入新住宿地點日期（變更日）：115年3月20日'}},{'name':'移工代號02','event_date':'2026-03-20','evidence':{'event_date':'外國人遷入新住宿地點日期（變更日）：115年3月20日'}}]},
 '聘僱許可函_掃描.png': {'kind':'聘僱許可函','fields':[{'name':'移工代號01','entry_date':'2027-01-20','permit_start':'2027-01-20','permit_end':'2030-01-19','evidence':{'entry_date':'入國日期：116年1月20日','permit_start':'自116年1月20日起','permit_end':'至119年1月19日止'}}]},
}

# The approved PDF contains the same synthetic scan and has its own file digest.
SCAN_SAMPLES['住宿地點變更_合成掃描.pdf'] = SCAN_SAMPLES['住宿地點變更_掃描.png']


def penalty_sample():
    return (config.ROOT/'validation'/'penalty'/'p01.txt').read_text(encoding='utf-8')
