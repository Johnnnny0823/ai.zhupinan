"""Regression tests for the S00-S02 code review findings (2026-11-17).

Run from the repo root:  .venv\\Scripts\\python -m unittest discover -s demo/tests -v
"""
import asyncio
import importlib
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "demo" / "server"))

EXTRACT = {"doc_type": "入國通報受理證明書",
           "workers": [{"name": "PERSON_01", "entry_date": "2026-03-05", "evidence": {"entry_date": "115/03/05"}}]}


class Base(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        self.tmp = tempfile.TemporaryDirectory()
        b = Path(self.tmp.name)
        os.environ.update({"ZP_DB_PATH": str(b / "t.db"), "ZP_UPLOAD_DIR": str(b / "u"), "ZP_TMP_DIR": str(b / "i"),
                           "DEMO_LOGIN_CODES": "employer_a:ca,employer_b:cb,officer:co"})
        for m in ("app", "db", "auth", "documents", "store"):
            sys.modules.pop(m, None)
        self.app = importlib.import_module("app")
        self.delay = 0
        self.reply = json.dumps(EXTRACT, ensure_ascii=False)

        def fake(*a, **k):
            if self.delay:
                time.sleep(self.delay)
            return self.reply
        self.app.llm.call = fake
        from fastapi.testclient import TestClient
        self.TC = TestClient

    def tearDown(self):
        for m in ("app", "db", "auth", "documents", "store"):
            sys.modules.pop(m, None)
        os.environ.clear()
        os.environ.update(self._env)
        self.tmp.cleanup()

    def login(self, acct="employer_a", code="ca", headers=None):
        c = self.TC(self.app.app)
        r = c.post("/api/session", json={"account": acct, "code": code}, headers=headers or {})
        assert r.status_code == 200, r.text
        return c


class NonBlockingTest(Base):
    def test_model_call_does_not_freeze_other_requests(self):
        import httpx
        self.delay = 1.5
        login = self.login()
        cookie = login.cookies.get("zp_session")

        async def run():
            transport = httpx.ASGITransport(app=self.app.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver",
                                         cookies={"zp_session": cookie}) as ac:
                t0 = time.monotonic()
                slow = asyncio.create_task(ac.post("/api/documents/extract",
                                                   files={"file": ("a.txt", "合成 115/03/05".encode())}))
                await asyncio.sleep(0.2)
                h = await ac.get("/api/health")
                health_at = time.monotonic() - t0
                r = await slow
                return h.status_code, health_at, r.status_code
        h, health_at, slow = asyncio.run(run())
        self.assertEqual((h, slow), (200, 200))
        self.assertLess(health_at, 1.0)  # answered while the model call was still running


class RocDateTest(Base):
    def test_slash_and_dot_roc_dates_flagged(self):
        import documents
        for s in ("115/03/05", "115.3.5", "民國115年3月5日", "115-03-05"):
            self.assertIn("民國年", documents.field_warning(s, False) or "", s)
        self.assertIsNone(documents.field_warning("2026/03/05", False))
        self.assertIsNone(documents.field_warning("2026-03-05", False))

    def test_slash_roc_requires_tick(self):
        c = self.login()
        ex = c.post("/api/documents/extract", files={"file": ("a.txt", "合成 115/03/05".encode())}).json()
        r = c.post("/api/documents/confirm", json={"extract_id": ex["extract_id"], "document_kind": ex["document_kind"],
                                                   "workers": [{"name": "X", "entry_date": "2026-03-05"}]})
        self.assertEqual(r.status_code, 422)


class LockoutTest(Base):
    def test_one_client_behind_proxy_does_not_lock_others(self):
        c = self.TC(self.app.app)
        for i in range(6):
            c.post("/api/session", json={"account": "employer_a", "code": f"bad{i}"},
                   headers={"X-Forwarded-For": "203.0.113.7"})
        locked = c.post("/api/session", json={"account": "employer_a", "code": "ca"},
                        headers={"X-Forwarded-For": "203.0.113.7"})
        self.assertEqual(locked.status_code, 429)
        other = self.TC(self.app.app).post("/api/session", json={"account": "employer_a", "code": "ca"},
                                           headers={"X-Forwarded-For": "198.51.100.9"})
        self.assertEqual(other.status_code, 200)

    def test_account_wide_cap_stops_rotating_ips(self):
        c = self.TC(self.app.app)
        codes = [c.post("/api/session", json={"account": "employer_b", "code": "x"},
                        headers={"X-Forwarded-For": f"10.0.{i // 250}.{i % 250}"}).status_code for i in range(60)]
        self.assertIn(429, codes)


class UploadSizeTest(Base):
    def test_oversized_request_refused_before_parsing(self):
        c = self.login()
        r = c.post("/api/documents/extract", content=b"x" * 10,
                   headers={"content-type": "multipart/form-data; boundary=zz", "content-length": str(40 * 1024 * 1024)})
        self.assertEqual(r.status_code, 413)

    def test_spool_keeps_uploads_in_memory(self):
        import starlette.formparsers as fp
        import documents
        self.assertGreater(fp.MultiPartParser.spool_max_size, documents.MAX_BYTES)


class EncodingTest(Base):
    def test_big5_and_utf16_text_accepted(self):
        c = self.login()
        for raw in ("合成測試 入國日期 115/03/05".encode("cp950"), "合成測試 入國日期".encode("utf-16")):
            r = c.post("/api/documents/extract", files={"file": ("a.txt", raw)})
            self.assertEqual(r.status_code, 200, r.text)

    def test_binary_still_rejected(self):
        r = self.login().post("/api/documents/extract", files={"file": ("a.txt", bytes(range(1, 255)) * 4)})
        self.assertEqual(r.status_code, 415)


class ResetTempTest(Base):
    def test_reset_keeps_fresh_temp_files_of_running_calls(self):
        import documents
        fresh = documents.tmp_root() / "zp-live" / "scan.png"
        fresh.parent.mkdir(parents=True)
        fresh.write_bytes(b"x")
        stale = documents.tmp_root() / "zp-old" / "scan.png"
        stale.parent.mkdir(parents=True)
        stale.write_bytes(b"x")
        old = time.time() - 3600
        os.utime(stale, (old, old))
        os.utime(stale.parent, (old, old))
        self.assertEqual(self.login("officer", "co").post("/api/demo/reset").status_code, 200)
        self.assertTrue(fresh.exists())
        self.assertFalse(stale.exists())


class SingleWritePathTest(Base):
    def test_obligations_save_goes_through_confirm(self):
        c = self.login()
        r = c.post("/api/obligations", json={"doc_type": "入國通報受理證明書",
                                             "workers": [{"name": "X", "entry_date": "2026-12-01"}], "save": True})
        self.assertEqual(r.status_code, 200)
        self.assertIn("task_ids", r.json())
        con = sqlite3.connect(os.environ["ZP_DB_PATH"])
        self.assertEqual(con.execute("SELECT source_filename FROM documents").fetchone()[0], "手動輸入")
        con.close()


class VersionTest(Base):
    def test_health_version_tracks_work_package(self):
        self.assertNotIn("s00", self.TC(self.app.app).get("/api/health").json()["version"])


if __name__ == "__main__":
    unittest.main()
