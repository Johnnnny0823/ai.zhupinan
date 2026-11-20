"""Reconstruct deadlines independently of rules.compute and its date helpers.

The calendar data is shared; arithmetic and the list of dates actually examined
are separate so disagreement cannot silently become a displayed deadline.
"""
from calendar import monthrange
from datetime import date, timedelta

DAY_LIMITS = {
    'apply_permit': 15,
    'recheck_report': 15,
    'dorm_change': 7,
    'termination_notice': 3,
    'abscond_notice': 3,
}


def _months(value, amount):
    total = value.year * 12 + value.month - 1 + amount
    year, month_index = divmod(total, 12)
    month = month_index + 1
    return date(year, month, min(value.day, monthrange(year, month)[1]))


def rebuild(kind, worker, key, off_days, holiday_notes, calendar_years):
    examined = []
    skipped = []
    steps = []
    window_start = None
    counting_start = None

    def off(value):
        examined.append(value)
        if str(value.year) in calendar_years:
            return value.isoformat() in off_days
        # Used only for comparison to the legacy engine; never trusted/displayed.
        return value.weekday() in (5, 6)

    def skip(value):
        reason = holiday_notes.get(value.isoformat())
        if not reason:
            reason = '星期六' if value.weekday() == 5 else '星期日' if value.weekday() == 6 else '休息日'
        skipped.append({'date': value.isoformat(), 'reason': reason})

    def roll(value):
        current = value
        while off(current):
            skip(current)
            current += timedelta(days=1)
        return current

    if key in DAY_LIMITS:
        event = date.fromisoformat(worker['entry_date'] if key == 'apply_permit' else worker['event_date'])
        counting_start = event + timedelta(days=1)
        raw = event + timedelta(days=DAY_LIMITS[key])
        due = roll(raw)
        rule = f'始日不計，事件日加{DAY_LIMITS[key]}日；末日依行政程序法第48條第4項順延'
        steps = [f'事件日：{event.isoformat()}', f'翌日起算：{counting_start.isoformat()}', f'原到期日：{raw.isoformat()}']
    elif key == 'health_entry':
        event = date.fromisoformat(worker['entry_date'])
        counting_start = event + timedelta(days=1)
        current, counted = event, 0
        while counted < 3:
            current += timedelta(days=1)
            if off(current):
                skip(current)
            else:
                counted += 1
                steps.append(f'第{counted}個工作日：{current.isoformat()}')
        raw = due = current
        rule = '入國翌日起，依政府辦公日曆累計3個工作日；休息日不計'
    elif key in ('health_6m', 'health_18m', 'health_30m'):
        if kind in ('入國通報受理證明書', '家事移工預定入國'):
            anchor = worker['entry_date']
        elif kind == '聘僱許可函':
            anchor = worker.get('entry_date') or worker['permit_start']
        else:
            anchor = worker['permit_start']
        event = date.fromisoformat(anchor)
        months = int(key[7:-1])
        midpoint = _months(event, months)
        window_start = midpoint - timedelta(days=30)
        raw = due = midpoint + timedelta(days=30)
        rule = f'起算日滿{months}個月之日前後30日（健檢期間；不作末日順延）'
        steps = [f'起算日：{event.isoformat()}', f'滿{months}個月：{midpoint.isoformat()}', f'辦理期間：{window_start.isoformat()}～{due.isoformat()}']
    elif key in ('renewal_window', 'permit_expiry'):
        event = date.fromisoformat(worker['permit_end'])
        if key == 'renewal_window':
            window_start = _months(event, -4)
            raw = due = _months(event, -2)
            rule = '許可屆滿日前4個月至2個月（不作末日順延）'
            steps = [f'許可屆滿日：{event.isoformat()}', f'申請期間：{window_start.isoformat()}～{due.isoformat()}']
        else:
            raw = due = event
            rule = '公文載明的許可屆滿日期（不作末日順延）'
            steps = [f'許可屆滿日：{due.isoformat()}']
    elif key == 'onestop_register':
        event = date.fromisoformat(worker['entry_date'])
        raw = due = event - timedelta(days=5)
        rule = '預定入國日減5日；一站式作業規定，線上系統不作假日順延'
        steps = [f'預定入國日：{event.isoformat()}', f'減5日：{due.isoformat()}']
    elif key == 'replacement_window':
        event = date.fromisoformat(worker['event_date'])
        notified = date.fromisoformat(worker['notify_date']) if worker.get('notify_date') else roll(event + timedelta(days=3))
        home_care = '看護' in (worker.get('job') or '')
        window_start = _months(notified, 1 if home_care else 3)
        base = _months(event, 1) if home_care else window_start
        raw = _months(base, 6) - timedelta(days=1)
        due = roll(raw)
        rule = '通報滿1個月' if home_care else '通報滿3個月'
        rule += '後核對遞補申請期間；末日依行政程序法第48條順延'
        steps = [f'通報日：{notified.isoformat()}', f'可申請日：{window_start.isoformat()}', f'原到期日：{raw.isoformat()}']
    else:
        raise ValueError('沒有此項目的獨立驗算規則')

    return {
        'event': event,
        'counting_start': counting_start or event,
        'raw_due': raw,
        'due': due,
        'window_start': window_start,
        'examined': examined,
        'skipped': skipped,
        'steps': steps,
        'rule': rule,
    }
