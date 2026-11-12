"""Score a run against ground truth.  Usage: python score.py extract_haiku [llm_only_haiku ...]"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from rules import compute  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["entry_date", "permit_start", "permit_end", "event_date"]
FIELD_ZH = {"entry_date": "入國日", "permit_start": "許可起日", "permit_end": "許可迄日", "event_date": "事件日"}


def norm(name: str | None) -> str:
    return re.sub(r"[^A-Z]", "", (name or "").upper())


def match_workers(truth_ws, pred_ws):
    """Return list of (truth_worker, pred_worker_or_None)."""
    pred_ws = list(pred_ws or [])
    used, pairs = set(), []
    for k, tw in enumerate(truth_ws):
        hit = next((j for j, pw in enumerate(pred_ws) if j not in used and norm(pw.get("name")) == norm(tw["name"])), None)
        if hit is None and k < len(pred_ws) and k not in used:
            hit = k  # fall back to order
        if hit is not None:
            used.add(hit)
        pairs.append((tw, pred_ws[hit] if hit is not None else None))
    return pairs, len(pred_ws) - len(used)


def obl_map(obls, name_by_norm=None):
    m = {}
    for o in obls:
        w = norm(o.get("worker"))
        if name_by_norm is not None:
            w = name_by_norm.get(w, w)
        m[(w, o.get("key"))] = (o.get("start") or None, o.get("due"))
    return m


def score_run(run: str):
    truth = json.loads((ROOT / os.environ.get("DOCS_DIR", "docs") / "ground_truth.json").read_text(encoding="utf-8"))
    run_dir = ROOT / "runs" / run
    mode = "extract" if run.startswith("extract") else "llm_only"
    agg = defaultdict(lambda: [0, 0])
    errors, missing_runs, extra_total, seconds = [], [], 0, []
    for d in truth:
        f = run_dir / f"{d['doc_id']}.json"
        if not f.exists():
            missing_runs.append(d["doc_id"]); continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        seconds.append(rec.get("seconds") or 0)
        pred = rec.get("parsed") or {}
        groups = ["全部", "圖片" if d["is_image"] else "純文字", f"日期格式:{d['date_style']}", f"類型:{d['doc_type']}"]

        def add(metric, ok):
            for g in groups:
                agg[(metric, g)][0] += int(ok); agg[(metric, g)][1] += 1

        if rec.get("error") or not pred:
            errors.append(f"{d['doc_id']}：無法解析輸出（{(rec.get('error') or '空白')[:80]}）")

        # map predicted worker names onto truth names so llm_only obligations line up
        if mode == "extract":
            add("文件類型", pred.get("doc_type") == d["doc_type"])
            if pred.get("doc_type") != d["doc_type"]:
                errors.append(f"{d['doc_id']}：文件類型判成「{pred.get('doc_type')}」，應為「{d['doc_type']}」")
            pairs, extra_w = match_workers(d["workers"], pred.get("workers"))
            if extra_w:
                errors.append(f"{d['doc_id']}：多抽出 {extra_w} 位不存在的外國人")
            pred_obls = []
            for tw, pw in pairs:
                for fld in FIELDS:
                    if tw[fld] is None and (pw or {}).get(fld) is None:
                        continue
                    ok = pw is not None and pw.get(fld) == tw[fld]
                    add("日期欄位", ok)
                    if not ok:
                        errors.append(f"{d['doc_id']}（{d['file']}，{d['date_style']}）{tw['name']} {FIELD_ZH[fld]}：抽成 {(pw or {}).get(fld)}，應為 {tw[fld]}")
                if pw:
                    pw2 = dict(pw, name=tw["name"])
                    pred_obls += [o.to_dict() for o in compute(pred.get("doc_type") or "", pw2)]
        else:
            pairs, _ = match_workers(d["workers"], [{"name": o.get("worker")} for o in {norm(o.get('worker')): o for o in pred.get("obligations", [])}.values()])
            name_map = {norm(pw["name"]): norm(tw["name"]) for tw, pw in pairs if pw}
            pred_obls = [dict(o, worker=o.get("worker")) for o in pred.get("obligations", [])]

        tmap = obl_map(d["obligations"])
        pmap = obl_map(pred_obls, None if mode == "extract" else name_map)
        doc_ok = True
        for k, v in tmap.items():
            ok = pmap.get(k) == v
            add("應辦期限", ok)
            if not ok:
                doc_ok = False
                if mode == "llm_only" or pmap.get(k) is not None:
                    errors.append(f"{d['doc_id']} 期限 {k[1]}：輸出 {pmap.get(k)}，應為 {v}")
        extras = [k for k in pmap if k not in tmap]
        extra_total += len(extras)
        if extras:
            doc_ok = False
        add("整份文件全對", doc_ok)
    return {"run": run, "mode": mode, "agg": agg, "errors": errors, "missing": missing_runs,
            "extra": extra_total, "avg_seconds": round(sum(seconds) / max(len(seconds), 1), 1), "n": len(seconds)}


def pct(a):
    return f"{a[0]}/{a[1]}（{100 * a[0] / a[1]:.1f}%）" if a[1] else "—"


def report(results):
    out = ["# 公文期限判讀驗證結果", ""]
    metrics = ["文件類型", "日期欄位", "應辦期限", "整份文件全對"]
    out.append("| 指標 | " + " | ".join(r["run"] for r in results) + " |")
    out.append("|---|" + "---|" * len(results))
    for m in metrics:
        out.append(f"| {m} | " + " | ".join(pct(r["agg"].get((m, "全部"), [0, 0])) for r in results) + " |")
    out.append("| 多餘/錯誤提醒數 | " + " | ".join(str(r["extra"]) for r in results) + " |")
    out.append("| 平均每份秒數 | " + " | ".join(str(r["avg_seconds"]) for r in results) + " |")
    out.append("| 已跑文件數 | " + " | ".join(str(r["n"]) for r in results) + " |")
    for r in results:
        out += ["", f"## {r['run']} 分組明細", "", "| 分組 | " + " | ".join(metrics) + " |", "|---|" + "---|" * len(metrics)]
        groups = sorted({g for (_, g) in r["agg"]}, key=lambda g: (g != "全部", g))
        for g in groups:
            out.append(f"| {g} | " + " | ".join(pct(r["agg"].get((m, g), [0, 0])) for m in metrics) + " |")
        out += ["", f"### 錯誤清單（{len(r['errors'])}）", ""] + [f"- {e}" for e in r["errors"]]
        if r["missing"]:
            out.append(f"\n未跑：{', '.join(r['missing'])}")
    return "\n".join(out)


if __name__ == "__main__":
    runs = sys.argv[1:] or ["extract_haiku"]
    res = [score_run(r) for r in runs]
    (ROOT / "results").mkdir(exist_ok=True)
    p = ROOT / "results" / f"score_{'_vs_'.join(runs)}.md"
    p.write_text(report(res), encoding="utf-8")
    print(p)
