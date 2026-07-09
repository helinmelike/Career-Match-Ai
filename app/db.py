import sqlite3

DB_FILE = "kariyerai.db"


def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            cv_text TEXT,
            cv_analysis TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS employers (
            id TEXT PRIMARY KEY,
            company_name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            employer_id TEXT,
            title TEXT,
            company TEXT,
            text TEXT,
            job_analysis TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS match_cache (
            candidate_id TEXT,
            job_id TEXT,
            score REAL,
            explanation TEXT,
            computed_at TEXT,
            PRIMARY KEY (candidate_id, job_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            candidate_id TEXT,
            job_id TEXT,
            created_at TEXT,
            PRIMARY KEY (candidate_id, job_id)
        )
    """)
    # Eski veritabanlarinda bu kolonlar olmayabilir, varsa hata yutuluyor.
    for stmt in (
        "ALTER TABLE jobs ADD COLUMN job_analysis TEXT",
        "ALTER TABLE jobs ADD COLUMN updated_at TEXT",
        "ALTER TABLE jobs ADD COLUMN employer_id TEXT",
        "ALTER TABLE candidates ADD COLUMN updated_at TEXT",
        "ALTER TABLE candidates ADD COLUMN phone TEXT",
        "ALTER TABLE candidates ADD COLUMN linkedin TEXT",
        "ALTER TABLE candidates ADD COLUMN github TEXT",
        "ALTER TABLE candidates ADD COLUMN location TEXT",
        "ALTER TABLE candidates ADD COLUMN password_hash TEXT",
    ):
        try:
            conn.execute(stmt)
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()
