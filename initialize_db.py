import os
import argparse
import logging
from typing import Set
from sqlcipher3 import dbapi2 as sqlcipher

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def open_encrypted_db(db_path: str, password: str | None = None) -> sqlcipher.Connection: # type: ignore[attr-defined]
    """Open a SQLite (SQLCipher) connection and apply the encryption key if provided.

    If ``password`` is ``None`` the connection is opened without a key (useful for testing).
    """
    conn = sqlcipher.connect(db_path) # type: ignore[attr-defined]
    if password:
        conn.execute(f"PRAGMA key = '{password}';")
    return conn


def get_current_columns(db_path: str) -> Set[str]:
    """Return a set of column names for the ``entries`` table.

    If the table does not exist the returned set will be empty.
    """
    # Prefer the password stored in Streamlit session state if available; fall back to env var
    try:
        import streamlit as st
        password = getattr(st.session_state, "db_password", None)
    except Exception:
        password = None
    if not password:
        password = os.getenv("REFLECTIONS_DB_PASSWORD")
    # If still no password, prompt the user interactively
    if not password:
        try:
            password = input("Enter database password (leave empty for none): ") or None
        except Exception:
            password = None
    conn = open_encrypted_db(db_path, password)
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(entries)")
        cols = {row[1] for row in cur.fetchall()}
    finally:
        conn.close()
    return cols


# --------------------------------------------------------------------
# Schema definition (canonical source of truth)
# --------------------------------------------------------------------
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    content TEXT NOT NULL,
    mood INTEGER NOT NULL,
    mood_factors TEXT,
    sentiment REAL,
    entry_type TEXT NOT NULL,
    ai_insight TEXT,
    weather_data TEXT
);
"""

# Expected column names – must match the CREATE_TABLE_SQL definition exactly
EXPECTED_COLUMNS: Set[str] = {
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


def create_database(db_path: str) -> None:
    """Create a fresh reflections.db file with the full schema."""
    password = os.getenv("REFLECTIONS_DB_PASSWORD")
    conn = open_encrypted_db(db_path, password)
    cur = conn.cursor()
    try:
        cur.executescript(CREATE_TABLE_SQL)
        conn.commit()
        logger.info("Database file created with full schema.")
    finally:
        conn.close()


def ensure_database() -> str:
    """Ensure a usable reflections.db exists.

    Returns a human‑readable status message that the CLI can print.
    """
    # Allow an environment variable to override the location – useful for testing
    # Ensure the data directory exists
    os.makedirs(os.path.join(os.getcwd(), "data"), exist_ok=True)
    db_path = os.getenv("REFLECTIONS_DB_PATH") or os.path.join(os.getcwd(), "data", "reflections.db")

    if not os.path.exists(db_path):
        logger.info("Database file not found – creating new DB at %s", db_path)
        create_database(db_path)
        return "Database created."

    # DB file exists – inspect schema
    current_columns = get_current_columns(db_path)
    if not current_columns:
        # The file exists but the 'entries' table is missing – treat as a fresh init
        logger.warning("Database file exists but 'entries' table missing – recreating tables.")
        create_database(db_path)
        return "Database created (missing table detected)."

    if current_columns == EXPECTED_COLUMNS:
        logger.info("Database already contains the expected schema.")
        return "Database already up‑to‑date."

    # Some columns are missing – run migrations
    missing = EXPECTED_COLUMNS - current_columns
    logger.info("Database missing columns %s – invoking migration.", missing)
    # Import migrate_db lazily to avoid circular import / unnecessary load
    import importlib
    migrate_mod = importlib.import_module("migrate_db")
    migrate_mod.migrate_database()
    return f"Migration applied – added columns: {', '.join(sorted(missing))}."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize or migrate the reflections SQLite database.")
    parser.add_argument("--password", help="Password (encryption key) for the SQLite database")
    args = parser.parse_args()
    # Prompt for password if not supplied via flag
    if not args.password:
        try:
            import getpass
            pwd = getpass.getpass('Enter database password (leave blank for none): ')
        except Exception:
            pwd = None
    else:
        pwd = args.password
    if pwd:
        os.environ["REFLECTIONS_DB_PASSWORD"] = pwd
    try:
        message = ensure_database()
        print(message)
    except Exception as exc:  # pragma: no cover – unexpected errors are re‑raised after logging
        logger.error("Failed to initialise database: %s", exc)
        raise