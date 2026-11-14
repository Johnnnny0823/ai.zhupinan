"""Deadline rule engine for 竹聘安 validation.

The LLM only extracts dates/fields from a document. Deadlines are computed here,
deterministically, from the law articles cited in each rule (texts in ../laws/).

Calendar: official DGPA government office calendar (../laws/calendar.json, 2026-2027).
Outside covered years, only weekends are treated as off days and a note is added.
Month arithmetic uses the "corresponding day" (clamped to month end).
"""
from __future__ import annotations

import calendar
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import date, timedelta


@dataclass
class Obligation:
    key: str          # stable id used for scoring
    worker: str       # worker name ("" for document-level)
    title: str        # human readable task
    start: str | None # ISO date; window start (None = no lower bound)
    due: str          # ISO date; last day
    basis: str        # legal basis
    note: str = ""

    def to_dict(self):
        return asdict(self)


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


_CAL = json.loads((Path(__file__).resolve().parent.parent / "laws" / "calendar.json").read_text(encoding="utf-8"))
OFF_DAYS = set(_CAL["off_days"])
CAL_YEARS = set(_CAL["years"])
HOLIDAY_NOTES = _CAL["notes"]


def is_off(d: date) -> bool:
    if str(d.year) in CAL_YEARS:
        return d.isoformat() in OFF_DAYS
    return d.weekday() >= 5


def roll_weekend(d: date) -> tuple[date, str]:
    """行政程序法第48條第4項: last day on Sunday/holiday/rest day -> next day;
    Saturday -> next Monday (morning). Repeats until a working day."""
    if not is_off(d):
        return d, ""
    orig = d
    while is_off(d):
        d += timedelta(days=1)
    why = HOLIDAY_NOTES.get(orig.isoformat()) or ("星期六" if orig.weekday() == 5 else "星期日" if orig.weekday() == 6 else "休息日")
    note = f"末日{orig.isoformat()}為{why}，依行政程序法第48條第4項順延至{d.isoformat()}"
    if str(orig.year) not in CAL_YEARS:
        note += "（該年度辦公日曆未納入，僅以週末判斷，請再確認）"
    return d, note


def days_after(d: date, n: int) -> tuple[date, str]:
    """始日不計算 (行政程序法第48條第2項), then roll off-days."""
    return roll_weekend(d + timedelta(days=n))


def working_days_after(d: date, n: int) -> date:
    cur, left = d, n
    while left:
        cur += timedelta(days=1)
        if not is_off(cur):
            left -= 1
    return cur


def _p(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def periodic_health_checks(anchor: date, worker: str, anchor_label: str) -> list[Obligation]:
    out = []
    for m in (6, 18, 30):
        mid = add_months(anchor, m)
        out.append(Obligation(
            key=f"health_{m}m", worker=worker,
            title=f"安排第{m}個月定期健康檢查",
            start=(mid - timedelta(days=30)).isoformat(),
            due=(mid + timedelta(days=30)).isoformat(),
            basis="受聘僱外國人健康檢查管理辦法第3條第4款、第6條第1項第2款；就業服務法第57條第5款",
            note=f"以{anchor_label}起算滿{m}個月之日（{mid.isoformat()}）前後30日",
        ))
    return out


def renewal_window(permit_end: date, worker: str) -> list[Obligation]:
    return [
        Obligation(
            key="renewal_window", worker=worker,
            title="申請期滿續聘或期滿轉換",
            start=add_months(permit_end, -4).isoformat(),
            due=add_months(permit_end, -2).isoformat(),
            basis="雇主聘僱外國人許可及管理辦法第39條、第40條",
            note="聘僱許可有效期間屆滿日前二個月至四個月內",
        ),
        Obligation(
            key="permit_expiry", worker=worker,
            title="聘僱許可屆滿（未續聘須於屆滿前辦理出國）",
            start=None, due=permit_end.isoformat(),
            basis="雇主聘僱外國人許可及管理辦法第69條第1項",
        ),
    ]


def abscond(w: dict, name: str, ev: date) -> list[Obligation]:
    """移工連續曠職三日失去聯繫。
    ev          = 連續曠職滿三日之日（雇主確認失聯日）
    notify_date = 實際書面通報日（選填；未填時以法定最後通報日推算遞補時程）
    job         = '家庭看護' or other
    permit_end  = 原聘僱許可迄日（選填，用於檢查是否不足六個月不予遞補）
    """
    out: list[Obligation] = []
    notice_due, n = days_after(ev, 3)
    out.append(Obligation(
        "abscond_notice", name, "書面通知當地主管機關、移民署及警察機關（並副知勞動部）", None, notice_due.isoformat(),
        "就業服務法第56條第1項；雇主聘僱外國人許可及管理辦法第68條第1項",
        "以連續曠職滿三日之日起算3日內。通知須屬實：不實通報移工得申訴，經查證屬實將撤銷廢止聘僱許可處分（就業服務法第56條第2項）。"
        + (n and "；" + n or "")))

    notified = _p(w.get("notify_date")) or notice_due
    home_care = "看護" in (w.get("job") or "")
    if home_care:
        start = add_months(notified, 1)            # 就服法58②2：通報滿一個月
        window_end_base = add_months(ev, 1)        # 管理辦法24②2：行蹤不明屆滿一個月之日起六個月內
        basis = "就業服務法第58條第2項第2款；雇主聘僱外國人許可及管理辦法第24條第2項第2款"
        rule = "家庭看護工於雇主處所行蹤不明：通報滿1個月未查獲可申請"
    else:
        start = add_months(notified, 3)            # 就服法58①：通報滿三個月
        window_end_base = start                    # 管理辦法24①：屆滿三個月之日起六個月內
        basis = "就業服務法第58條第1項；雇主聘僱外國人許可及管理辦法第24條第1項"
        rule = "通報滿3個月未查獲可申請"
    due, n2 = roll_weekend(add_months(window_end_base, 6) - timedelta(days=1))
    note = f"{rule}，6個月內提出，逾期不予許可" + ("" if w.get("notify_date") else "（未填實際通報日，以法定最後通報日推算）")
    pe = _p(w.get("permit_end"))
    if pe and add_months(start, 6) > pe:
        note += "。注意：原聘僱許可所餘期間可能不足6個月，依就業服務法第58條第3項不予遞補，請確認"
    if n2:
        note += "；" + n2
    out.append(Obligation("replacement_window", name, "申請遞補移工", start.isoformat(), due.isoformat(), basis, note))
    return out


ONESTOP_SRC = "勞動部《移工一站式服務問答集》113年7月"


def onestop_entry(name: str, entry: date) -> list[Obligation]:
    """家事移工（家庭看護工、家庭幫傭）自國外新聘入國：移工一站式服務（112-01-01 起）。
    最遲於預定入國日5日（含）前完成線上登錄，且聘僱許可須受理完成；
    例：入國日 112-01-01 → 最晚 111-12-27（入國日減5日）。
    這是勞動部作業規定（問答集），非法條；線上系統24小時可申請，故不依行政程序法第48條順延。"""
    reg_due = entry - timedelta(days=5)
    out = [Obligation(
        "onestop_register", name, "至移工一站式服務網登錄入國講習，並線上申請聘僱許可（須受理完成）",
        None, reg_due.isoformat(),
        f"{ONESTOP_SRC}雇主篇問題1、4、6；聘僱許可篇問題1（作業規定，非法條）",
        "以預定入國日減5日為最後期限。一併申辦居留許可、職災保險、全民健保、入國通報生活照顧檢查。"
        "逾期將自動取消講習申請，須延後入國日；改期亦須於原入國日5日前辦理，新入國日限5～30日內。"
        "適用：自國外新聘之家庭看護工／家庭幫傭（未持5年內入國講習完訓證明）；"
        "國內接續聘僱、期滿續聘、期滿轉換不適用。網址 https://fwots.wda.gov.tw/",
    ), Obligation(
        "health_entry", name, "安排入國三日內健康檢查", None,
        working_days_after(entry, 3).isoformat(),
        "受聘僱外國人健康檢查管理辦法第3條第3款",
        "入國後三個工作日內（依人事行政總處辦公日曆）；一站式講習完訓交接當日或隔日安排。"
        "因故未能依限完成者，得於延長三個工作日內補行辦理",
    )]
    out += periodic_health_checks(entry, name, "入國日")
    return out


def compute(doc_type: str, w: dict) -> list[Obligation]:
    """w: one worker record with ISO date strings (entry_date, permit_start,
    permit_end, event_date)."""
    name = w.get("name", "")
    entry, ps, pe, ev = (_p(w.get(k)) for k in ("entry_date", "permit_start", "permit_end", "event_date"))
    out: list[Obligation] = []

    if doc_type == "入國通報受理證明書" and entry:
        d, n = days_after(entry, 15)
        out.append(Obligation("apply_permit", name, "申請聘僱許可", None, d.isoformat(),
                              "雇主聘僱外國人許可及管理辦法第36條", n))
        out.append(Obligation("health_entry", name, "安排入國三日內健康檢查", None,
                              working_days_after(entry, 3).isoformat(),
                              "受聘僱外國人健康檢查管理辦法第3條第3款", "入國後三個工作日內（依人事行政總處辦公日曆）"))
        out += periodic_health_checks(entry, name, "入國日")

    elif doc_type == "聘僱許可函" and pe:
        anchor, label = (entry, "入國日") if entry else (ps, "聘僱許可生效日")
        if anchor:
            out += periodic_health_checks(anchor, name, label)
        out += renewal_window(pe, name)

    elif doc_type == "期滿續聘許可函" and pe:
        if ps:
            out += periodic_health_checks(ps, name, "聘僱許可生效日")
        out += renewal_window(pe, name)

    elif doc_type == "再檢查診斷證明書" and ev:
        d, n = days_after(ev, 15)
        out.append(Obligation("recheck_report", name, "再檢查證明送衛生主管機關備查", None, d.isoformat(),
                              "受聘僱外國人健康檢查管理辦法第9條第2項", ("收受次日起15日內。" + n).strip("。")))

    elif doc_type == "住宿地點變更" and ev:
        d, n = days_after(ev, 7)
        out.append(Obligation("dorm_change", name, "通知當地主管機關住宿地點變更", None, d.isoformat(),
                              "雇主聘僱外國人許可及管理辦法第33條第5項", n))

    elif doc_type == "家事移工預定入國" and entry:
        out += onestop_entry(name, entry)

    elif doc_type == "移工失聯" and ev:
        out += abscond(w, name, ev)

    elif doc_type == "聘僱關係終止" and ev:
        d, n = days_after(ev, 3)
        out.append(Obligation("termination_notice", name, "書面通知當地主管機關、移民署及警察機關", None, d.isoformat(),
                              "就業服務法第56條第1項", n))

    return out
