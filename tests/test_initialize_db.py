import os
import sqlite3
import pytest

# Helper – a thin wrapper around a plain SQLite connection.
# In the real code this would be SQLCipher, but for tests we can use the
# standard ``sqlite3`` module.
def _plain_connect(path: str):
    return sqlite3.connect(path)

@pytest.fixture(autouse=True)
def patch_encrypted_connect(monkeypatch):
    """Replace the SQLCipher helper with a plain SQLite connection for the
    duration of the test suite.
    """
    monkeypatch.setattr("initialize_db.open_encrypted_db", lambda db_path, password=None, **kwargs: _plain_connect(db_path))

def test_open_encrypted_db_returns_connection(set_db_path):
    """The helper should return a usable SQLite connection."""
    from initialize_db import open_encrypted_db
    conn = open_encrypted_db(set_db_path, password=None)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    assert cur.fetchone()[0] == 1
    conn.close()

def test_create_database_and_schema(set_db_path):
    """Create a fresh DB and verify that the expected tables/columns exist."""
    from initialize_db import create_database, get_current_columns, EXPECTED_COLUMNS
    assert not os.path.exists(set_db_path)
    create_database(set_db_path)
    assert os.path.exists(set_db_path)
    cols = get_current_columns(set_db_path)
    assert cols == EXPECTED_COLUMNS

def test_ensure_database_creates_new_file(set_db_path):
    """When no DB exists, ``ensure_database`` should create it."""
    from initialize_db import ensure_database, get_current_columns, EXPECTED_COLUMNS
    assert not os.path.exists(set_db_path)
    msg = ensure_database()
    assert msg == "Database created."
    assert os.path.exists(set_db_path)
    cols = get_current_columns(set_db_path)
    assert cols == EXPECTED_COLUMNS

def test_ensure_database_no_changes_when_up_to_date(set_db_path):
    """Running ``ensure_database`` on an up‑to‑date DB should be a no‑op."""
    from initialize_db import ensure_database
    ensure_database()
    msg = ensure_database()
    assert msg == "Database already up‑to‑date."

def test_ensure_database_adds_missing_column(set_db_path, monkeypatch):
    """Simulate a missing column and verify that the migration routine is
    invoked (the test just checks that the returned message mentions the
    missing column).
    """
    import sqlite3
    reduced_sql = """
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        content TEXT NOT NULL,
        mood INTEGER NOT NULL,
        mood_factors TEXT,
        sentiment REAL,
        entry_type TEXT NOT NULL,
        ai_insight TEXT
    );
    """
    conn = sqlite3.connect(set_db_path)
    conn.executescript(reduced_sql)
    conn.commit()
    conn.close()

    called = {"ran": False}
    def fake_migrate():
        called["ran"] = True
    monkeypatch.setitem(__import__("sys").modules, "migrate_db", type("FakeMigrate", (), {"migrate_database": fake_migrate})())
    from initialize_db import ensure_database
    msg = ensure_database()
    assert "Migration applied" in msg
    assert "weather_data" in msg
    assert called["ran"] is True
