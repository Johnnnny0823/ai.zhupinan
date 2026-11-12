"""Generate 50 synthetic employer documents + ground truth.

Every document is marked as synthetic test data. Names, numbers and addresses
are fictional. Output: ../docs/doc_XX.(txt|png) and ../docs/ground_truth.json
"""
from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rules import compute, working_days_after  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
SEED = 115
WATERMARK = "【合成測試文件・非真實公文・僅供竹聘安 AI 驗證使用】"

rng = random.Random(SEED)

# ---------- date formatting ----------
CN = "〇一二三四五六七八九"
FW = str.maketrans("0123456789", "０１２３４５６７８９")


def cn_num(n: int) -> str:  # 3 -> 三, 12 -> 十二, 25 -> 二十五
    if n < 10:
        return CN[n]
    t, o = divmod(n, 10)
    return ("" if t == 1 else CN[t]) + "十" + ("" if o == 0 else CN[o])


def fmt(d: date, style: str) -> str:
    roc = d.year - 1911
    if style == "roc":
        return f"{roc}年{d.month}月{d.day}日"
    if style == "roc_cn":
        return "".join(CN[int(c)] for c in str(roc)) + f"年{cn_num(d.month)}月{cn_num(d.day)}日"
    if style == "roc_fw":
        return f"{roc}年{d.month}月{d.day}日".translate(FW)
    if style == "roc_dot":
        return f"{roc}.{d.month:02d}.{d.day:02d}"
    if style == "iso":
        return d.isoformat()
    raise ValueError(style)


STYLES = ["roc", "roc", "roc_cn", "roc_fw", "roc_dot", "iso"]

# ---------- holiday guard (calendar ignores national holidays) ----------
FIXED = {(1, 1), (2, 28), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7), (5, 1), (9, 28), (10, 10), (10, 25), (12, 25)}


def holiday_risky(d: date) -> bool:
    if (d.month, d.day) in FIXED or d.month in (1, 2):
        return True
    if d.month == 6 and 5 <= d.day <= 25:      # Dragon Boat range
        return True
    if (d.month == 9 and d.day >= 10) or (d.month == 10 and d.day <= 12):  # Mid-Autumn range
        return True
    return False


def span_ok(a: date, b: date) -> bool:
    d = a
    while d <= b:
        if holiday_risky(d):
            return False
        d += timedelta(days=1)
    return True


def rand_date(lo: date, hi: date) -> date:
    return lo + timedelta(days=rng.randint(0, (hi - lo).days))


def safe_event_date(span_days: int) -> date:
    while True:
        d = rand_date(date(2026, 3, 1), date(2027, 11, 30))
        if span_ok(d, d + timedelta(days=span_days + 3)):
            return d


# ---------- fictional entities ----------
ID_FIRST = ["Dewi", "Sri", "Rina", "Ayu", "Wulan", "Indah", "Fitri", "Yuni"]
ID_LAST = ["Lestari", "Rahayu", "Susanti", "Wahyuni", "Handayani", "Purnama"]
VN = ["NGUYEN THI LAN", "TRAN VAN HUNG", "LE THI MAI", "PHAM VAN DUC", "HOANG THI HOA", "VU VAN NAM", "DO THI THU"]
PH = ["MARIA CLARA REYES", "JOY ANN BAUTISTA", "ROSALIE DELA CRUZ", "MARK ANTHONY SORIANO"]
TH = ["SOMCHAI PHROMMA", "ANAN KAEWDEE"]
NAT = {"印尼": lambda: f"{rng.choice(ID_FIRST).upper()} {rng.choice(ID_LAST).upper()}",
       "越南": lambda: rng.choice(VN), "菲律賓": lambda: rng.choice(PH), "泰國": lambda: rng.choice(TH)}
HOME_EMP = ["陳○○", "林○○", "黃○○", "張○○", "李○○", "王○○", "吳○○", "劉○○"]
CO_EMP = ["風城精密工業股份有限公司", "竹塹電子材料股份有限公司", "香山金屬製品有限公司", "東門食品股份有限公司", "頭前溪塑膠股份有限公司"]
DIST = ["東區", "北區", "香山區"]
ROADS = ["中正路", "民族路", "經國路一段", "光復路一段", "中華路三段", "延平路二段", "建功一路", "西大路"]


def addr():
    return f"新竹市{rng.choice(DIST)}{rng.choice(ROADS)}{rng.randint(10, 499)}號{rng.choice(['', str(rng.randint(2, 12)) + '樓'])}"


def docno(prefix="勞動發事字第"):
    return f"{prefix}{rng.randint(1150000000, 1169999999)}號"


def passport():
    return f"{rng.choice('BCEP')}{rng.randint(1000000, 9999999)}"


def worker(nat=None, taken=None):
    nat = nat or rng.choice(list(NAT))
    name = NAT[nat]()
    while taken is not None and name in taken:
        nat = rng.choice(list(NAT))
        name = NAT[nat]()
    if taken is not None:
        taken.add(name)
    return {"name": name, "nat": nat, "passport": passport(),
            "birth": rand_date(date(1975, 1, 1), date(2002, 12, 31))}


# ---------- templates ----------
def t_permit(i, style, renewal=False):
    home = rng.random() < 0.5
    emp = rng.choice(HOME_EMP) if home else rng.choice(CO_EMP)
    job = "家庭看護工作" if home else "製造工作"
    n = 1 if home else rng.choice([1, 1, 2, 3])
    issue = rand_date(date(2026, 3, 1), date(2027, 11, 30))
    ws, rows, taken = [], [], set()
    for _ in range(n):
        w = worker(taken=taken)
        if renewal:
            ps = rand_date(issue + timedelta(days=20), issue + timedelta(days=90))
            entry = None
        else:
            entry = rand_date(issue - timedelta(days=40), issue - timedelta(days=10))
            ps = entry
        pe = date(ps.year + 3, ps.month, ps.day) - timedelta(days=1) if not (ps.month == 2 and ps.day == 29) else date(ps.year + 3, 2, 27)
        rec = {"name": w["name"], "entry_date": entry.isoformat() if entry else None,
               "permit_start": ps.isoformat(), "permit_end": pe.isoformat(), "event_date": None}
        ws.append(rec)
        rows.append((w, entry, ps, pe))
    title = "期滿續聘許可" if renewal else "聘僱許可"
    lines = [WATERMARK, "勞動部 函", f"地址：（略）", f"受文者：{emp}",
             f"發文日期：中華民國{fmt(issue, style if style.startswith('roc') else 'roc')}",
             f"發文字號：{docno()}", "速別：普通件", "附件：外國人名冊",
             "", f"主旨：核准貴雇主{title}外國人計{n}名從事{job}，"
             f"許可期間詳如名冊，請查照。", "說明：",
             f"一、依據貴雇主{fmt(issue - timedelta(days=rng.randint(15, 40)), style)}申請書辦理。"]
    if renewal:
        lines.append("二、本案係期滿續聘，免依規定辦理入國通報。")
    else:
        lines.append("二、請依規定安排外國人接受定期健康檢查，並依外國人生活照顧服務計畫書確實執行。")
    lines.append("三、外國人聘僱許可期間屆滿，未申請期滿續聘或期滿轉換者，應於期滿前辦理出國。")
    lines += ["", "外國人名冊："]
    for k, (w, entry, ps, pe) in enumerate(rows, 1):
        lines.append(f"（{k}）姓名：{w['name']}　國籍：{w['nat']}　護照號碼：{w['passport']}　"
                     f"出生日期：{fmt(w['birth'], 'iso' if style == 'iso' else 'roc_dot')}")
        if entry:
            lines.append(f"　　入國日期：{fmt(entry, style)}")
        lines.append(f"　　聘僱許可期間：自{fmt(ps, style)}起至{fmt(pe, style)}止")
        lines.append(f"　　護照效期：{fmt(rand_date(pe, pe + timedelta(days=900)), style)}")
    lines += ["", "正本：" + emp, "副本：新竹市政府", "部長　○○○"]
    return ("期滿續聘許可函" if renewal else "聘僱許可函"), ws, lines


def t_entry_cert(i, style):
    emp = rng.choice(HOME_EMP + CO_EMP)
    w = worker()
    entry = safe_event_date(20)
    notify = entry + timedelta(days=rng.randint(0, 3))
    issue = notify + timedelta(days=rng.randint(0, 2))
    lines = [WATERMARK, "新竹市政府", "受理雇主聘僱外國人入國通報證明書",
             f"證明書字號：{docno('府勞外字第')}", f"雇主名稱：{emp}", f"雇主地址：{addr()}",
             f"外國人姓名：{w['name']}", f"國籍：{w['nat']}", f"護照號碼：{w['passport']}",
             f"入國日期：{fmt(entry, style)}", f"通報日期：{fmt(notify, style)}",
             f"住宿地點：{addr()}", f"招募許可文號：{docno()}",
             "", "茲證明上開雇主已依雇主聘僱外國人許可及管理辦法第34條規定辦理入國通報。",
             "本證明書供雇主向勞動部申請聘僱許可使用。", "",
             f"中華民國{fmt(issue, 'roc')}"]
    return "入國通報受理證明書", [{"name": w["name"], "entry_date": entry.isoformat(),
                             "permit_start": None, "permit_end": None, "event_date": None}], lines


def t_recheck(i, style):
    emp = rng.choice(HOME_EMP + CO_EMP)
    w = worker()
    recv = safe_event_date(18)
    exam = recv - timedelta(days=rng.randint(20, 45))
    rechk = exam + timedelta(days=rng.randint(7, 15))
    issue = recv - timedelta(days=rng.randint(2, 6))
    lines = [WATERMARK, "○○醫院（衛生福利部指定醫院）", "受聘僱外國人再檢查診斷證明書",
             f"受檢者：{w['name']}　國籍：{w['nat']}　護照號碼：{w['passport']}",
             f"雇主：{emp}", f"原定期健康檢查日期：{fmt(exam, style)}",
             f"再檢查日期：{fmt(rechk, style)}", "檢查項目：胸部X光肺結核檢查",
             "診斷結果：再檢查結果正常，判定合格。", f"開立日期：{fmt(issue, style)}",
             "", f"〔雇主收文章〕收文日期：{fmt(recv, style)}　收文號：{rng.randint(100, 999)}"]
    return "再檢查診斷證明書", [{"name": w["name"], "entry_date": None, "permit_start": None,
                          "permit_end": None, "event_date": recv.isoformat()}], lines


def t_dorm(i, style):
    emp = rng.choice(CO_EMP)
    n = rng.choice([1, 2, 3])
    taken = set()
    ws_raw = [worker(taken=taken) for _ in range(n)]
    move = safe_event_date(10)
    fill = move + timedelta(days=rng.randint(0, 3))
    lease = move - timedelta(days=rng.randint(5, 30))
    lines = [WATERMARK, "外國人生活照顧服務計畫書　變更事項表（第五款：住宿地點及生活照顧服務人員）",
             f"雇主名稱：{emp}", f"填表日期：{fmt(fill, style)}", "",
             f"原住宿地點：{addr()}", f"新住宿地點：{addr()}",
             f"新宿舍租賃契約起租日：{fmt(lease, style)}",
             f"外國人遷入新住宿地點日期（變更日）：{fmt(move, style)}",
             f"生活照顧服務人員：{rng.choice(['張', '陳', '許', '彭'])}○○（不變）", "", "異動外國人："]
    for k, w in enumerate(ws_raw, 1):
        lines.append(f"（{k}）{w['name']}　{w['nat']}　護照號碼 {w['passport']}")
    ws = [{"name": w["name"], "entry_date": None, "permit_start": None, "permit_end": None,
           "event_date": move.isoformat()} for w in ws_raw]
    return "住宿地點變更", ws, lines


def t_term(i, style):
    emp = rng.choice(HOME_EMP + CO_EMP)
    w = worker()
    end = safe_event_date(6)
    sign = end - timedelta(days=rng.randint(3, 20))
    leave = end + timedelta(days=rng.randint(5, 20))
    lines = [WATERMARK, "外國人聘僱關係終止協議書", f"甲方（雇主）：{emp}",
             f"乙方（外國人）：{w['name']}　國籍：{w['nat']}　護照號碼：{w['passport']}", "",
             "甲乙雙方合意終止聘僱關係，約定如下：",
             f"一、聘僱關係終止日：{fmt(end, style)}。",
             f"二、乙方預定出國日期：{fmt(leave, style)}。",
             "三、甲方應依法給付乙方工資至終止日止，並協助辦理出國手續。",
             "四、乙方已確認本協議係出於自由意願。", "",
             f"簽約日期：{fmt(sign, style)}", "甲方簽章：____　乙方簽章：____"]
    return "聘僱關係終止", [{"name": w["name"], "entry_date": None, "permit_start": None,
                        "permit_end": None, "event_date": end.isoformat()}], lines


# ---------- rendering ----------
def render_png(lines: list[str], path: Path):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    font = ImageFont.truetype(r"C:\Windows\Fonts\msjh.ttc", 26)
    W, lh = 1400, 40
    img = Image.new("L", (W, 120 + lh * len(lines)), 250)
    dr = ImageDraw.Draw(img)
    for k, ln in enumerate(lines):
        dr.text((70, 60 + k * lh), ln, fill=rng.randint(15, 45), font=font)
    img = img.rotate(rng.uniform(-1.5, 1.5), expand=True, fillcolor=250, resample=Image.BICUBIC)
    px = img.load()
    for _ in range(img.size[0] * img.size[1] // 300):
        x, y = rng.randrange(img.size[0]), rng.randrange(img.size[1])
        px[x, y] = rng.choice([90, 200])
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    img.convert("RGB").save(path, "PNG")


PLAN = (["permit"] * 14 + ["renewal"] * 8 + ["entry"] * 10 + ["recheck"] * 7 + ["dorm"] * 6 + ["term"] * 5)
GEN = {"permit": lambda i, s: t_permit(i, s), "renewal": lambda i, s: t_permit(i, s, True),
       "entry": t_entry_cert, "recheck": t_recheck, "dorm": t_dorm, "term": t_term}


def main():
    OUT.mkdir(exist_ok=True)
    rng.shuffle(PLAN)
    image_ids = set(rng.sample(range(1, 51), 15))
    truth = []
    for i, kind in enumerate(PLAN, 1):
        style = rng.choice(STYLES)
        dtype, workers, lines = GEN[kind](i, style)
        did = f"doc_{i:02d}"
        if i in image_ids:
            fname = f"{did}.png"
            render_png(lines, OUT / fname)
        else:
            fname = f"{did}.txt"
            (OUT / fname).write_text("\n".join(lines), encoding="utf-8")
        obligations = [o.to_dict() for w in workers for o in compute(dtype, w)]
        truth.append({"doc_id": did, "file": fname, "doc_type": dtype, "date_style": style,
                      "is_image": i in image_ids, "workers": workers, "obligations": obligations})
    (OUT / "ground_truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1), encoding="utf-8")
    n_obl = sum(len(t["obligations"]) for t in truth)
    n_w = sum(len(t["workers"]) for t in truth)
    print(f"docs={len(truth)} images={len(image_ids)} workers={n_w} obligations={n_obl}")


if __name__ == "__main__":
    main()
