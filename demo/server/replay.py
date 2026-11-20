"""開場案例重播：用現行規則引擎重算一件公開訴願案的期限，示範「如果當時有竹聘安」。

輸入只有公開訴願決定可推得的日期（不含任何人名、證號或地址），
期限由 rules.compute_traced 計算，提醒時點與準時判讀沿用系統現行邏輯。
"""
from datetime import date, timedelta
from .domain import compute_traced, proof_verdict
from .notifications import REMINDER_DAYS, TITLE

SOURCE = {
    'title': '勞動部勞動法訴二字第1140017128號訴願決定',
    'authority': '原處分機關：新竹市政府',
    'law': '就業服務法第57條第5款、第67條',
    'note': '依公開訴願決定所載日期重建；不含當事人資料，非原案文件。',
}
# 聘僱許可生效日：訴願決定所載「生效滿18個月為114/4/8」往回推算。
PERMIT_START = '2023-10-08'
PERMIT_END = '2026-10-07'
ACTUAL_DONE = '2025-05-27'
FINE = 60000


def roc(iso):
    d = date.fromisoformat(iso)
    return f'{d.year - 1911}/{d.month}/{d.day}'


def build():
    worker = {'name': '合成重演', 'permit_start': PERMIT_START, 'permit_end': PERMIT_END}
    task = next(o for o in compute_traced('聘僱許可函', worker) if o['key'] == 'health_18m')
    due = date.fromisoformat(task['due'])
    reminders = [{'date': (due - timedelta(days=n)).isoformat(), 'roc': roc((due - timedelta(days=n)).isoformat()),
                  'days_left': n, 'text': f"【竹聘安】安排定期健康檢查\n期限：{roc(task['due'])}" + ('（今天到期）' if n == 0 else f'（剩 {n} 天）')}
                 for n in REMINDER_DAYS]
    verdict = proof_verdict(task['start'], task['due'], ACTUAL_DONE)
    late_days = (date.fromisoformat(ACTUAL_DONE) - due).days
    return {
        'source': SOURCE,
        'permit_start': {'date': PERMIT_START, 'roc': roc(PERMIT_START)},
        'task': {
            'title': task['title'], 'start': task['start'], 'due': task['due'],
            'start_roc': roc(task['start']), 'due_roc': roc(task['due']),
            'basis': task['basis'], 'steps': task['calc_trace']['steps'], 'status': task['status'],
            'rules_version': task['calc_trace']['rules_version'],
        },
        'reminders': reminders,
        'actual': {'date': ACTUAL_DONE, 'roc': roc(ACTUAL_DONE), 'verdict': verdict, 'late_days': late_days, 'fine': FINE},
        'synthetic': True,
    }
