"""Optional second read for the masked synthetic document text."""
import os

import httpx

from . import llm

DEFAULT_MODEL = 'gemini-3.1-pro-preview'


def call(system, document):
    token = os.getenv('GEMINI_API_KEY')
    if not token:
        raise llm.LLMError('Gemini 尚未設定金鑰')
    model = os.getenv('DEMO_GEMINI_MODEL') or DEFAULT_MODEL
    if not model.startswith('gemini-') or not all(ch.isascii() and (ch.isalnum() or ch in '-.') for ch in model):
        raise llm.LLMError('Gemini 模型名稱不符')
    try:
        response = httpx.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
            headers={'x-goog-api-key': token},
            json={
                'systemInstruction': {'parts': [{'text': system}]},
                'contents': [{'role': 'user', 'parts': [{'text': document}]}],
                'generationConfig': {'responseMimeType': 'application/json'},
            },
            timeout=35,
        )
        response.raise_for_status()
        content = response.json()['candidates'][0]['content']['parts']
        return llm.parse_json(''.join(part['text'] for part in content if 'text' in part and not part.get('thought')))
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        raise llm.LLMError('Gemini 暫時無法完成交叉比對') from None


DATE_FIELDS = ('entry_date', 'permit_start', 'permit_end', 'event_date', 'notify_date')


def signature(kind, workers):
    if not isinstance(workers, list) or not workers or any(not isinstance(worker, dict) for worker in workers):
        return None
    if any(worker.get(field) is not None and not isinstance(worker[field], str) for worker in workers for field in DATE_FIELDS):
        return None
    return kind, sorted(tuple(worker.get(field) or '' for field in DATE_FIELDS) for worker in workers)
