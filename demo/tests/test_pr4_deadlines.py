"""Independent deadline reconstruction and calendar-use boundaries."""
import json
from dataclasses import replace

from demo.server import config
import rules


def test_long_term_windows_do_not_need_office_calendar():
    worker = {'entry_date': '2026-03-05', 'permit_start': '2026-03-05', 'permit_end': '2029-03-04'}
    tasks = {t['key']: t for t in rules.compute_traced('聘僱許可函', worker)}
    for key in ('permit_expiry', 'renewal_window', 'health_30m'):
        assert tasks[key]['status'] == 'todo', (key, tasks[key])
        assert tasks[key]['due']
        assert tasks[key]['calc_trace']['calendar_examined'] == []


def test_all_250_deadlines_are_independently_rebuilt():
    from deadline_trace import rebuild
    count, uncovered = 0, []
    for folder in ('docs', 'docs_holiday'):
        docs = json.loads((config.ROOT / 'validation' / folder / 'ground_truth.json').read_text(encoding='utf-8'))
        for doc in docs:
            for worker in doc['workers']:
                obligations = rules.compute(doc['doc_type'], worker)
                traced = rules.compute_traced(doc['doc_type'], worker)
                for original, task in zip(obligations, traced, strict=True):
                    count += 1
                    independent = rebuild(doc['doc_type'], worker, original.key, rules.OFF_DAYS, rules.HOLIDAY_NOTES, rules.CAL_YEARS)
                    assert independent['due'].isoformat() == original.due
                    assert (independent['window_start'].isoformat() if independent['window_start'] else None) == original.start
                    assert task['calc_trace']['independent_verified'] is True
                    if task['status'] == 'needs_review':
                        uncovered.append((doc['doc_id'], original.key))
                        assert task['due'] is None
                    else:
                        assert task['due'] == original.due
    assert count == 250
    assert uncovered == [('doc_H12', 'termination_notice')]


def test_only_examined_days_require_calendar():
    safe = rules.compute_traced('住宿地點變更', {'event_date': '2025-12-28'})[0]
    assert safe['status'] == 'todo'  # Only the 2026 deadline is checked for a holiday.
    unsafe = rules.compute_traced('聘僱關係終止', {'event_date': '2027-12-28'})[0]
    assert unsafe['status'] == 'needs_review' and unsafe['due'] is None
    assert any(d.startswith('2028-') for d in unsafe['calc_trace']['calendar_examined'])


def test_trace_rejects_an_engine_disagreement(monkeypatch):
    original = rules.compute('住宿地點變更', {'event_date': '2026-11-13'})[0]
    monkeypatch.setattr(rules, 'compute', lambda *_: [replace(original, due='2026-11-23')])
    task = rules.compute_traced('住宿地點變更', {'event_date': '2026-11-13'})[0]
    assert task['status'] == 'needs_review' and task['due'] is None
    assert task['calc_trace']['independent_verified'] is False
    assert any('獨立重算' in reason for reason in task['calc_trace']['review_reasons'])
