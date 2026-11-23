"""Read masked synthetic documents through Gemini CLI in an isolated profile."""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from threading import Lock

from . import llm

DEFAULT_MODEL = 'gemini-3.1-pro-preview'
PROFILE_LOCK = Lock()
CLI_SETTINGS = {
    'general': {'enableAutoUpdate': False},
    'context': {'fileName': 'ZHUPINAN_NO_CONTEXT.md'},
    'telemetry': {'enabled': False, 'logPrompts': False},
    'hooks': {'enabled': False},
    'tools': {'core': ['zhupinan_no_tools']},
}


def app_directory():
    if os.name == 'nt' and os.getenv('LOCALAPPDATA'):
        return Path(os.environ['LOCALAPPDATA']) / 'Zhupinan'
    return Path.home() / '.local' / 'share' / 'zhupinan'


def cli_command():
    node = shutil.which('node')
    local = app_directory() / 'gemini-cli' / 'node_modules' / '@google' / 'gemini-cli' / 'bundle' / 'gemini.js'
    if node and local.is_file():
        return [node, str(local)]
    executable = shutil.which('gemini')
    if executable:
        script = Path(executable).parent / 'node_modules' / '@google' / 'gemini-cli' / 'bundle' / 'gemini.js'
        if node and os.name == 'nt' and script.is_file():
            return [node, str(script)]
        return [executable]
    raise llm.LLMError('找不到 Gemini CLI，請先安裝並登入')


def clear_cli_history(profile):
    history = profile / '.gemini' / 'tmp'
    # Clear only runtime data in the dedicated application profile.
    expected_profile = profile.parent.resolve() / profile.name
    if profile.resolve() != expected_profile:
        raise OSError('Gemini application profile is redirected')
    if history.exists():
        if history.resolve() != expected_profile / '.gemini' / 'tmp':
            raise OSError('Gemini runtime directory is redirected')
        shutil.rmtree(history)


def call(system, document):
    model = os.getenv('DEMO_GEMINI_MODEL') or DEFAULT_MODEL
    if not re.fullmatch(r'gemini-[A-Za-z0-9.-]+', model):
        raise llm.LLMError('Gemini 模型名稱不符')
    try:
        command = cli_command()
        with PROFILE_LOCK, tempfile.TemporaryDirectory(prefix='zhupinan-gemini-') as workspace:
            profile = app_directory() / 'gemini-profile'
            profile.mkdir(parents=True, exist_ok=True)
            clear_cli_history(profile)
            system_file = Path(workspace) / 'system.md'
            system_file.write_text(system, encoding='utf-8')
            settings = Path(workspace) / '.gemini' / 'settings.json'
            settings.parent.mkdir()
            settings.write_text(json.dumps(CLI_SETTINGS), encoding='utf-8')
            policy = Path(workspace) / 'deny-tools.toml'
            policy.write_text('[[rule]]\ntoolName = "*"\ndecision = "deny"\npriority = 999\n', encoding='utf-8')
            env = dict(os.environ, GEMINI_CLI_HOME=str(profile),
                       GEMINI_SYSTEM_MD=str(system_file),
                       GEMINI_TELEMETRY_ENABLED='false', GEMINI_TELEMETRY_LOG_PROMPTS='false')
            try:
                result = subprocess.run(
                    [*command, '--model', model, '--output-format', 'json', '--skip-trust',
                     '--extensions', 'none', '--allowed-mcp-server-names', 'none',
                     '--admin-policy', policy.name,
                     '--prompt', 'Return only the extraction JSON described in the system instructions.'],
                    input=document, capture_output=True, text=True, encoding='utf-8',
                    timeout=55, cwd=workspace, env=env,
                )
            finally:
                clear_cli_history(profile)
        if result.returncode:
            raise llm.LLMError('Gemini CLI 登入或模型服務暫時不可用')
        envelope = llm.parse_json(result.stdout)
        response = envelope.get('response')
        if envelope.get('error') or not isinstance(response, str):
            raise llm.LLMError('Gemini CLI 回傳格式錯誤')
        return llm.parse_json(response)
    except (OSError, UnicodeError, subprocess.TimeoutExpired):
        raise llm.LLMError('Gemini CLI 暫時無法完成交叉比對') from None


DATE_FIELDS = ('entry_date', 'permit_start', 'permit_end', 'event_date', 'notify_date')


def signature(kind, workers):
    if not isinstance(workers, list) or not workers or any(not isinstance(worker, dict) for worker in workers):
        return None
    if any(worker.get(field) is not None and not isinstance(worker[field], str) for worker in workers for field in DATE_FIELDS):
        return None
    return kind, sorted(tuple(worker.get(field) or '' for field in DATE_FIELDS) for worker in workers)
