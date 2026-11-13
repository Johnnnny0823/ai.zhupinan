"""Legal Q&A test: 30 questions, ground truth = key facts from statute text.

Two conditions:
  bare : model answers from its own knowledge
  rag  : top-5 retrieved articles (char-bigram BM25 over ../laws/*.txt) are given first
Grading is automatic: an answer is correct only if ALL key facts appear; citation
is checked separately (law article number mentioned).
Usage: python qa.py run --model haiku --cond bare|rag ;  python qa.py score
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract import claude_bin, ROOT  # noqa: E402

LAWS = ROOT / "laws"
import os
OUT = ROOT / "runs" / ("qa_holdout" if os.environ.get("QSET") == "holdout" else "qa")
CN = "零一二三四五六七八九"


def num_variants(n: int) -> list[str]:
    if n < 10:
        cn = CN[n]
    elif n < 100:
        t, o = divmod(n, 10)
        cn = ("" if t == 1 else CN[t]) + "十" + ("" if o == 0 else CN[o])
    else:
        cn = None
    v = [str(n)]
    if cn:
        v.append(cn)
    if n == 2:
        v.append("兩")
    return v


def days(n):  # "3日" / "三日" / "3天"
    return [f"{x}{u}" for x in num_variants(n) for u in ("日", "天", " 日", " 天")]


def months(n):
    return [f"{x}{u}" for x in num_variants(n) for u in ("個月", "月", " 個月")]


def wan(n):  # 3萬 / 三萬 / 30,000 / 30000
    return [f"{x}萬" for x in num_variants(n)] + [f"{n * 10000:,}", str(n * 10000)]


def art(law_short, no):
    return {"law": law_short, "no": no}


# Each question: q, facts (list of alternatives lists — all must match), cite
Q = [
    ("我家看護工剛入境台灣，我要在幾天內通知市政府來檢查？", [days(3)], art("管理辦法", "34")),
    ("移工入國後，雇主要在幾天內向勞動部申請聘僱許可？", [days(15)], art("管理辦法", "36")),
    ("我們工廠要把移工搬到新宿舍，搬完之後多久內要通知主管機關？", [days(7)], art("管理辦法", "33")),
    ("移工住宿地點變更，要通知哪一個機關？", [["當地主管機關", "地方主管機關", "縣市政府", "市政府"]], art("管理辦法", "33")),
    ("移工連續曠職幾天失去聯繫，雇主就要通報？要在幾天內通報？", [["連續曠職三日", "連續曠職3日", "連續曠職三天", "連續曠職3天"], ["三日內", "3日內", "三天內", "3天內"]], art("就服法", "56")),
    ("移工失聯時，雇主要以書面通知哪些機關？", [["當地主管機關", "地方主管機關"], ["入出國管理機關", "移民署"], ["警察機關", "警察局", "警察"]], art("就服法", "56")),
    ("移工失聯或聘僱關係終止，雇主沒有依規定通報，會被罰多少錢？", [wan(3), wan(15)], art("就服法", "68")),
    ("移工的定期健康檢查要在什麼時候做？", [["六個月", "6個月"], ["十八個月", "18個月"], ["三十個月", "30個月"], ["前後三十日", "前後30日", "前後30天", "前後三十天"]], art("健檢辦法", "3")),
    ("移工入國後的健康檢查期限是多久？", [["三個工作日", "3個工作日", "三個工作天", "3個工作天"]], art("健檢辦法", "3")),
    ("雇主沒有依規定安排移工做健康檢查，罰鍰是多少？", [wan(6), wan(30)], art("就服法", "67")),
    ("雇主收到移工定期健檢的再檢查診斷證明書後，要在多久內送衛生局備查？", [days(15)], art("健檢辦法", "9")),
    ("移工健檢確診肺結核，雇主要在多久內做什麼？", [days(15), ["都治"]], art("健檢辦法", "10")),
    ("移工聘僱許可快到期，我想繼續聘僱，要在什麼時間申請期滿續聘？", [["二個月", "2個月", "兩個月"], ["四個月", "4個月"]], art("管理辦法", "39")),
    ("移工聘僱許可快到期，但我不想續聘，可以怎麼做？期限為何？", [["期滿轉換"], ["二個月", "2個月", "兩個月"], ["四個月", "4個月"]], art("管理辦法", "40")),
    ("聘請家庭看護工，雇主要在移工入國前幾天向勞動部申請辦理入國講習等事項？", [["五日前", "5日前", "五天前", "5天前"]], art("管理辦法", "34-1")),
    ("家庭看護工入國時沒有完成入國講習，雇主應該怎麼辦？", [["九十日", "90日", "九十天", "90天"], ["講習"]], art("管理辦法", "34-4")),
    ("雇主可以幫移工保管護照嗎？違反的罰則是什麼？", [["不得", "禁止", "不可以", "不能"], wan(6), wan(30)], art("就服法", "57")),
    ("我請的家庭看護工，可以順便叫她到我開的店裡幫忙嗎？違反會怎樣？", [["不得", "不可以", "不能", "禁止", "許可以外"], wan(3), wan(15)], art("就服法", "57")),
    ("聘僱沒有工作許可的外國人，雇主會被罰多少？", [wan(15), wan(75)], art("就服法", "63")),
    ("雇主五年內再次非法聘僱外國人，會有什麼刑責？", [["三年以下有期徒刑", "3年以下有期徒刑"], ["一百二十萬", "120萬", "1,200,000"]], art("就服法", "63")),
    ("家庭看護工在台灣累計最多可以工作幾年？", [["十二年", "12年"], ["十四年", "14年"]], art("就服法", "52")),
    ("移工的聘僱許可期間最長是幾年？", [["三年", "3年"]], art("就服法", "52")),
    ("移工失聯，雇主依規定通報後滿多久仍未查獲，可以申請遞補？", [months(3)], art("就服法", "58")),
    ("原聘僱許可剩下的期間不足多久，就不能申請遞補？", [months(6)], art("就服法", "58")),
    ("被看護者幾歲以上聘請家庭看護工可以免經醫療機構專業評估？", [["八十歲", "80歲"], ["七十歲", "70歲"], ["癌症"]], art("就服法", "46")),
    ("雇主就業安定費繳晚了，有寬限期嗎？滯納金怎麼算？", [days(30), ["百分之零點三", "0.3%", "千分之三"], ["百分之三十", "30%"]], art("就服法", "55")),
    ("我是低收入戶，聘請家庭看護工要繳就業安定費嗎？", [["免繳", "免繳納", "不用繳", "不需繳", "免除"]], art("就服法", "55")),
    ("工廠移工聘僱關係終止要出國，雇主什麼時候要通知當地主管機關？", [["出國前"]], art("管理辦法", "68")),
    ("市府要對違規雇主開罰之前，一定要給雇主陳述意見的機會嗎？", [["陳述意見"], ["第一百零三條", "第103條", "103條", "得不給予", "例外"]], art("行政程序法", "102")),
    ("市府書面裁處書（行政處分書）依法應記載哪些事項？", [["事實"], ["理由"], ["法令依據", "法規依據", "法律依據"], ["救濟"]], art("行政程序法", "96")),
]

# Held-out questions written AFTER retrieval v2 was tuned on Q; never used for tuning.
QH = [
    ("就業安定費加徵滯納金 30 日後雇主還是沒繳，會發生什麼事？", [["強制執行"], ["廢止"]], art("就服法", "55")),
    ("期滿轉換時，移工已經和新雇主談好接手，新雇主可以直接申請嗎？", [["接續聘僱"]], art("管理辦法", "40")),
    ("移工健檢不合格被要求出國，雇主最晚什麼時候要讓他出國？", [["限令出國期限前", "出國期限前", "限令出國之期限前"]], art("管理辦法", "69")),
    ("移工因為許可被廢止而出國後，雇主多久內要通知勞動部？", [days(30)], art("管理辦法", "69")),
    ("如果雇主亂報移工失聯，移工可以怎麼辦？", [["申訴"], ["當地主管機關", "地方主管機關"]], art("就服法", "56")),
    ("移工連續曠職失聯、許可被廢止以後，雇主還要繼續繳就業安定費嗎？", [["無須", "不用", "不需", "免", "毋須", "不必"]], art("就服法", "55")),
    ("聘請家庭看護工，勞動契約可以簽不定期的嗎？", [["定期契約", "定期"]], art("就服法", "46")),
    ("移工入國三個工作日內來不及做健康檢查，怎麼辦？", [["延長三個工作日", "延長3個工作日", "補行"]], art("健檢辦法", "3")),
    ("市府開罰前，在什麼情況下可以不讓雇主陳述意見？", [["客觀上明白", "大量作成", "情況急迫", "顯屬輕微", "法定期間"]], art("行政程序法", "103")),
    ("移工的定期健檢再檢查結果出來，雇主要送哪個機關備查？", [["衛生主管機關", "衛生局"]], art("健檢辦法", "9")),
]
import os as _os
if _os.environ.get("QSET") == "holdout":
    Q = QH

LAW_FILES = {"N0090001.txt": "就業服務法", "N0090027.txt": "雇主聘僱外國人許可及管理辦法",
             "L0050018.txt": "受聘僱外國人健康檢查管理辦法", "A0030055.txt": "行政程序法"}


def load_articles():
    arts = []
    for f, name in LAW_FILES.items():
        t = (LAWS / f).read_text(encoding="utf-8")
        for m in re.finditer(r"## (第 [\d\-]+ 條)\n(.*?)(?=\n## |\Z)", t, re.S):
            arts.append({"law": name, "no": m.group(1).replace(" ", ""), "text": m.group(2).strip()})
    return arts


def bigrams(s):
    s = re.sub(r"\s", "", s)
    return [s[i:i + 2] for i in range(len(s) - 1)]


class BM25:
    def __init__(self, docs, k1=1.4, b=0.75):
        self.toks = [Counter(bigrams(d["law"] + d["text"])) for d in docs]
        self.N = len(docs)
        self.avg = sum(sum(c.values()) for c in self.toks) / self.N
        df = Counter(t for c in self.toks for t in c)
        self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()}
        self.k1, self.b, self.docs = k1, b, docs

    def top(self, q, k=5):
        qt = set(bigrams(q))
        scores = []
        for i, c in enumerate(self.toks):
            L = sum(c.values())
            s = sum(self.idf.get(t, 0) * c[t] * (self.k1 + 1) / (c[t] + self.k1 * (1 - self.b + self.b * L / self.avg)) for t in qt if t in c)
            scores.append((s, i))
        return [self.docs[i] for _, i in sorted(scores, reverse=True)[:k]]


SYNONYMS = [  # layperson phrase -> statute wording appended to the query
    (["入境", "剛來", "來台"], "入國"),
    (["搬", "宿舍", "住的地方", "住處"], "住宿地點 變更 生活照顧服務計畫書"),
    (["失聯", "跑掉", "逃跑", "不見"], "連續曠職三日失去聯繫"),
    (["罰", "多少錢", "違反會", "後果", "刑責", "坐牢"], "罰鍰 處 新臺幣"),
    (["看護工", "看護"], "家庭看護工作"),
    (["護照", "證件"], "扣留 護照 居留證件"),
    (["沒有工作許可", "沒有許可", "非法聘僱", "黑工"], "聘僱未經許可"),
    (["市政府", "市府", "縣政府"], "當地主管機關"),
    (["健檢", "體檢"], "健康檢查"),
    (["店裡", "幫忙", "別的工作", "兼差"], "許可以外之工作"),
    (["續聘", "到期", "快到期"], "聘僱許可有效期間屆滿 期滿續聘"),
    (["遞補", "補人"], "申請遞補 行蹤不明 屆滿 六個月內"),
    (["講習"], "入國講習"),
    (["裁處書", "處分書"], "行政處分 書面 記載"),
    (["陳述意見"], "陳述意見之機會"),
]
CN_NUM = {str(i): v for i, v in enumerate(["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"])}


def to_cn_article(n: int) -> str:
    t, o = divmod(n, 10)
    return ("" if t == 0 else ("" if t == 1 else CN_NUM[str(t)]) + "十") + ("" if o == 0 else CN_NUM[str(o)])


def expand_query(q: str) -> str:
    extra = [rep for keys, rep in SYNONYMS if any(k in q for k in keys)]
    return q + " " + " ".join(extra)


class Retriever2:
    """BM25 over expanded query; then attach penalty articles that cite a retrieved 就業服務法 article."""

    def __init__(self, arts):
        self.bm = BM25(arts)
        self.arts = arts
        self.penalty_of = {}  # "第56條" -> [penalty article dicts]
        esa = [a for a in arts if a["law"] == "就業服務法"]
        for a in esa:
            n = int(a["no"].strip("第條").split("-")[0])
            if 63 <= n <= 75:
                for b in esa:
                    bn = b["no"].strip("第條")
                    if "-" in bn:
                        continue
                    if f"第{to_cn_article(int(bn))}條" in a["text"]:
                        self.penalty_of.setdefault(b["no"], []).append(a)

    def top(self, q, k=6):
        hits = self.bm.top(expand_query(q), k)
        if any(x in q for x in ("罰", "多少錢", "違反", "後果", "刑")):
            seen = {(h["law"], h["no"]) for h in hits}
            for h in list(hits):
                if h["law"] == "就業服務法":
                    for pen in self.penalty_of.get(h["no"], []):
                        if (pen["law"], pen["no"]) not in seen:
                            hits.append(pen); seen.add((pen["law"], pen["no"]))
        return hits


SYS = ("你是「竹聘安 AI」法規助理，對象是台灣聘僱外籍移工的雇主與市府承辦人。"
       "請用繁體中文簡潔回答（150 字內），具體寫出天數、金額等數字，並在最後標明依據的法規名稱與條號。"
       "若提供了參考條文，請以參考條文為準。")


SYS_STRICT = SYS + (" 嚴格規則：(1) 只回答使用者問的事，不要主動補充其他情況；"
                     "(2) 每個數字、期限、罰則都必須能在某一條參考條文中找到原文，並標明是哪一條；"
                     "(3) 不同條文的罰則不可混用——某罰則條文只適用於它文字中列舉的條款；"
                     "(4) 參考條文中找不到的內容，直接說『參考條文未涵蓋』，不要憑記憶補充。")


def ask(i, model, cond, retriever):
    out = OUT / f"{cond}_{model}" / f"q{i + 1:02d}.json"
    if out.exists():
        return "cached"
    q = Q[i][0]
    user = q
    hits = []
    if cond in ("rag", "rag2", "rag2s"):
        hits = retriever.top(q, 5) if cond == "rag" else retriever.top(q)
        ctx = "\n\n".join(f"【{h['law']} {h['no']}】\n{h['text']}" for h in hits)
        user = f"參考條文：\n{ctx}\n\n問題：{q}"
    sp = ROOT / "runs" / "_system_qa.txt"
    sp.write_text(SYS_STRICT if cond == "rag2s" else SYS, encoding="utf-8")
    p = subprocess.run([claude_bin(), "-p", "--model", model, "--system-prompt-file", str(sp), "--tools", "",
                        "--strict-mcp-config", "--no-session-persistence", "--output-format", "json"],
                       input=user, capture_output=True, text=True, encoding="utf-8", timeout=300, cwd=str(ROOT))
    try:
        env = json.loads(p.stdout)
        ans, err = env.get("result"), (env.get("result") if env.get("is_error") else None)
    except Exception as e:  # noqa: BLE001
        ans, err = None, f"{e}: {p.stdout[:200]}"
    if err and ("401" in err or "limit" in err.lower()):
        return "FATAL " + err[:150]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"q": q, "answer": ans, "error": err,
                               "retrieved": [f"{h['law']}{h['no']}" for h in hits]}, ensure_ascii=False, indent=1), encoding="utf-8")
    return "ok"


LAW_ALIASES = {"管理辦法": ["雇主聘僱外國人許可及管理辦法", "許可及管理辦法", "管理辦法"],
               "就服法": ["就業服務法", "就服法"], "健檢辦法": ["健康檢查管理辦法", "健檢"],
               "行政程序法": ["行政程序法"]}


def cn_article(no: str) -> list[str]:
    base, *sub = no.split("-")
    n = int(base)
    cn = ""
    h, r = divmod(n, 100)
    if h:
        cn += CN[h] + "百" + ("零" if 0 < r < 10 else "")
    t, o = divmod(r, 10)
    if t:
        cn += ("" if (t == 1 and not h) else CN[t]) + "十"
    if o:
        cn += CN[o]
    suf = [f"-{sub[0]}", f"之{sub[0]}", f"之{CN[int(sub[0])]}"] if sub else [""]
    return [f"第{x}{s}條" for x in (base, cn) for s in suf] + [f"第{x}條{s}" for x in (base, cn) for s in suf if s] + ([f"{base}條"] if not sub else [])


def grade(ans: str, facts, cite):
    a = re.sub(r"\s", "", ans or "")
    a = a.replace("，", ",")
    # expand ranges like "2-4個月", "2至4個月", "二到四個月" so each endpoint is gradable
    a += " " + re.sub(r"([0-9一二三四五六七八九十兩]+)(?:-|~|～|至|到)([0-9一二三四五六七八九十]+)(個月|日|天|年|萬|歲)", r"\1\3 \2\3", a)
    facts_ok = all(any(re.sub(r"\s", "", alt) in a for alt in alts) for alts in facts)
    cite_ok = any(x in a for x in cn_article(cite["no"])) and any(x in a for x in LAW_ALIASES[cite["law"]])
    return facts_ok, cite_ok


PENALTY_MARKERS = {  # distinctive amounts of each penalty article (就業服務法)
    "63": ["75萬", "七十五萬", "750,000", "有期徒刑", "120萬", "一百二十萬"],
    "67": ["30萬", "三十萬", "300,000"],
    "68": ["15萬", "十五萬", "150,000"],
}


def contamination(ans: str, i: int, qs=None) -> list[str]:
    """Penalty markers from an article other than the question's own penalty article.
    Only meaningful for questions asking about fines; others return []."""
    qs = qs or Q
    q, facts, cite = qs[i]
    if not any("萬" in alt for alts in facts for alt in alts):
        return []
    a = re.sub(r"\s", "", ans or "")
    own = cite["no"] if cite["no"] in PENALTY_MARKERS else {"57": None}.get(cite["no"])
    # infer own article from expected amounts
    exp = "".join(alt for alts in facts for alt in alts)
    if "75萬" in exp: own = "63"
    elif "30萬" in exp: own = "67"
    elif "15萬" in exp: own = "68"
    bad = []
    for art_no, marks in PENALTY_MARKERS.items():
        if art_no == own:
            continue
        hit = [m for m in marks if m in a and not (own == "63" and m in ("15萬", "十五萬", "150,000"))]
        if hit:
            bad.append(f"第{art_no}條:{hit[0]}")
    return bad


def score():
    rows, summary = [], {}
    for d in sorted(OUT.glob("*_*")):
        ok_f = ok_c = n = n_bad = 0
        for i, (q, facts, cite) in enumerate(Q):
            f = d / f"q{i + 1:02d}.json"
            if not f.exists():
                continue
            r = json.loads(f.read_text(encoding="utf-8"))
            fo, co = grade(r["answer"], facts, cite)
            bad = contamination(r["answer"], i)
            n += 1; ok_f += fo; ok_c += co; n_bad += bool(bad)
            prefix = ("⚠混用" + ",".join(bad) + "｜") if bad else ""
            rows.append((d.name, i + 1, q, fo, co, prefix + (r["answer"] or "").replace("\n", " ")[:220], r.get("retrieved")))
        summary[d.name] = (ok_f, ok_c, n, n_bad)
    lines = ["# 法規問答 30 題驗證結果", "", "評分：答案須包含標準答案的全部關鍵事實（天數、金額、機關等，取自條文原文）才算正確；條號另計。", "",
             "混用罰則：罰則題的答案中出現『不屬於該題罰則條文』的金額或刑責（例：失聯未通報卻提到第63條的有期徒刑）。", "",
             "| 條件 | 內容正確 | 條號正確 | 混用罰則 | 題數 |", "|---|---|---|---|---|"]
    for k, (f, c, n, b) in summary.items():
        lines.append(f"| {k} | {f}/{n}（{100 * f / max(n, 1):.0f}%） | {c}/{n}（{100 * c / max(n, 1):.0f}%） | {b} 題 | {n} |")
    lines += ["", "## 逐題", "", "| 條件 | 題 | 問題 | 內容 | 條號 | 回答摘錄 |", "|---|---|---|---|---|---|"]
    for run, i, q, fo, co, a, _ in rows:
        lines.append(f"| {run} | {i} | {q} | {'✔' if fo else '✘'} | {'✔' if co else '✘'} | {a.replace('|', '／')} |")
    p = ROOT / "results" / ("score_qa_holdout.md" if os.environ.get("QSET") == "holdout" else "score_qa.md")
    p.parent.mkdir(exist_ok=True)
    p.write_text("\n".join(lines), encoding="utf-8")
    print(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["run", "score", "selftest"])
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--cond", choices=["bare", "rag", "rag2", "rag2s"], default="bare")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    if a.action == "score":
        return score()
    if a.action == "selftest":
        arts = load_articles()
        r1, r2 = BM25(arts), Retriever2(arts)
        def ok(hits, c):
            return any(h["no"].replace("第", "").replace("條", "") == c["no"] for h in hits)
        h1 = sum(ok(r1.top(q, 5), c) for q, _, c in Q)
        h2 = sum(ok(r2.top(q), c) for q, _, c in Q)
        miss = [i + 1 for i, (q, _, c) in enumerate(Q) if not ok(r2.top(q), c)]
        print(f"articles={len(arts)} v1_hit@5={h1}/{len(Q)} v2_hit={h2}/{len(Q)} v2_miss={miss} penalty_links={len(r2.penalty_of)}")
        return
    retr = BM25(load_articles()) if a.cond == "rag" else Retriever2(load_articles()) if a.cond in ("rag2", "rag2s") else None
    with ThreadPoolExecutor(a.workers) as ex:
        for i, msg in enumerate(ex.map(lambda i: ask(i, a.model, a.cond, retr), range(len(Q)))):
            print(f"q{i + 1:02d} {msg}", flush=True)
            if msg.startswith("FATAL"):
                break


if __name__ == "__main__":
    main()
