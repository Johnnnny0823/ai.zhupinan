"""Leak test: mask every synthetic document and check that no personal data survives,
while the dates and legal text the LLM needs are left intact.

Usage: python test_privacy.py   -> writes ../results/privacy_leak_test.md
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from privacy import mask  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files = (sorted(glob.glob(os.path.join(ROOT, "docs", "*.txt")))
         + sorted(glob.glob(os.path.join(ROOT, "docs_holiday", "*.txt")))
         + sorted(glob.glob(os.path.join(ROOT, "penalty", "p*.txt"))))
truth = {}
for gt in ("docs", "docs_holiday"):
    for d in json.load(open(os.path.join(ROOT, gt, "ground_truth.json"), encoding="utf-8")):
        truth[d["file"]] = d

KEY = re.compile(r"(入國日期|聘僱許可期間|收文日期|變更日|終止日|檢查日期|罰鍰|第\d+條)")
leaks, damaged, n_secrets = [], [], 0
by_kind = {}
for f in files:
    t = open(f, encoding="utf-8").read()
    m, mp = mask(t)
    secrets = []

    def add(kind, values):
        for v in values:
            v = v.strip()
            if v and v not in ("（略）",):
                secrets.append((kind, v))

    add("護照號碼", re.findall(r"護照號碼\s*[:：]?\s*([A-Z0-9]{6,10})", t))
    add("身分證／居留證號", re.findall(r"(?<![A-Za-z0-9])[A-Z][12A-D89]\d{8}(?![0-9])", t))
    add("統一編號", re.findall(r"統一編號\s*[:：]?\s*(\d{8})", t))
    add("出生日期", re.findall(r"出生(?:日期|年月日)\s*[:：]?\s*([^\s　]+)", t))
    add("地址", re.findall(r"(?:地址|住宿地點)\s*[:：]\s*([^\n　]+)", t))
    d = truth.get(os.path.basename(f))
    if d:
        add("移工姓名", [w["name"] for w in d["workers"]])
    add("移工姓名", re.findall(r"外國人([A-Z][A-Z ]+[A-Z])於", t))
    for kind, s in set(secrets):
        n_secrets += 1
        by_kind[kind] = by_kind.get(kind, 0) + 1
        if s in m:
            leaks.append((os.path.basename(f), kind, s))
    inv = {real: tok for tok, real in mp.items()}
    for line in t.splitlines():
        if KEY.search(line):
            exp = line
            for real, tok in inv.items():
                exp = exp.replace(real, tok)
            if exp not in m:
                damaged.append((os.path.basename(f), line.strip()[:70]))

out = ["# 個資遮蔽洩漏測試", "",
       f"- 測試文件：{len(files)} 份純文字（公文 47、處分書草稿 30）；15 份掃描圖片無法在本機先遮蔽，不在範圍內",
       f"- 檢查的個資值：{n_secrets} 筆（" + "、".join(f"{k} {v}" for k, v in sorted(by_kind.items())) + "）",
       f"- **洩漏：{len(leaks)} 筆**",
       f"- **關鍵日期／條文被誤遮：{len(damaged)} 行**", ""]
out += [f"- 洩漏 {a}｜{b}｜{c}" for a, b, c in leaks]
out += [f"- 誤遮 {a}｜{b}" for a, b in damaged]
os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
p = os.path.join(ROOT, "results", "privacy_leak_test.md")
open(p, "w", encoding="utf-8").write("\n".join(out))
print(p)
