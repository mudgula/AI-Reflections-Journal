import sqlite3
import logging
from typing import Any

# Import the ReflectionDB class for type hinting and to access the existing encrypted DB connection
from database import ReflectionDB

logger = logging.getLogger(__name__)


def import_legacy_db(legacy_path: str, db: ReflectionDB) -> int:
    """Import entries from an unencrypted legacy SQLite database.

    Parameters
    ----------
    legacy_path: str
        Path to the legacy (plain‑text) SQLite ``.db`` file.
    db: ReflectionDB
        The current encrypted database instance. Its ``conn`` attribute is an
        open connection that will be used for the insert statements.

    Returns
    -------
    int
        Number of rows successfully imported.
    """
    imported = 0
    try:
        # Open the legacy database (no encryption)
        legacy_conn = sqlite3.connect(legacy_path)
        legacy_cur = legacy_conn.cursor()
        legacy_cur.execute(
            "SELECT date, content, mood, mood_factors, sentiment, entry_type, ai_insight, weather_data "
            "FROM entries"
        )
        rows = legacy_cur.fetchall()
        legacy_conn.close()
    except Exception as e:
        logger.error(f"Failed to read legacy database '{legacy_path}': {e}")
        return 0

    # Insert each row into the encrypted database using the existing connection
    try:
        cur = db.conn.cursor()
        for row in rows:
            try:
                cur.execute(
                    """
                    INSERT INTO entries (
                        date, content, mood, mood_factors,
                        sentiment, entry_type, ai_insight, weather_data
                    ) VALUES (?,?,?,?,?,?,?,?)
                    """,
                    row,
                )
                imported += 1
            except Exception as row_err:
                logger.error(f"Failed to import row {row}: {row_err}")
        db.conn.commit()
    except Exception as e:
        logger.error(f"Error during import into encrypted DB: {e}")
        return imported

    logger.info(f"Imported {imported} rows from legacy DB '{legacy_path}'.")
    return imported
