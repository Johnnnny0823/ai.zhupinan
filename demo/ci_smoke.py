"""Synthetic browser smoke evidence on a real CI operating system.

Runs the documented seed/serve commands against an isolated temporary database.
Never prints login codes, cookies, model inputs, or real user data.
"""
import json
import locale
import os
import platform
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
ORIGIN = 'http://127.0.0.1:8765'


def main():
    from playwright.sync_api import sync_playwright, expect

    output = ROOT / 'artifacts' / 'pr4'
    output.mkdir(parents=True, exist_ok=True)
    report = {
        'platform': platform.platform(), 'python': platform.python_version(),
        'preferred_encoding': locale.getpreferredencoding(False),
        'pythonutf8_set': 'PYTHONUTF8' in os.environ,
        'utf8_mode': sys.flags.utf8_mode, 'synthetic': True,
        'model_mode': 'stored synthetic fixtures only', 'checks': [], 'layouts': [],
        'screenshots': [], 'browser_errors': [], 'http_5xx': [],
    }
    if report['pythonutf8_set']:
        raise RuntimeError('Browser smoke must run without PYTHONUTF8')

    with tempfile.TemporaryDirectory(prefix='zpa-pr4-smoke-') as temp:
        codes = {name: secrets.token_urlsafe(24) for name in ('A', 'B', 'OFFICER')}
        child_env = {
            **os.environ, 'DEMO_DATA': 'true', 'PUBLIC_ORIGIN': ORIGIN,
            'DEMO_DB_PATH': str(Path(temp) / 'demo.sqlite3'),
            'DEMO_TEMP_PATH': str(Path(temp) / 'uploads-temp'),
            **{'DEMO_LOGIN_' + key: value for key, value in codes.items()},
        }
        child_env.pop('PYTHONUTF8', None)
        subprocess.run([sys.executable, '-m', 'demo.run', 'seed'], cwd=ROOT, env=child_env, check=True)
        with (output / 'server.txt').open('w', encoding='utf-8') as log:
            server = subprocess.Popen(
                [sys.executable, '-m', 'demo.run', 'serve'], cwd=ROOT, env=child_env,
                stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 45
                while True:
                    if server.poll() is not None:
                        raise RuntimeError('Isolated demo server exited before readiness')
                    try:
                        if httpx.get(ORIGIN + '/api/health', timeout=2).status_code == 200:
                            break
                    except httpx.RequestError:
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError('Isolated demo server did not become ready')
                    time.sleep(0.2)

                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch()
                    context = browser.new_context(viewport={'width': 1280, 'height': 800}, locale='zh-TW')
                    page = context.new_page()
                    page.on('pageerror', lambda error: report['browser_errors'].append(str(error)))
                    page.on('response', lambda response: report['http_5xx'].append({'url': response.url, 'status': response.status}) if response.status >= 500 else None)
                    page.goto(ORIGIN)
                    page.get_by_label('一次性登入碼', exact=True).fill(codes['A'])
                    page.get_by_role('button', name='打開我的案件手帖 →', exact=True).click()
                    expect(page.get_by_role('heading', name='今天，先辦這幾件。', exact=True)).to_be_visible()
                    case = context.request.get(ORIGIN + '/api/cases/case-a')
                    assert case.status == 200
                    task_id = case.json()['tasks'][0]['id']
                    detail = context.request.get(ORIGIN + '/api/tasks/' + task_id)
                    assert detail.status == 200
                    report['checks'].append('login, case API, task-detail API return 200')

                    def capture(name, all_sizes=False):
                        for width, height in ([(320, 700), (390, 844), (1280, 800)] if all_sizes else [(1280, 800)]):
                            page.set_viewport_size({'width': width, 'height': height})
                            page.locator('h1').wait_for()
                            layout = page.evaluate('({width:innerWidth, documentWidth:document.documentElement.scrollWidth})')
                            assert layout['documentWidth'] <= layout['width'], (name, layout)
                            report['layouts'].append({'screen': name, **layout})
                            filename = f'{name}-{width}.png'
                            page.screenshot(path=str(output / filename), full_page=True, animations='disabled')
                            report['screenshots'].append(filename)

                    capture('employer-tasks')
                    page.get_by_role('button', name='再檢查證明送衛生主管機關備查', exact=True).click()
                    expect(page.get_by_role('heading', name='再檢查證明送衛生主管機關備查', exact=True)).to_be_visible()
                    capture('task-detail')
                    report['checks'].append('task detail visibly renders without 500')

                    page.locator('[data-page="documents"]').click()
                    page.get_by_label('讀取方式', exact=True).select_option('stored')
                    page.get_by_role('button', name='住宿變更 · 合成掃描範例 ↗', exact=True).click()
                    expect(page.get_by_role('heading', name='請把日期，逐一核對。', exact=True)).to_be_visible()
                    page.locator('#confirm-fields').check()
                    page.get_by_role('button', name='確認日期，新增待辦 →', exact=True).click()
                    expect(page.locator('.field-error')).to_have_count(2)
                    capture('unchecked-date-errors', all_sizes=True)
                    report['checks'].append('unchanged unchecked scan dates are refused and highlighted')

                    page.locator('#field-0-event_date').fill('2026-03-21')
                    expect(page.locator('#checked-0-event_date')).to_be_disabled()
                    page.locator('#checked-1-event_date').check()
                    page.locator('#confirm-fields').check()
                    capture('edited-and-checked-dates', all_sizes=True)
                    page.get_by_role('button', name='確認日期，新增待辦 →', exact=True).click()
                    expect(page.get_by_role('heading', name='今天，先辦這幾件。', exact=True)).to_be_visible()
                    case = context.request.get(ORIGIN + '/api/cases/case-a').json()
                    assert any(task['event_date'] == '2026-03-21' and task['due_date'] == '2026-03-30' for task in case['tasks'])
                    report['checks'].append('edited date needs no tick; other unchanged date is ticked; due recomputed')

                    page.get_by_role('button', name='登出 ↗', exact=True).click()
                    page.get_by_label('示範帳號', exact=True).select_option('officer')
                    page.get_by_label('一次性登入碼', exact=True).fill(codes['OFFICER'])
                    page.get_by_role('button', name='打開我的案件手帖 →', exact=True).click()
                    page.get_by_role('button', name='載入合成裁處書草稿', exact=True).click()
                    page.get_by_label('檢核方式', exact=True).select_option('stored')
                    page.get_by_role('button', name='開始七項輔助檢核 →', exact=True).click()
                    expect(page.locator('.checklist > li')).to_have_count(7)
                    expect(page.get_by_text('預存示範結果 · 耗時', exact=False)).to_be_visible()
                    capture('officer-stored-penalty', all_sizes=True)
                    report['checks'].append('officer stored penalty visibly renders seven checks')
                    assert not report['browser_errors'], report['browser_errors']
                    assert not report['http_5xx'], report['http_5xx']
                    browser.close()
                    report['passed'] = True
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=10)
                (output / 'browser-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
