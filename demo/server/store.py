"""Writing confirmed documents and their tasks: the single write path shared by the API and migrate_state.py."""
from __future__ import annotations

import hashlib
import json
import sqlite3

import db

DATE_FIELDS = ("entry_date", "permit_start", "permit_end", "event_date", "notify_date")
KEEP_FIELDS = ("name", "job") + DATE_FIELDS   # the only worker fields stored after confirmation


def norm_worker(name: str) -> str:
    """Same worker + same task + same deadline = same to-do (prevents duplicates)."""
    return (name or "").strip().upper()


def save_document(con: sqlite3.Connection, actor_id: int | None, case_id: int, kind: str, workers: list[dict],
                  items: list[dict], filename: str | None, digest: str | None) -> tuple[int, list[int], int]:
    """Store only the confirmed fields (never the original) and the tasks, in one transaction.
    Returns (document_id, task_ids in the order of `items`, number of newly added tasks)."""
    kept = [{k: w.get(k) for k in KEEP_FIELDS if w.get(k)} for w in workers]
    fields = json.dumps({"doc_type": kind, "workers": kept}, ensure_ascii=False, sort_keys=True)
    added, task_ids = 0, []
    with db.tx(con):
        doc_id = con.execute(
            "INSERT INTO documents(case_id, kind, source_filename, confirmed_fields_json, confirmed_at, source_digest) "
            "VALUES (?,?,?,?,?,?)",
            (case_id, kind, filename, fields, db.now(), digest or hashlib.sha256(fields.encode("utf-8")).hexdigest())).lastrowid
        for o in items:
            cur = con.execute(
                "INSERT OR IGNORE INTO tasks(case_id, document_id, rule_key, worker, worker_norm, title, start_date, "
                "due_date, law_ref, note, office, official_url, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (case_id, doc_id, o["key"], o["worker"], norm_worker(o["worker"]), o["title"], o.get("start"),
                 o["due"], o.get("basis"), o.get("note"), o.get("office"), (o.get("online") or {}).get("url"), db.now()))
            added += cur.rowcount
            row = con.execute(
                "SELECT id FROM tasks WHERE case_id=? AND worker_norm=? AND rule_key=? AND IFNULL(start_date,'')=? AND due_date=?",
                (case_id, norm_worker(o["worker"]), o["key"], o.get("start") or "", o["due"])).fetchone()
            task_ids.append(row["id"])
        con.execute("UPDATE cases SET updated_at=? WHERE id=?", (db.now(), case_id))
        db.audit(con, actor_id, case_id, "document", doc_id, f"confirm:{added}_tasks")
    return doc_id, task_ids, added
