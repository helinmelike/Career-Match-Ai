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
            cv_text TEXT,
            cv_analysis TEXT,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            text TEXT,
            job_analysis TEXT,
            created_at TEXT
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
    try:
        conn.execute("ALTER TABLE jobs ADD COLUMN job_analysis TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
