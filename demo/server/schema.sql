PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS accounts (
 id TEXT PRIMARY KEY, role TEXT NOT NULL CHECK(role IN ('employer','officer')),
 display_name TEXT NOT NULL, created_at TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0 CHECK(is_admin IN (0,1))
);
CREATE TABLE IF NOT EXISTS login_codes (
 code_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 expires_at TEXT NOT NULL, consumed_at TEXT
);
CREATE TABLE IF NOT EXISTS login_attempts (key_hash TEXT PRIMARY KEY, failures INTEGER NOT NULL, blocked_until TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
 id_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE, expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cases (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES accounts(id), display_code TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE, kind TEXT NOT NULL,
 source_filename TEXT NOT NULL, confirmed_fields_json TEXT NOT NULL, confirmed_at TEXT NOT NULL,
 source_digest TEXT NOT NULL, UNIQUE(case_id, source_digest)
);
CREATE TABLE IF NOT EXISTS tasks (
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
 document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE, rule_key TEXT NOT NULL,
 title TEXT NOT NULL, event_date TEXT, start_date TEXT, due_date TEXT, law_ref TEXT NOT NULL,
 law_version TEXT NOT NULL, calc_trace_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('todo','delegated','proof_submitted','done','needs_review')),
 office TEXT NOT NULL, official_url TEXT NOT NULL, UNIQUE(document_id,rule_key)
);
CREATE TABLE IF NOT EXISTS proofs (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, submitted_at TEXT NOT NULL,
 observed_date TEXT, verdict TEXT NOT NULL, confirmed_at TEXT, excerpt TEXT NOT NULL DEFAULT '', source_digest TEXT NOT NULL, read_mode TEXT NOT NULL DEFAULT '即時模型擷取',
 UNIQUE(task_id,source_digest)
);
CREATE TABLE IF NOT EXISTS line_bindings (
 account_id TEXT PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE, line_user_id TEXT NOT NULL,
 bound_at TEXT NOT NULL, revoked_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS unique_active_line ON line_bindings(line_user_id) WHERE revoked_at IS NULL;
CREATE TABLE IF NOT EXISTS pair_codes (
 code_hash TEXT PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 expires_at TEXT NOT NULL, consumed_at TEXT
);
CREATE TABLE IF NOT EXISTS webhook_events (id TEXT PRIMARY KEY, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notification_log (
 id INTEGER PRIMARY KEY, account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
 task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE, notice_type TEXT NOT NULL, send_date TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('pending','sent','failed','uncertain')), line_request_id TEXT,
 retry_key TEXT NOT NULL, failure_reason TEXT, claimed_at TEXT NOT NULL,
 UNIQUE(account_id,task_id,notice_type,send_date)
);
CREATE TABLE IF NOT EXISTS audit_events (
 id INTEGER PRIMARY KEY, actor_id TEXT REFERENCES accounts(id), case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
 entity_type TEXT NOT NULL, entity_id TEXT NOT NULL, action TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS qa_events (
 id INTEGER PRIMARY KEY, actor_id TEXT REFERENCES accounts(id), case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
 article_ids_json TEXT NOT NULL, data_version TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS owner_cases ON cases(owner_id);
CREATE INDEX IF NOT EXISTS case_tasks ON tasks(case_id);
