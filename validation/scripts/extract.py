"""Run the LLM over synthetic docs via the local Claude CLI (subscription auth).

Usage:
  python extract.py --model haiku --mode extract     # 竹聘安 pipeline: LLM extracts, rules compute
  python extract.py --model haiku --mode llm_only    # baseline: LLM computes deadlines itself
  python extract.py ... --only doc_01,doc_02          # subset
Results are cached in ../runs/<mode>_<model>/doc_XX.json (re-run skips done docs).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))   # sibling modules (privacy) under python -I

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / os.environ.get("DOCS_DIR", "docs")

DOC_TYPES = ["聘僱許可函", "期滿續聘許可函", "入國通報受理證明書", "再檢查診斷證明書", "住宿地點變更", "聘僱關係終止"]

EXTRACT_SYS = f"""你是「竹聘安 AI」的文件判讀模組。使用者是聘僱外籍移工的雇主，會上傳一份文件。
你的工作只有一件：從文件中抽取欄位，輸出 JSON。不要計算任何期限，不要解釋。

輸出格式（只輸出這個 JSON，不要加 markdown 程式碼框）：
{{"doc_type": "<{' | '.join(DOC_TYPES)}>",
 "workers": [{{"name": "<外國人姓名，照文件原樣>",
              "entry_date": "<入國日期 YYYY-MM-DD 或 null>",
              "permit_start": "<聘僱許可期間起日 YYYY-MM-DD 或 null>",
              "permit_end": "<聘僱許可期間迄日 YYYY-MM-DD 或 null>",
              "event_date": "<事件日 YYYY-MM-DD 或 null>"}}]}}

規則：
- 日期一律換算成西元 YYYY-MM-DD。民國年 + 1911 = 西元年。文件可能使用民國年、國字數字、全形數字或「115.03.02」格式。
- event_date 的意義依文件類型而定：
  再檢查診斷證明書 → 雇主「收受（收文）」該證明書的日期，不是檢查日或開立日；
  住宿地點變更 → 外國人遷入新住宿地點的日期（變更日），不是填表日或租約起租日；
  聘僱關係終止 → 聘僱關係終止日，不是簽約日或預定出國日；
  其他文件類型 → null。
- 不要把發文日期、通報日期、出生日期、護照效期、申請日當成上述欄位。
- 文件沒有的欄位填 null。名冊有幾位外國人就輸出幾筆 workers。"""

LLM_ONLY_SYS = """你是協助台灣雇主遵守外籍移工法規的助理。使用者會上傳一份文件。
請依中華民國現行法規（就業服務法、雇主聘僱外國人許可及管理辦法、受聘僱外國人健康檢查管理辦法、行政程序法期間計算），
列出這份文件觸發、雇主必須辦理的事項及期限。

只能使用下列 key（只列出適用者）：
apply_permit（申請聘僱許可）、health_entry（入國三日內健康檢查）、health_6m / health_18m / health_30m（定期健康檢查）、
renewal_window（申請期滿續聘或期滿轉換）、permit_expiry（聘僱許可屆滿日）、recheck_report（再檢查證明送衛生主管機關備查）、
dorm_change（通知住宿地點變更）、termination_notice（聘僱關係終止之書面通知）

輸出格式（只輸出 JSON，不要 markdown 程式碼框）：
{"obligations": [{"key": "...", "worker": "<外國人姓名>", "start": "<期間起日 YYYY-MM-DD 或 null>", "due": "<最後期限 YYYY-MM-DD>"}]}
期間型義務（定期健檢、期滿續聘）請填 start 與 due；單一期限只填 due、start 為 null。"""


def claude_bin() -> str:
    for c in ("claude.cmd", "claude"):
        p = shutil.which(c)
        if p:
            return p
    raise SystemExit("claude CLI not found")


def parse_json(text: str):
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else None


MASK = False   # set by --mask: personal data is masked locally before the LLM sees the text


def run_one(doc: dict, model: str, mode: str, out_dir: Path) -> str:
    out = out_dir / f"{doc['doc_id']}.json"
    if out.exists():
        return f"{doc['doc_id']} cached"
    sys_prompt = EXTRACT_SYS if mode == "extract" else LLM_ONLY_SYS
    mapping = {}
    if MASK:
        from privacy import PROMPT_NOTE
        sys_prompt += PROMPT_NOTE
    path = DOCS / doc["file"]
    sp_file = ROOT / "runs" / f"_system_{mode}{'_mask' if MASK else ''}.txt"
    sp_file.write_text(sys_prompt, encoding="utf-8")
    cmd = [claude_bin(), "-p", "--model", model, "--system-prompt-file", str(sp_file),
           "--strict-mcp-config", "--no-session-persistence", "--output-format", "json"]
    if doc["is_image"]:
        cmd += ["--tools", "Read", "--allowedTools", "Read", "--add-dir", str(DOCS)]
        user = f"Use the Read tool to open this uploaded document image, then output only the JSON as instructed: {path}"
    else:
        cmd += ["--tools", ""]
        text = path.read_text(encoding="utf-8")
        if MASK:
            from privacy import mask
            text, mapping = mask(text)
        user = "以下是雇主上傳的文件內容：\n\n" + text
    t0 = time.time()
    p = subprocess.run(cmd, input=user, capture_output=True, text=True, encoding="utf-8", timeout=300,
                       cwd=str(ROOT))
    rec = {"doc_id": doc["doc_id"], "model": model, "mode": mode, "seconds": round(time.time() - t0, 1),
           "returncode": p.returncode, "parsed": None, "error": None, "raw": None, "usage": None}
    try:
        env = json.loads(p.stdout)
        rec["raw"] = env.get("result")
        rec["usage"] = {k: env.get(k) for k in ("total_cost_usd", "num_turns", "duration_ms")}
        if env.get("is_error"):
            rec["error"] = env.get("result")
        else:
            rec["parsed"] = parse_json(env.get("result") or "")
            if mapping:
                from privacy import restore
                rec["parsed"] = restore(rec["parsed"], mapping)
                rec["masked"] = True
    except Exception as e:  # noqa: BLE001
        rec["error"] = f"{type(e).__name__}: {e}; stdout={p.stdout[:300]!r}; stderr={p.stderr[:300]!r}"
    if rec["error"] and ("401" in rec["error"] or "authenticate" in rec["error"].lower() or "limit" in rec["error"].lower()):
        return f"{doc['doc_id']} FATAL {rec['error'][:200]}"  # do not cache auth/quota failures
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    return f"{doc['doc_id']} {'ERR ' + rec['error'][:120] if rec['error'] else 'ok'} {rec['seconds']}s"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--mode", choices=["extract", "llm_only"], default="extract")
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--mask", action="store_true", help="mask personal data before the LLM (text docs only)")
    a = ap.parse_args()
    global MASK
    MASK = a.mask
    truth = json.loads((DOCS / "ground_truth.json").read_text(encoding="utf-8"))
    if a.only:
        keep = set(a.only.split(","))
        truth = [d for d in truth if d["doc_id"] in keep]
    if a.mask:
        truth = [d for d in truth if not d["is_image"]]   # pixels cannot be masked locally
    out_dir = ROOT / "runs" / (f"{a.mode}_{a.model}" + ("_mask" if a.mask else "") + ("" if DOCS.name == "docs" else "_" + DOCS.name))
    out_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(a.workers) as ex:
        for msg in ex.map(lambda d: run_one(d, a.model, a.mode, out_dir), truth):
            print(msg, flush=True)
            if "FATAL" in msg:
                print("Stopping: auth or usage-limit problem.", flush=True)
                ex.shutdown(cancel_futures=True)
                break


if __name__ == "__main__":
    main()
