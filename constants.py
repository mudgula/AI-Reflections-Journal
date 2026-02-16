"""Application constants for mood and other configurable values."""

# Mood scale configuration
MOOD_MIN = 1
MOOD_MAX = 5
MOOD_DEFAULT = 3
MOOD_SCALE = {
    1: "Very Low",
    2: "Low",
    3: "Neutral",
    4: "High",
    5: "Very High",
}

# Mood factors options
MOOD_FACTORS = ["Work", "Relationships", "Health", "Family", "Hobbies", "Weather", "Sleep"]

# Default location settings
DEFAULT_ZIP_CODE = "20871"

# Database configuration
DATABASE_DIR = "data"
DATABASE_NAME = "reflections.db"
DATABASE_PATH = f"{DATABASE_DIR}/{DATABASE_NAME}"
