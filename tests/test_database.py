import sys, os
import pytest
import sqlite3
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import ReflectionDB
from initialize_db import open_encrypted_db

# ------------------------------------------------
# Patch the encrypted helper to use a plain SQLite connection for testing.
# ------------------------------------------------
@pytest.fixture(autouse=True)
def patch_encrypted_connect(monkeypatch):
    monkeypatch.setattr("database.open_encrypted_db", lambda db_path, pwd=None: sqlite3.connect(db_path))

def test_reflectiondb_initialises_and_creates_tables(set_db_path):
    """Construction should create the DB and the ``entries`` table."""
    db = ReflectionDB()
    assert os.path.exists(set_db_path)
    cur = db.conn.cursor()
    cur.execute("PRAGMA table_info(entries)")
    cols = {row[1] for row in cur.fetchall()}
    expected = {
        "id",
        "date",
        "content",
        "mood",
        "mood_factors",
        "sentiment",
        "entry_type",
        "ai_insight",
        "weather_data",
    }
    assert cols == expected
    db.conn.close()

def test_add_and_get_entry(set_db_path):
    db = ReflectionDB()
    success = db.add_entry(
        content="Test entry",
        mood=3,
        mood_factors="Work,Health",
        ai_insight="Nice insight",
        weather_data={"temperature": 70, "description": "Sunny", "humidity": 30},
    )
    assert success
    df = db.get_entries(limit=10)
    assert not df.empty
    row = df.iloc[0]
    assert row["content"] == "Test entry"
    assert row["mood"] == 3
    assert "Work" in row["mood_factors"]
    assert row["ai_insight"] == "Nice insight"
    db.conn.close()

def test_update_entry(set_db_path):
    db = ReflectionDB()
    db.add_entry(content="Original", mood=2, mood_factors="Sleep", ai_insight="Old")
    entry_id = db.get_entries().iloc[0]["id"]
    ok = db.update_entry(
        entry_id,
        content="Updated",
        mood=5,
        mood_factors="Work,Health",
        ai_insight="New insight",
    )
    assert ok
    row = db.get_entries().iloc[0]
    assert row["content"] == "Updated"
    assert row["mood"] == 5
    assert "Work" in row["mood_factors"]
    assert row["ai_insight"] == "New insight"
    db.conn.close()

def test_delete_entry(set_db_path):
    db = ReflectionDB()
    db.add_entry(content="Will be deleted", mood=1, mood_factors=None)
    entry_id = db.get_entries().iloc[0]["id"]
    ok = db.delete_entry(entry_id)
    assert ok
    df = db.get_entries()
    assert df.empty
    db.conn.close()
