"""Holiday supplement: 12 text docs whose deadlines fall on/through official holidays.
Output: ../docs_holiday/doc_HXX.txt + ground_truth.json (same schema as docs/)."""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import gen_docs as g  # noqa: E402
from rules import compute  # noqa: E402

OUT = g.ROOT / "docs_holiday"
CASES = [  # (template, forced event date, note)
    ("entry", date(2027, 2, 1), "入國後第3日為小年夜，工作日跨春節"),
    ("entry", date(2026, 2, 13), "入國後第3日為除夕，第15日為週六"),
    ("entry", date(2026, 9, 22), "第3日中秋、接週末與教師節"),
    ("entry", date(2027, 10, 22), "第3日為臺灣光復紀念日"),
    ("entry", date(2027, 4, 1), "清明連假"),
    ("recheck", date(2026, 12, 10), "第15日為行憲紀念日"),
    ("recheck", date(2027, 5, 25), "第15日為端午節"),
    ("recheck", date(2026, 2, 5), "第15日為春節補假"),
    ("dorm", date(2026, 4, 24), "第7日為勞動節"),
    ("dorm", date(2027, 10, 4), "第7日為國慶補假"),
    ("term", date(2026, 6, 16), "第3日為端午節"),
    ("term", date(2027, 12, 28), "第3日為元旦補假，順延跨年"),
]
TPL = {"entry": g.t_entry_cert, "recheck": g.t_recheck, "dorm": g.t_dorm, "term": g.t_term}


def main():
    OUT.mkdir(exist_ok=True)
    truth = []
    for i, (kind, d, note) in enumerate(CASES, 1):
        g.safe_event_date = lambda span, d=d: d  # force the event date
        style = g.rng.choice(["roc", "roc_cn", "roc_fw", "iso"])
        dtype, workers, lines = TPL[kind](i, style)
        did = f"doc_H{i:02d}"
        (OUT / f"{did}.txt").write_text("\n".join(lines), encoding="utf-8")
        obl = [o.to_dict() for w in workers for o in compute(dtype, w)]
        truth.append({"doc_id": did, "file": f"{did}.txt", "doc_type": dtype, "date_style": style, "is_image": False,
                      "workers": workers, "obligations": obl, "holiday_case": note})
    (OUT / "ground_truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1), encoding="utf-8")
    rolled = sum(1 for t in truth for o in t["obligations"] if "順延" in (o.get("note") or ""))
    print(f"docs={len(truth)} obligations={sum(len(t['obligations']) for t in truth)} rolled_by_holiday={rolled}")


if __name__ == "__main__":
    main()
