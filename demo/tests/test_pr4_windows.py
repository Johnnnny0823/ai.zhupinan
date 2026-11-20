"""Windows regressions from the 2026-11-17 integration work package."""
import os
import subprocess
import sys
from datetime import date
from importlib.metadata import version

from demo.server import config


def test_today_without_system_iana_database():
    """Windows has no system TZPATH; the installed tzdata must supply Taipei."""
    env = {**os.environ, 'PYTHONTZPATH': ''}
    env.pop('PYTHONUTF8', None)
    result = subprocess.run(
        [sys.executable, '-c', 'from demo.server.config import today; print(today().isoformat())'],
        env=env, capture_output=True, text=True, encoding='utf-8',
    )
    assert result.returncode == 0, result.stderr
    assert isinstance(date.fromisoformat(result.stdout.strip()), date)
    assert isinstance(config.today(), date)


def test_reviewed_tzdata_version_is_installed():
    assert version('tzdata') == '2026.6'


import json
from pathlib import Path
import pytest


@pytest.mark.parametrize('checkout_newline,request_newline', [
    ('\r\n', '\n'), ('\n', '\r\n'), ('\r\n', '\r\n'), ('\n', '\n'),
])
def test_stored_penalty_ignores_only_line_ending(clients, tmp_path, monkeypatch, checkout_newline, request_newline):
    root = config.ROOT
    original = (root / 'validation/penalty/p01.txt').read_text(encoding='utf-8')
    target = tmp_path / 'reference'
    drafts = target / 'validation/penalty'
    saved = target / 'validation/runs/penalty/haiku'
    drafts.mkdir(parents=True)
    saved.mkdir(parents=True)
    (drafts / 'p01.txt').write_bytes(original.replace('\n', checkout_newline).encode('utf-8'))
    (saved / 'p01.json').write_bytes((root / 'validation/runs/penalty/haiku/p01.json').read_bytes())
    monkeypatch.setattr(config, 'ROOT', target)
    client = clients['officer']
    result = client.post('/api/penalty/check', json={
        'text': original.replace('\n', request_newline), 'mode': 'stored',
    })
    assert result.status_code == 200, result.text
    assert len(result.json()['items']) == 7
    changed = client.post('/api/penalty/check', json={'text': original + ' altered', 'mode': 'stored'})
    assert changed.status_code == 422


def test_all_demo_text_reads_choose_encoding():
    """Default Windows encodings must not control source/fixture interpretation."""
    import ast
    missing = []
    for path in (config.ROOT / 'demo').rglob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'read_text':
                if not node.args and not any(k.arg == 'encoding' for k in node.keywords):
                    missing.append(f'{path.relative_to(config.ROOT)}:{node.lineno}')
    assert not missing, missing


def test_baseline_with_windows_cp950_default(monkeypatch, capsys):
    import io
    from demo import verify_baseline
    original = io.open

    def windows_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
        return original(file, mode, buffering, encoding if 'b' in mode or encoding not in (None, 'locale') else 'cp950', errors, newline, closefd, opener)

    monkeypatch.setattr(io, 'open', windows_open)
    verify_baseline.main()
    assert json.loads(capsys.readouterr().out)['legacy_holiday']['passed'] == 33
