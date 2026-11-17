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
