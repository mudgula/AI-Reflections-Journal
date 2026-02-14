import os
from initialize_db import open_encrypted_db
import streamlit as st
import logging
from sqlalchemy import create_engine, text
from textblob import TextBlob
from datetime import datetime
import json

# Set up logging
logger = logging.getLogger(__name__)

class ReflectionDB:
    def __init__(self, password: str | None = None):
        try:
            self.db_path = os.getenv("REFLECTIONS_DB_PATH") or os.path.join(os.getcwd(), 'data', 'reflections.db')
            # Ensure the data directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self.password = password
            logger.info(f"Connecting to database at: {self.db_path}")
            self.conn = open_encrypted_db(self.db_path, password)
            # SQLAlchemy engine using the same encrypted connection creator
            self.engine = create_engine('sqlite://', creator=lambda: open_encrypted_db(self.db_path, self.password))
            logger.info("Database connection established")
            self.create_tables()
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            st.error(f"Database initialization error: {str(e)}")
    
    def create_tables(self):
        try:
            logger.info("Creating tables if they don't exist...")
            cursor = self.conn.cursor()
            cursor.execute('''
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
                )
            ''')
            self.conn.commit()
            logger.info("Tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {str(e)}")
            st.error(f"Error creating tables: {str(e)}")

    def update_entry(self, entry_id, content, mood, mood_factors, ai_insight=None):
        try:
            sentiment = TextBlob(content).sentiment.polarity  # type: ignore[attr-defined]
            conn = open_encrypted_db(self.db_path, self.password)
            cursor = conn.cursor()
            # Preserve existing entry_type (NOT NULL)
            cursor.execute('SELECT entry_type FROM entries WHERE id = ?', (entry_id,))
            row = cursor.fetchone()
            entry_type = row[0] if row else "text"
            cursor.execute('''
                UPDATE entries
                SET content = ?, mood = ?, mood_factors = ?, sentiment = ?, ai_insight = ?, entry_type = ?
                WHERE id = ?
            ''', (content, mood, mood_factors, sentiment, ai_insight, entry_type, entry_id))
            conn.commit()
            logger.info(f"Entry {entry_id} updated successfully")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating entry: {str(e)}")
            st.error(f"Error updating entry: {str(e)}")
            return False

    def delete_entry(self, entry_id):
        try:
            conn = open_encrypted_db(self.db_path, self.password)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
            conn.commit()
            logger.info(f"Entry {entry_id} deleted successfully")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error deleting entry: {str(e)}")
            st.error(f"Error deleting entry: {str(e)}")
            return False
    
    def add_entry(self, content, mood, mood_factors, ai_insight=None, weather_data=None, entry_type="text"):
        try:
            conn = open_encrypted_db(self.db_path, self.password)
            sentiment = TextBlob(content).sentiment.polarity # type: ignore[attr-defined]
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO entries (
                    date, content, mood, mood_factors,
                    sentiment, entry_type, ai_insight, weather_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(), content, mood, mood_factors,
                sentiment, entry_type, ai_insight,
                json.dumps(weather_data) if weather_data else None
            ))
            conn.commit()

            cursor.execute('SELECT COUNT(*) FROM entries')
            count = cursor.fetchone()[0]
            logger.info(f"Total entries after insert: {count}")
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding entry: {str(e)}")
            st.error(f"Error saving entry: {str(e)}")
            return False
    
    def get_entries(self, limit=10):
        try:
            # Use SQLAlchemy engine to execute query and fetch results
            query = 'SELECT * FROM entries ORDER BY date DESC LIMIT :limit'
            logger.info(f"Fetching entries with query: {query}, limit: {limit}")
            with self.engine.connect() as conn:
                result = conn.execute(text(query), {"limit": limit})
                rows = result.fetchall()
            columns = result.keys()
            # Convert to list of dicts for easier consumption without pandas
            entries = [dict(zip(columns, row)) for row in rows]
            logger.info(f"Retrieved {len(entries)} entries")
            return entries
        except Exception as e:
            logger.error(f"Error getting entries: {str(e)}")
            st.error(f"Error retrieving entries: {str(e)}")
            return [] 