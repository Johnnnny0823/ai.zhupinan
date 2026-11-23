"""Claude CLI without content caches or persistent sessions. Prompt files always cleaned."""
from __future__ import annotations
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from . import config

class LLMError(RuntimeError):
    def __init__(self,message):
        import logging
        logging.getLogger('zhupinan').warning('model_unavailable')
        super().__init__(message)

def call(system: str, user: str, model='haiku', timeout=90):
    if model == 'sonnet':
        model = config.CLAUDE_MODEL
    exe = shutil.which('claude.cmd') or shutil.which('claude')
    if not exe:
        raise LLMError('找不到 Claude CLI。請安裝並登入，或明確切換「預存示範結果」。')
    config.TEMP_PATH.mkdir(parents=True,exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=config.TEMP_PATH,prefix='llm-') as temp:
            system_file=Path(temp)/'system.txt'
            system_file.write_text(system,encoding='utf-8')
            cmd=[exe,'-p','--model',model,'--system-prompt-file',str(system_file),'--strict-mcp-config',
                 '--no-session-persistence','--output-format','json']
            cmd += ['--tools','']
            p=subprocess.run(cmd,input=user,capture_output=True,text=True,encoding='utf-8',timeout=timeout,cwd=temp)
            try: env=json.loads(p.stdout)
            except (ValueError,TypeError): raise LLMError('模型回覆無法讀取，請重試或切換預存示範結果') from None
            if p.returncode or env.get('is_error'):
                raise LLMError('模型服務不可用或登入已失效。請執行 claude auth login，或切換預存示範結果。')
            return env.get('result') or ''
    except subprocess.TimeoutExpired:
        raise LLMError('模型回應逾時，請重試或切換預存示範結果') from None
    except OSError:
        raise LLMError('模型程序無法啟動，請檢查 CLI 安裝') from None

def parse_json(text):
    text=re.sub(r'^```(?:json)?|```$','',text.strip(),flags=re.M).strip()
    try:
        data=json.loads(text)
        if not isinstance(data,dict): raise ValueError()
        return data
    except ValueError:
        raise LLMError('模型回傳格式錯誤，請核對後重試') from None
