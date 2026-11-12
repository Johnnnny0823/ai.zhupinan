"""竹聘安 AI demo server.

Run:  python -m uvicorn app:app --port 8765     (from demo/server)
Uses the same validated modules as ../../validation/scripts (rules, retrieval, checker).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import date
from pathlib import Path

import httpx
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
VALID = HERE.parent.parent / "validation" / "scripts"
sys.path.insert(0, str(VALID))

import llm  # noqa: E402
import penalty as pen_mod  # noqa: E402
import qa as qa_mod  # noqa: E402
from extract import EXTRACT_SYS  # noqa: E402
from rules import CAL_YEARS, compute  # noqa: E402

WEB = HERE.parent / "web"
DATA = HERE / "data"
DATA.mkdir(exist_ok=True)
UPLOADS = HERE / "uploads"
UPLOADS.mkdir(exist_ok=True)

app = FastAPI(title="竹聘安 AI demo")

# ---------------------------------------------------------------- extraction
DEMO_EXTRACT_SYS = EXTRACT_SYS + """

另外，請在每位 worker 物件中加入 "evidence" 欄位：{"entry_date": "<該日期在文件中的原文片段>", ...}，
只列出非 null 的欄位，原文片段照抄文件（例如「一一五年三月十日」），不要改寫。"""


@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    suffix = Path(file.filename or "upload").suffix.lower()
    raw = await file.read()
    if len(raw) > 15 * 1024 * 1024:
        raise HTTPException(413, "檔案太大（上限 15MB）")
    fid = uuid.uuid4().hex[:10]
    path = UPLOADS / f"{fid}{suffix}"
    path.write_bytes(raw)
    image = None
    text_doc = None
    if suffix in (".png", ".jpg", ".jpeg", ".webp"):
        image = path
    elif suffix == ".pdf":
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        page_text = "\n".join(p.get_text() for p in doc)
        if len(page_text.strip()) > 50:
            text_doc = page_text
        else:
            image = UPLOADS / f"{fid}.png"
            doc[0].get_pixmap(dpi=150).save(image)
    elif suffix in (".txt", ".md"):
        text_doc = raw.decode("utf-8", errors="replace")
    else:
        raise HTTPException(415, "請上傳圖片（JPG/PNG）、PDF 或文字檔")
    try:
        if image is not None:
            # validation: Haiku 0% on scans, Sonnet 78.6% -> images go to Sonnet
            out = llm.call(DEMO_EXTRACT_SYS, "請只輸出 JSON。", model="sonnet", image=image)
            model = "sonnet"
        else:
            out = llm.call(DEMO_EXTRACT_SYS, "以下是雇主上傳的文件內容：\n\n" + text_doc, model="haiku")
            model = "haiku"
        data = llm.parse_json(out)
    except llm.LLMError as e:
        raise HTTPException(502, str(e)) from e
    # flag fields that need human confirmation
    for w in data.get("workers", []):
        flags = {}
        for k, src in (w.get("evidence") or {}).items():
            if any(c in (src or "") for c in "〇一二三四五六七八九十"):
                flags[k] = "國字日期，請再確認"
        if image is not None:
            for k in ("entry_date", "permit_start", "permit_end", "event_date"):
                if w.get(k) and k not in flags:
                    flags[k] = "掃描文件，請核對原件"
        w["flags"] = flags
    return {"file_id": fid, "filename": file.filename, "is_image": image is not None, "model": model, **data}


# ---------------------------------------------------------------- obligations
class Confirmed(BaseModel):
    doc_type: str
    workers: list[dict]
    save: bool = True


@app.post("/api/obligations")
def obligations(body: Confirmed):
    items = []
    for w in body.workers:
        for o in compute(body.doc_type, w):
            d = o.to_dict()
            d["days_left"] = (date.fromisoformat(d["due"]) - date.today()).days
            items.append(d)
    items.sort(key=lambda x: x["start"] or x["due"])
    added = len(items)
    if body.save:
        state = load_state()
        seen = {_okey(o) for d in state["docs"] for o in d["obligations"]}
        new = [o for o in items if _okey(o) not in seen]
        added = len(new)
        if new:
            state["docs"].append({"doc_type": body.doc_type, "workers": body.workers, "obligations": new})
            save_state(state)
    return {"obligations": items, "added": added, "calendar_years": sorted(CAL_YEARS)}


def _okey(o):
    """Same worker + same task + same deadline = same to-do (prevents duplicates)."""
    return (o["worker"].strip().upper(), o["key"], o.get("start"), o["due"])


def load_state():
    f = DATA / "state.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"docs": []}


def save_state(s):
    (DATA / "state.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


@app.get("/api/todos")
def todos():
    state = load_state()
    items, seen = [], set()
    for d in state["docs"]:
        for o in d["obligations"]:
            if _okey(o) not in seen:  # also cleans duplicates saved before this fix
                seen.add(_okey(o))
                items.append(o)
    for o in items:
        o["days_left"] = (date.fromisoformat(o["due"]) - date.today()).days
    items.sort(key=lambda x: x["due"])
    workers = sorted({o["worker"] for o in items})
    return {"workers": workers, "items": items}


@app.delete("/api/todos")
def clear_todos():
    save_state({"docs": []})
    return {"ok": True}


# ---------------------------------------------------------------- legal Q&A
_ARTS = qa_mod.load_articles()
_RETR = qa_mod.Retriever2(_ARTS)


class Ask(BaseModel):
    question: str


@app.post("/api/ask")
def ask(body: Ask):
    q = body.question.strip()
    if not q:
        raise HTTPException(400, "請輸入問題")
    hits = _RETR.top(q)
    ctx = "\n\n".join(f"【{h['law']} {h['no']}】\n{h['text']}" for h in hits)
    try:
        ans = llm.call(qa_mod.SYS_STRICT, f"參考條文：\n{ctx}\n\n問題：{q}", model="haiku")
    except llm.LLMError as e:
        raise HTTPException(502, str(e)) from e
    cited = [h for h in hits if h["no"].replace("第", "").replace("條", "") in ans or h["no"] in ans]
    return {"answer": ans, "citations": cited or hits[:2], "retrieved": hits}


# ---------------------------------------------------------------- penalty checker
pen_mod.REF_ARTS[0] = ("就業服務法", ["第 46 條", "第 56 條", "第 57 條", "第 63 條", "第 67 條", "第 68 條"], "N0090001.txt")
PEN_SYS = pen_mod.SYS + """
另外，對每個 ok 為 false 的項目，加入 "fix" 欄位，提供可直接貼入裁處書的建議文字（一至兩句）。
注意：「製造工作」屬就業服務法第46條第1項第10款之工作。"""


class Draft(BaseModel):
    text: str


@app.post("/api/check-penalty")
def check_penalty(body: Draft):
    if len(body.text.strip()) < 30:
        raise HTTPException(400, "請貼上完整的裁處書草稿")
    try:
        out = llm.call(PEN_SYS + "\n\n" + pen_mod.refs(), "請檢核以下裁處書草稿：\n\n" + body.text, model="haiku")
        data = llm.parse_json(out)
    except llm.LLMError as e:
        raise HTTPException(502, str(e)) from e
    items = [{"id": c, "name": pen_mod.CHECK_ZH[c], **(data.get(c) or {"ok": None, "reason": "未回傳"})} for c in pen_mod.CHECKS]
    return {"items": items}


# ---------------------------------------------------------------- LINE
LINE_ENV = HERE / "line.env"   # KEY=VALUE lines; written by the team, never committed or shared


def line_cfg() -> tuple[str, str]:
    """Read LINE credentials from env vars or line.env on every call (no restart needed)."""
    vals = {}
    if LINE_ENV.exists():
        for ln in LINE_ENV.read_text(encoding="utf-8-sig").splitlines():
            if "=" in ln and not ln.strip().startswith("#"):
                k, v = ln.split("=", 1)
                vals[k.strip()] = v.strip().strip('"')
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN") or vals.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    secret = os.environ.get("LINE_CHANNEL_SECRET") or vals.get("LINE_CHANNEL_SECRET", "")
    return token, secret


def line_api(path: str, payload: dict) -> tuple[int, str]:
    token, _ = line_cfg()
    r = httpx.post(f"https://api.line.me/v2/bot/message/{path}", timeout=15,
                   headers={"Authorization": f"Bearer {token}"}, json=payload)
    return r.status_code, r.text[:300]


def load_users() -> list[str]:
    f = DATA / "line_users.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


TEMPLATES = {
    "zh": "【竹聘安提醒】{status}\n{worker}：{title}\n期限：{when}\n依據：{basis}",
    "id": "[Pengingat Zhu Pin An] {status}\n{worker}: {title}\nBatas waktu: {when}\nDasar hukum: {basis}",
    "vi": "[Nhắc nhở Zhu Pin An] {status}\n{worker}: {title}\nHạn chót: {when}\nCăn cứ: {basis}",
}
STATUS = {
    "zh": ("已逾期 {n} 天，請儘速辦理", "還剩 {n} 天", "{n} 天後開始辦理"),
    "id": ("Terlambat {n} hari, segera urus", "Sisa {n} hari", "Mulai dalam {n} hari"),
    "vi": ("Đã quá hạn {n} ngày, vui lòng xử lý ngay", "Còn {n} ngày", "Bắt đầu sau {n} ngày"),
}


def reminder_text(o, lang="zh"):
    lang = lang if lang in TEMPLATES else "zh"
    when = f"{o['start']} ～ {o['due']}" if o.get("start") else o["due"]
    over, left, starts = STATUS[lang]
    start_left = (date.fromisoformat(o["start"]) - date.today()).days if o.get("start") else None
    if o["days_left"] < 0:
        status = over.format(n=-o["days_left"])
    elif start_left is not None and start_left > 0:
        status = starts.format(n=start_left)
    else:
        status = left.format(n=o["days_left"])
    title = TITLE_I18N.get(lang, {}).get(o["key"], o["title"])
    return TEMPLATES[lang].format(status=status, worker=o["worker"], title=title, when=when, basis=o["basis"])


# translation drafts (to be reviewed by native speakers before real use)
TITLE_I18N = {
    "id": {"apply_permit": "Ajukan izin kerja (聘僱許可)", "health_entry": "Pemeriksaan kesehatan dalam 3 hari kerja setelah tiba",
           "health_6m": "Pemeriksaan kesehatan berkala bulan ke-6", "health_18m": "Pemeriksaan kesehatan berkala bulan ke-18",
           "health_30m": "Pemeriksaan kesehatan berkala bulan ke-30", "renewal_window": "Ajukan perpanjangan atau pindah majikan",
           "permit_expiry": "Izin kerja berakhir", "recheck_report": "Laporkan hasil pemeriksaan ulang ke dinas kesehatan",
           "dorm_change": "Laporkan perubahan tempat tinggal", "termination_notice": "Laporkan pemutusan hubungan kerja"},
    "vi": {"apply_permit": "Nộp đơn xin giấy phép tuyển dụng (聘僱許可)", "health_entry": "Khám sức khỏe trong 3 ngày làm việc sau khi nhập cảnh",
           "health_6m": "Khám sức khỏe định kỳ tháng thứ 6", "health_18m": "Khám sức khỏe định kỳ tháng thứ 18",
           "health_30m": "Khám sức khỏe định kỳ tháng thứ 30", "renewal_window": "Nộp đơn gia hạn hoặc chuyển chủ khi hết hạn",
           "permit_expiry": "Giấy phép tuyển dụng hết hạn", "recheck_report": "Nộp kết quả khám lại cho cơ quan y tế",
           "dorm_change": "Thông báo thay đổi nơi ở", "termination_notice": "Thông báo chấm dứt quan hệ lao động"},
}


@app.get("/api/line/status")
def line_status():
    token, secret = line_cfg()
    return {"configured": bool(token and secret), "followers": len(load_users())}


class Push(BaseModel):
    days: int = 30
    lang: str = "zh"


def _due_items(days: int):
    out = []
    for o in todos()["items"]:
        start_left = (date.fromisoformat(o["start"]) - date.today()).days if o.get("start") else None
        in_range = o["days_left"] <= days or (start_left is not None and 0 <= start_left <= days)
        if in_range:
            out.append(o)
    return out


DIGEST_HEAD = {"zh": "【竹聘安提醒】近期待辦 {n} 項", "id": "[Pengingat Zhu Pin An] {n} tugas mendatang",
               "vi": "[Nhắc nhở Zhu Pin An] {n} việc sắp đến hạn"}
DIGEST_MORE = {"zh": "…另有 {n} 項，請到竹聘安網頁查看", "id": "…dan {n} tugas lainnya di situs Zhu Pin An",
               "vi": "…và {n} việc khác trên trang Zhu Pin An"}
SEP = "\n────────\n"


def digest(items, lang="zh", limit=8):
    """One LINE message listing all due items (instead of one message per item)."""
    lang = lang if lang in TEMPLATES else "zh"
    body = SEP.join(f"{i}. " + reminder_text(o, lang).split("\n", 1)[0].split("】")[-1].split("] ")[-1] + "\n"
                    + reminder_text(o, lang).split("\n", 1)[1] for i, o in enumerate(items[:limit], 1))
    text = DIGEST_HEAD[lang].format(n=len(items)) + SEP + body
    if len(items) > limit:
        text += SEP + DIGEST_MORE[lang].format(n=len(items) - limit)
    return text[:4900]  # LINE text limit is 5000 chars


@app.get("/api/line/preview")
def line_preview(days: int = 30, lang: str = "zh"):
    items = _due_items(days)
    return {"count": len(items), "text": digest(items, lang) if items else ""}


@app.post("/api/line/send")
def line_send(body: Push):
    items = _due_items(body.days)
    messages = [digest(items, body.lang)] if items else []
    if not messages:
        return {"sent": 0, "preview": [], "mode": "none", "note": "近期沒有需要提醒的事項"}
    token, secret = line_cfg()
    if not (token and secret):
        return {"sent": 0, "preview": messages, "mode": "preview", "note": "尚未設定 LINE Messaging API，僅顯示預覽"}
    users = load_users()
    if not users:
        return {"sent": 0, "preview": messages, "mode": "preview",
                "note": "還沒有人加入官方帳號好友（或 webhook 尚未設定好）。請先用手機加好友，再按一次。"}
    sent, errors = 0, []
    for uid in users:
        code, text = line_api("push", {"to": uid, "messages": [{"type": "text", "text": m} for m in messages]})
        if code == 200:
            sent += 1
        else:
            errors.append(f"{code} {text}")
    note = f"已推播給 {sent} 位好友（1 則訊息，含 {len(items)} 項待辦）" + (f"；失敗：{errors[0]}" if errors else "")
    return {"sent": sent, "preview": messages, "mode": "line", "note": note}


WELCOME = ("歡迎使用竹聘安 AI！\n我會在移工的法定期限（健檢、通報、續聘）快到時提醒您，每則提醒都附法條依據。\n\n"
           "傳「待辦」可查看近期待辦。\n（決賽展示版本・資料為合成測試資料）")


@app.post("/line/webhook")
async def line_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("x-line-signature", "")
    _, secret = line_cfg()
    expect = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    if not secret or not hmac.compare_digest(sig, expect):
        raise HTTPException(403, "bad signature")
    payload = json.loads(body)
    users = set(load_users())
    for ev in payload.get("events", []):
        uid = (ev.get("source") or {}).get("userId")
        if uid and ev.get("type") in ("follow", "message"):
            users.add(uid)
        token = ev.get("replyToken")
        if not token:
            continue
        if ev.get("type") == "follow":
            line_api("reply", {"replyToken": token, "messages": [{"type": "text", "text": WELCOME}]})
        elif ev.get("type") == "message" and (ev.get("message") or {}).get("type") == "text":
            text = ev["message"].get("text", "")
            if "待辦" in text or "提醒" in text:
                items = _due_items(90)
                msgs = [digest(items)] if items else ["目前 90 天內沒有待辦事項。"]
            else:
                msgs = ["您好！傳「待辦」可查看近期待辦；法規問題請到竹聘安網頁的「法規問答」查詢。"]
            line_api("reply", {"replyToken": token, "messages": [{"type": "text", "text": m} for m in msgs]})
    (DATA / "line_users.json").write_text(json.dumps(sorted(users)), encoding="utf-8")
    return {"ok": True}


# ---------------------------------------------------------------- static
@app.get("/api/health")
def health():
    return {"ok": True, "calendar_years": sorted(CAL_YEARS), "articles": len(_ARTS)}


if WEB.exists():
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    return JSONResponse({"detail": f"系統錯誤：{type(exc).__name__}"}, status_code=500)
