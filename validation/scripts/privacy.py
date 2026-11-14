"""Mask personal data locally BEFORE any text is sent to an external LLM.

行政院〈行政院及所屬機關（構）使用生成式AI參考指引〉：不得向生成式 AI 提供個人資料。

Two kinds of handling:
- Pseudonymise (reversible): foreign worker names -> PERSON_01 ... The extractor needs a name
  to attach deadlines to a person, so the LLM sees a code and we swap the real name back
  locally after the LLM answers.
- Redact (irreversible): national ID / ARC numbers, passport numbers, company tax IDs,
  birth dates, addresses, phone numbers, and natural-person names after labels such as
  受處分人／代表人. The LLM never needs these; a placeholder keeps the fact that the field
  exists (so the penalty checker can still see "受處分人 has an ID number").

Limitation: only TEXT can be masked locally. Scanned images go to the model as pixels;
the demo warns about this, and a government deployment should use an on-premise model.
"""
from __future__ import annotations

import re
from typing import Any

ID_TOKEN = "〔身分證或居留證號已遮蔽〕"
PASSPORT_TOKEN = "〔護照號碼已遮蔽〕"
TAXID_TOKEN = "〔統一編號已遮蔽〕"
BIRTH_TOKEN = "〔出生日期已遮蔽〕"
ADDR_TOKEN = "〔地址已遮蔽〕"
PHONE_TOKEN = "〔電話已遮蔽〕"
NAME_TOKEN = "〔姓名已遮蔽〕"

# National ID (A123456789), new ARC (A800000000/A900000000), old ARC (AB12345678)
RE_ID = re.compile(r"(?<![A-Za-z0-9])[A-Z][12A-D89]\d{8}(?![0-9])")
RE_PASSPORT = re.compile(r"(護照(?:號碼|號)\s*[:：]?\s*)([A-Z0-9]{6,10})")
RE_TAXID = re.compile(r"(統一編號\s*[:：]?\s*)(\d{8})")
RE_BIRTH = re.compile(r"(出生(?:日期|年月日)\s*[:：]?\s*)([^\s　|，。,]+)")
RE_ADDR = re.compile(r"((?:雇主|原|新)?(?:住宿地點|地址|住居所)\s*[:：]\s*)([^\n　]+)")
RE_MOBILE = re.compile(r"(?<!\d)09\d{2}-?\d{3}-?\d{3}(?!\d)")
RE_LANDLINE = re.compile(r"(?<!\d)0\d{1,2}-\d{6,8}(?!\d)")
# Natural-person names after labels (companies are kept: not personal data)
RE_LABELED_PERSON = re.compile(r"((?:受處分人|代表人|負責人|甲方（雇主）|雇主名稱|雇主|受文者|正本)\s*[:：]\s*)([^\s　（(，。]{2,12})")
COMPANY_HINT = ("公司", "有限", "股份", "工業", "企業", "工廠", "行號", "社", "政府", "醫院", "機構", "協會", "（略）", "展示用")
# Foreign worker names on official documents are written in capitals: NGUYEN THI LAN
RE_LATIN_NAME = re.compile(r"(?<![A-Za-z_])[A-Z][A-Z'\-]+(?: [A-Z][A-Z'\-]+){1,4}(?![A-Za-z_])")
LATIN_STOPWORDS = {"PDF", "PNG", "JPG", "LINE", "API", "AI", "DEMO", "ARC", "ID"}


def _is_company(s: str) -> bool:
    return any(h in s for h in COMPANY_HINT)


def mask(text: str) -> tuple[str, dict[str, str]]:
    """Return (masked_text, mapping token->real name) for later restore()."""
    mapping: dict[str, str] = {}
    reverse: dict[str, str] = {}

    def pseudo(m: re.Match) -> str:
        name = m.group(0)
        if name in LATIN_STOPWORDS or all(w in LATIN_STOPWORDS for w in name.split()):
            return name
        if name not in reverse:
            tok = f"PERSON_{len(reverse) + 1:02d}"
            reverse[name] = tok
            mapping[tok] = name
        return reverse[name]

    t = text
    t = RE_PASSPORT.sub(lambda m: m.group(1) + PASSPORT_TOKEN, t)
    t = RE_TAXID.sub(lambda m: m.group(1) + TAXID_TOKEN, t)
    t = RE_BIRTH.sub(lambda m: m.group(1) + BIRTH_TOKEN, t)
    t = RE_ADDR.sub(lambda m: m.group(1) + (m.group(2) if m.group(2).strip() in ("（略）", "(略)") else ADDR_TOKEN), t)
    t = RE_ID.sub(ID_TOKEN, t)
    t = RE_MOBILE.sub(PHONE_TOKEN, t)
    t = RE_LANDLINE.sub(PHONE_TOKEN, t)
    t = RE_LABELED_PERSON.sub(lambda m: m.group(1) + (m.group(2) if _is_company(m.group(2)) else NAME_TOKEN), t)
    t = RE_LATIN_NAME.sub(pseudo, t)
    return t, mapping


def restore(obj: Any, mapping: dict[str, str]) -> Any:
    """Swap PERSON_xx codes back to real names inside an LLM result (str / list / dict)."""
    if not mapping:
        return obj
    if isinstance(obj, str):
        for tok, real in mapping.items():
            obj = obj.replace(tok, real)
        return obj
    if isinstance(obj, list):
        return [restore(x, mapping) for x in obj]
    if isinstance(obj, dict):
        return {k: restore(v, mapping) for k, v in obj.items()}
    return obj


PROMPT_NOTE = ("\n\n（隱私說明：文件已在送出前遮蔽個資。形如 PERSON_01 的代號代表一位外國人的姓名，"
               "輸出姓名時請照抄代號；「〔…已遮蔽〕」表示該欄位原本有資料、已被遮蔽，視為已填寫。）")
