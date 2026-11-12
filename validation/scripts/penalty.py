"""Penalty-decision checker test: 30 synthetic draft 處分書 with injected defects.

Seven checks (basis in ../laws):
 C1 相對人      行政程序法96(1)
 C2 事實        行政程序法96(2)  — concrete date + act + evidence
 C3 違反條文    就業服務法 56/57 — must match the facts
 C4 處罰條文    就業服務法 63/67/68 — must match the violated article
 C5 罰鍰金額    within statutory range
 C6 陳述意見    行政程序法102/103
 C7 救濟教示    行政程序法96(6) + 訴願法4,14,58: 30日, 經由新竹市政府, 向勞動部
Usage: python penalty.py gen | run --model haiku | score
"""
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract import claude_bin, parse_json, ROOT  # noqa: E402

DIR = ROOT / "penalty"
OUT = ROOT / "runs" / "penalty"
CHECKS = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
CHECK_ZH = {"C1": "處分相對人", "C2": "事實", "C3": "違反條文", "C4": "處罰條文", "C5": "罰鍰金額", "C6": "陳述意見", "C7": "救濟教示"}
rng = random.Random(1150)

V = [  # fact, violated article, penalty article, min, max
    ("所聘僱之外國人{w}自{d}起連續曠職三日失去聯繫，受處分人未於三日內以書面通知本府、移民署及警察機關，遲至{d2}始行通報",
     "就業服務法第56條第1項", "就業服務法第68條第1項", 30000, 150000),
    ("指派所聘僱從事家庭看護工作之外國人{w}，於{d}在受處分人經營之小吃店從事備餐、洗碗等許可以外之工作",
     "就業服務法第57條第3款", "就業服務法第68條第1項", 30000, 150000),
    ("未經許可，指派所聘僱從事製造工作之外國人{w}，自{d}起至他廠區（新竹市香山區）工作，變更工作場所",
     "就業服務法第57條第4款", "就業服務法第68條第1項", 30000, 150000),
    ("未依規定安排所聘僱之外國人{w}於入國後滿六個月之日前後三十日內（期限至{d}）接受定期健康檢查",
     "就業服務法第57條第5款", "就業服務法第67條第1項", 60000, 300000),
    ("非法扣留所聘僱外國人{w}之護照及居留證，經本府於{d}訪查時當場查獲",
     "就業服務法第57條第8款", "就業服務法第67條第1項", 60000, 300000),
    ("聘僱未經許可之外國人{w}於{d}在受處分人工廠從事包裝工作",
     "就業服務法第57條第1款", "就業服務法第63條第1項", 150000, 750000),
]
SAME_PEN = {"就業服務法第68條第1項": ["就業服務法第56條第1項", "就業服務法第57條第3款", "就業服務法第57條第4款"],
            "就業服務法第67條第1項": ["就業服務法第57條第5款", "就業服務法第57條第8款", "就業服務法第57條第9款"],
            "就業服務法第63條第1項": ["就業服務法第57條第1款", "就業服務法第57條第2款"]}
RANGE = {"就業服務法第68條第1項": (30000, 150000), "就業服務法第67條第1項": (60000, 300000), "就業服務法第63條第1項": (150000, 750000)}
WRONG_PEN = {"就業服務法第68條第1項": "就業服務法第67條第1項", "就業服務法第67條第1項": "就業服務法第68條第1項",
             "就業服務法第63條第1項": "就業服務法第67條第1項"}
NAMES = ["NGUYEN THI HOA", "DEWI LESTARI", "MARIA SANTOS", "TRAN VAN BINH", "SRI WAHYUNI", "JOY BAUTISTA"]
EMP = [("風城精密工業股份有限公司", "代表人：陳○○"), ("竹塹電子材料股份有限公司", "代表人：林○○"), ("黃○○", ""), ("張○○", ""), ("香山金屬製品有限公司", "代表人：吳○○")]


def roc(y, m, d):
    return f"{y - 1911}年{m}月{d}日"


def make(i, defects):
    v = V[i % len(V)]
    fact_t, viol, pen, lo, hi = v
    emp, rep = rng.choice(EMP)
    w = rng.choice(NAMES)
    m = rng.randint(3, 8)
    d1, d2 = roc(2026, m, rng.randint(1, 20)), roc(2026, m, rng.randint(21, 28))
    fine = rng.choice([lo, lo, lo + (hi - lo) // 4])
    lines = ["【合成測試文件・非真實公文・僅供竹聘安 AI 驗證使用】", "新竹市政府 裁處書（草稿）",
             f"發文日期：中華民國{roc(2026, m + 2, rng.randint(1, 28))}", f"發文字號：府勞外字第{rng.randint(1150000000, 1159999999)}號", ""]
    if "C1" in defects:
        lines.append("受處分人：（詳附件）")
    else:
        if rep:
            lines.append(f"受處分人：{emp}（統一編號：{rng.randint(10000000, 99999999)}）")
            lines.append(f"代表人：{rep.split('：')[1]}　出生年月日：{rng.randint(45, 80)}年{rng.randint(1, 12)}月{rng.randint(1, 28)}日　性別：{rng.choice(['男', '女'])}　身分證統一號碼：J{rng.randint(1, 2)}{rng.randint(10000000, 99999999)}")
        else:
            lines.append(f"受處分人：{emp}　出生年月日：{rng.randint(45, 80)}年{rng.randint(1, 12)}月{rng.randint(1, 28)}日　性別：{rng.choice(['男', '女'])}　身分證統一號碼：J{rng.randint(1, 2)}{rng.randint(10000000, 99999999)}")
        lines.append(f"地址：新竹市東區{rng.choice(['光復路一段', '中華路三段', '經國路一段'])}{rng.randint(10, 400)}號")
    lines.append("")
    lines.append(f"主旨：處受處分人新臺幣{fine:,}元罰鍰。".replace(f"{fine:,}", "{FINE}"))
    if "C2" in defects:
        fact = "受處分人違反就業服務法相關規定，經查屬實。"
    else:
        fact = "受處分人" + fact_t.format(w=w, d=d1, d2=d2) + f"，有本府{d2}訪查紀錄及談話紀錄在卷可稽。"
    lines += ["事實：", fact, ""]
    viol_cited = rng.choice([x for x in SAME_PEN[pen] if x != viol]) if "C3" in defects else viol
    pen_cited = WRONG_PEN[pen] if "C4" in defects else pen
    if "C4" in defects and "C5" not in defects:
        olo, ohi = RANGE[pen_cited]
        fine = max(lo, olo)
        assert fine <= min(hi, ohi)
    if "C5" in defects:
        fine = rng.choice([lo // 2, hi * 2])
        if "C4" in defects:  # out of both ranges
            olo, ohi = RANGE[pen_cited]
            fine = rng.choice([min(lo, olo) // 2, max(hi, ohi) * 2])
    lines[lines.index(next(l for l in lines if l.startswith("主旨")))] = f"主旨：處受處分人新臺幣{fine:,}元罰鍰。"
    lines += ["理由及法令依據：", f"一、按{viol_cited}定有明文。",
              f"二、受處分人違反上開規定，依{pen_cited}規定，處新臺幣{fine:,}元罰鍰。"]
    if "C6" not in defects:
        lines.append(f"三、本府前於{d2}以書面通知受處分人陳述意見，受處分人陳述意見未能採為有利之認定。")
    lines.append("")
    if "C7" not in defects:
        lines.append("救濟教示：受處分人如不服本處分，應自本處分書送達之次日起30日內，繕具訴願書經由本府向勞動部提起訴願。")
    else:
        lines.append(rng.choice(["救濟教示：受處分人如不服本處分，得於二個月內向本府提起訴願。",
                                 "救濟教示：受處分人如不服本處分，應自送達之次日起30日內，逕向臺北高等行政法院提起訴訟。",
                                 "（本處分書未載救濟教示）"]))
    lines += ["", "市長　○○○（署名蓋章）"]
    return lines


def gen():
    DIR.mkdir(exist_ok=True)
    plan = [[] for _ in range(8)]
    for c in CHECKS:
        plan += [[c], [c]]
    plan += [["C2", "C6"], ["C4", "C7"], ["C3", "C5"], ["C1", "C7"], ["C5", "C6"], ["C2", "C4"], ["C3", "C6"], ["C5", "C7"]]
    plan = plan[:30] if len(plan) >= 30 else plan
    rng.shuffle(plan)
    truth = []
    for i, defects in enumerate(plan, 1):
        (DIR / f"p{i:02d}.txt").write_text("\n".join(make(i, set(defects))), encoding="utf-8")
        truth.append({"id": f"p{i:02d}", "defects": sorted(defects)})
    (DIR / "truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(truth), "drafts;", sum(not t["defects"] for t in truth), "clean")


REF_ARTS = [("就業服務法", ["第 56 條", "第 57 條", "第 63 條", "第 67 條", "第 68 條"], "N0090001.txt"),
            ("行政程序法", ["第 96 條", "第 102 條", "第 103 條"], "A0030055.txt"),
            ("訴願法", ["第 4 條", "第 14 條", "第 58 條"], "A0030020.txt")]


def refs():
    out = []
    for law, arts, f in REF_ARTS:
        t = (ROOT / "laws" / f).read_text(encoding="utf-8")
        for a in arts:
            m = re.search(r"## " + a + r"\n(.*?)(?=\n## |\Z)", t, re.S)
            out.append(f"【{law}{a.replace(' ', '')}】\n{m.group(1).strip()}")
    return "\n\n".join(out)


SYS = """你是「竹聘安 AI」處分書檢核助手，協助新竹市政府承辦人檢查就業服務法裁處書草稿是否有缺漏。你只指出問題與依據，不決定是否裁罰。
請逐項檢查以下七項，輸出 JSON（不要 markdown 程式碼框）：
{"C1": {"ok": true/false, "reason": "..."}, ..., "C7": {...}}
C1 處分相對人：是否載明受處分人姓名或名稱、地址（法人另載代表人）。
C2 事實：是否具體載明違規日期、行為與證據，而非概括性用語。
C3 違反條文：引用的違反條文是否與事實所述行為相符。
C4 處罰條文：引用的處罰條文是否為該違反條文所對應的罰則。
C5 罰鍰金額：金額是否在該處罰條文的法定範圍內。
C6 陳述意見：是否載明已給予陳述意見機會，或說明依行政程序法第103條得不給予之事由。
C7 救濟教示：是否正確載明救濟方法、期間及受理機關（不服縣市政府處分：自送達次日起30日內，經由原處分機關向中央主管機關提起訴願）。
reason 請用一句繁體中文說明，並引用條號。以下附參考條文，請以參考條文為準。"""


def run_one(pid, model):
    out = OUT / model / f"{pid}.json"
    if out.exists():
        return "cached"
    sp = ROOT / "runs" / "_system_penalty.txt"
    sp.write_text(SYS + "\n\n" + refs(), encoding="utf-8")
    doc = (DIR / f"{pid}.txt").read_text(encoding="utf-8")
    p = subprocess.run([claude_bin(), "-p", "--model", model, "--system-prompt-file", str(sp), "--tools", "",
                        "--strict-mcp-config", "--no-session-persistence", "--output-format", "json"],
                       input="請檢核以下裁處書草稿：\n\n" + doc, capture_output=True, text=True, encoding="utf-8",
                       timeout=300, cwd=str(ROOT))
    try:
        env = json.loads(p.stdout)
        res, err = env.get("result"), (env.get("result") if env.get("is_error") else None)
    except Exception as e:  # noqa: BLE001
        res, err = None, f"{e}: {p.stdout[:200]}"
    if err and ("401" in err or "limit" in err.lower()):
        return "FATAL " + err[:150]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"raw": res, "parsed": parse_json(res or "") if not err else None, "error": err},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    return "ok" if not err else "ERR " + err[:100]


def score():
    truth = json.loads((DIR / "truth.json").read_text(encoding="utf-8"))
    lines = ["# 處分書七項要件檢核驗證結果", ""]
    for d in sorted(OUT.iterdir()):
        tp = fp = fn = tn = 0
        per = {c: [0, 0, 0] for c in CHECKS}  # tp, fn, fp
        exact = n = 0
        detail = []
        for t in truth:
            f = d / f"{t['id']}.json"
            if not f.exists():
                continue
            n += 1
            pr = json.loads(f.read_text(encoding="utf-8")).get("parsed") or {}
            flagged = {c for c in CHECKS if not (pr.get(c) or {}).get("ok", True)}
            real = set(t["defects"])
            for c in CHECKS:
                if c in real and c in flagged: tp += 1; per[c][0] += 1
                elif c in real: fn += 1; per[c][1] += 1; detail.append(f"- {t['id']} 漏抓 {c} {CHECK_ZH[c]}")
                elif c in flagged: fp += 1; per[c][2] += 1; detail.append(f"- {t['id']} 誤報 {c} {CHECK_ZH[c]}：{(pr.get(c) or {}).get('reason', '')}")
                else: tn += 1
            exact += flagged == real
        rec = tp / max(tp + fn, 1); prec = tp / max(tp + fp, 1)
        clean = [t for t in truth if not t["defects"]]
        lines += [f"## 模型：{d.name}", "",
                  f"- 埋入缺漏 {tp + fn} 個，抓到 {tp} 個 → **偵測率（recall）{100 * rec:.0f}%**",
                  f"- 提出警示 {tp + fp} 次，正確 {tp} 次 → **警示準確率（precision）{100 * prec:.0f}%**",
                  f"- 整份判斷完全正確：{exact}/{n}",
                  f"- 無缺漏草稿共 {len(clean)} 份；逐項誤報總數 {fp}", "",
                  "| 項目 | 抓到 | 漏抓 | 誤報 |", "|---|---|---|---|"]
        lines += [f"| {c} {CHECK_ZH[c]} | {v[0]} | {v[1]} | {v[2]} |" for c, v in per.items()]
        lines += ["", "### 明細", ""] + detail + [""]
    p = ROOT / "results" / "score_penalty.md"
    p.parent.mkdir(exist_ok=True)
    p.write_text("\n".join(lines), encoding="utf-8")
    print(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["gen", "run", "score"])
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    if a.action == "gen":
        return gen()
    if a.action == "score":
        return score()
    ids = [t["id"] for t in json.loads((DIR / "truth.json").read_text(encoding="utf-8"))]
    with ThreadPoolExecutor(a.workers) as ex:
        for pid, msg in zip(ids, ex.map(lambda p: run_one(p, a.model), ids)):
            print(pid, msg, flush=True)
            if msg.startswith("FATAL"):
                break


if __name__ == "__main__":
    main()
