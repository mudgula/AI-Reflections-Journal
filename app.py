from textblob import TextBlob
import plotly.express as px
import pandas as pd
import random
import streamlit as st
from database import ReflectionDB
from ai_services import AIService
from import_db import import_legacy_db
from weather_service import WeatherService
import json
import pathlib, tempfile
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def display_daily_quote():
    if 'daily_quote' not in st.session_state:
        ai_service = AIService(provider=st.session_state.llm_provider)
        st.session_state.daily_quote = ai_service.generate_daily_quote()
    st.caption("Daily motivational quote:")
    st.markdown(f"*{st.session_state.daily_quote}*", help="Daily AI-generated inspiration")
    st.markdown("---")

def generate_prompt(mood):
    prompts = {
        5: [
            "What made today particularly wonderful?",
            "How can you recreate this positive energy tomorrow?",
            "Who would you like to share your joy with?"
        ],
        4: [
            "What went well today?",
            "What are you looking forward to?",
            "What made you smile today?"
        ],
        3: [
            "How would you describe your energy levels today?",
            "What would make tomorrow better?",
            "What's one small thing you can do for yourself?"
        ],
        2: [
            "What's challenging you right now?",
            "How could you better support yourself?",
            "What would help you feel more grounded?"
        ],
        1: [
            "What do you need right now?",
            "Who could you reach out to for support?",
            "What's one tiny step you could take to feel better?"
        ]
    }
    return random.choice(prompts[mood])


def display_weather():
    if 'weather_service' not in st.session_state:
        # Check for multiple possible key names for flexibility
        api_key = st.secrets.get("weather", {}).get("api_key") or \
                  st.secrets.get("weather", {}).get("openweather_api_key") or ""
        st.session_state.weather_service = WeatherService(api_key)
    
    zip_code = st.secrets.get("weather", {}).get("zip_code", "20871") # Default zip code
    
    if not st.session_state.weather_service.api_key:
        st.sidebar.warning("⚠️ Weather API key missing. Please add it to your secrets.")
        return None
    
    try:
        weather_info = st.session_state.weather_service.get_weather(zip_code)
        if weather_info:
            st.sidebar.markdown("---")
            st.sidebar.markdown(f"### Current Weather in {zip_code}")
            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.write(f"🌡️ **{weather_info['temperature']}°F**")
            with col2:
                st.write(f"☁️ {weather_info['description']}")
            st.sidebar.write(f"💧 Humidity: {weather_info['humidity']}%")
            return weather_info
    except Exception as e:
        st.sidebar.error(f"Weather error: {str(e)}")
    
    return None

def new_entry_page():
    st.header("New Journal Entry")
    
    # Get weather data
    weather_data = display_weather()
    
    mood = st.slider("How are you feeling today?", 1, 5, 3,
                     help="1 = Very Low, 5 = Very High")
    
    prompt = generate_prompt(mood)
    st.write("📝", prompt)
    
    mood_factors = st.multiselect(
        "What factors are influencing your mood?",
        ["Work", "Relationships", "Health", "Family", "Hobbies", "Weather", "Sleep"]
    )
    
    content = st.text_area("Your reflection", height=200)
    
    if st.button("Save Entry"):
        if content:
            # Get AI analysis first
            ai_service = AIService(provider=st.session_state.llm_provider)
            analysis = ai_service.analyze_entry(
                content,
                mood,
                ", ".join(mood_factors) if mood_factors else None
            )
            
            # Save the entry with the AI insight
            success = st.session_state.db.add_entry(
                content=content,
                mood=mood,
                mood_factors=", ".join(mood_factors) if mood_factors else None,
                ai_insight=analysis,
                weather_data=weather_data
            )
            
            if success:
                st.session_state.last_analysis = analysis
                st.success("Entry saved successfully!")
                st.rerun()
        else:
            st.error("Please write something before saving.")
    
    # Display the last analysis if it exists
    if 'last_analysis' in st.session_state:
        st.markdown("### AI Insight")
        st.markdown(st.session_state.last_analysis)
        
        # Add a button to clear the analysis
        if st.button("Clear Analysis"):
            del st.session_state.last_analysis
            st.rerun()

def edit_entry(entry):
    st.subheader("Edit Entry")
    
    # Convert mood_factors string back to list
    current_factors = entry['mood_factors'].split(', ') if entry.get('mood_factors') else []
    
    # Edit fields
    edited_mood = st.slider("Mood", 1, 5, int(entry['mood']))
    edited_factors = st.multiselect(
        "Factors",
        ["Work", "Relationships", "Health", "Family", "Hobbies", "Weather", "Sleep"],
        default=current_factors
    )
    edited_content = st.text_area("Content", entry['content'], height=200)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save Changes"):
            if edited_content:
                success = st.session_state.db.update_entry(
                    entry['id'],
                    edited_content,
                    edited_mood,
                    ", ".join(edited_factors) if edited_factors else None
                )
                if success:
                    st.success("Entry updated successfully!")
                    st.rerun()
            else:
                st.error("Content cannot be empty")
    
    with col2:
        if st.button("Cancel"):
            st.session_state.editing = None
            st.rerun()

def past_entries_page():
    st.header("Past Entries")
    
    if st.button("Refresh Entries"):
        st.rerun()
    
    entries = st.session_state.db.get_entries()
    if entries:
        for entry in entries:
            with st.expander(f"Entry from {entry['date'][:10]}"):
                st.write(f"**Mood:** {'😊' * int(entry['mood'])}")
                if entry.get('mood_factors'):
                    st.write(f"**Factors:** {entry['mood_factors']}")
                st.write(entry['content'])

                # Display AI Insight if available
                if entry.get('ai_insight'):
                    st.markdown("### AI Insight")
                    st.markdown(entry['ai_insight'])

                # Display weather if available
                if entry.get('weather_data'):
                    weather = json.loads(entry['weather_data'])
                    st.markdown("### Weather During Entry")
                    st.write(f"🌡️ {weather['temperature']}°F - {weather['description']}")
                    st.write(f"💧 Humidity: {weather['humidity']}%")

                sentiment = TextBlob(entry['content']).sentiment  # type: ignore[attr-defined]
                score = sentiment.polarity  # type: ignore[attr-defined]
                sent = ""
                if score > 0:
                    sent = "Positive"
                elif score < 0:
                    sent = "Negative"
                else:
                    sent = "Neutral"
                st.write(f"**Sentiment:** {sent}")

                # Edit and Delete buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Edit", key=f"edit_{entry['id']}"):
                        st.session_state.editing = entry
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"delete_{entry['id']}"):
                        if st.session_state.db.delete_entry(entry['id']):
                            st.success("Entry deleted successfully!")
                            st.rerun()
                            
        # Show edit form if an entry is being edited
        if hasattr(st.session_state, 'editing') and st.session_state.editing is not None:
            edit_entry(st.session_state.editing)
    else:
        st.info("No entries yet. Start journaling to see your entries here!")

def insights_page():
    st.header("Insights & Analytics")
    raw_entries = st.session_state.db.get_entries(limit=100)
    entries = pd.DataFrame(raw_entries) if raw_entries else pd.DataFrame()
    
    if not entries.empty:
        fig_mood = px.line(entries, x='date', y='mood',
                          title='Mood Trends Over Time')
        st.plotly_chart(fig_mood)

        fig_sentiment = px.scatter(entries, x='mood', y='sentiment',
                                 title='Mood vs. Sentiment Analysis')
        st.plotly_chart(fig_sentiment)

        if entries['mood_factors'].notna().any():
            factors = entries['mood_factors'].str.split(', ').explode()
            factor_counts = factors.value_counts()
            fig_factors = px.bar(factor_counts, title='Common Mood Factors')
            st.plotly_chart(fig_factors)
    else:
        st.info("Add some journal entries to see insights!")

def import_legacy_page():
    st.header("Import Legacy Database")
    legacy_file = st.file_uploader(
        "Import legacy SQLite DB",
        type=["db"],
        help="Import legacy database",
        key="legacy_db_uploader",
    )
    if st.button("Import legacy database", key="legacy_import_btn"):
        if legacy_file is not None:
            tmp_path = pathlib.Path(tempfile.gettempdir()) / legacy_file.name
            with open(tmp_path, "wb") as f:
                f.write(legacy_file.getbuffer())
            count = import_legacy_db(str(tmp_path), st.session_state.db)
            if count > 0:
                st.success(f"Imported {count} entries from legacy DB.")
                # Delete temporary file after successful import
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception as e:
                    logger.error(f"Failed to delete temporary file {tmp_path}: {e}")
            else:
                st.warning("No entries were imported.")
        else:
            st.warning("Please select a legacy DB file first.")

def main():
    st.set_page_config(page_title="AI Reflection Journal", layout="wide")
    
    # Prompt for encrypted DB password and store it in session state
    if not st.session_state.get('logged_in', False):
        login_placeholder = st.empty()
        with login_placeholder.form("login_form"):
            pwd = st.text_input('Database password', type='password')
            submitted = st.form_submit_button('Login')
            if submitted:
                if not pwd:
                    st.warning('Please enter the database password to continue.')
                else:
                    st.session_state.db = ReflectionDB(password=pwd)
                    st.session_state.logged_in = True
                    login_placeholder.empty()
                    st.rerun()
    else:
        # Database already initialized and user is logged in
        pass
    
    st.title("AI Reflection Journal")
    
    # Add LLM provider selection
    with st.sidebar:
        st.sidebar.title("Settings")
        llm_provider = st.sidebar.selectbox(
            "Select LLM Provider",
            options=["ollama"],
            index=0,
            help="Ollama only option for now. Public LLM providers cannot be trusted with personal info."
        )
        
        # Store the selected provider in session state
        if 'llm_provider' not in st.session_state or st.session_state.llm_provider != llm_provider:
            st.session_state.llm_provider = llm_provider
            # Clear any existing AI service instance
            if 'ai_service' in st.session_state:
                del st.session_state.ai_service
            if 'daily_quote' in st.session_state:
                del st.session_state.daily_quote
    
    display_daily_quote()  # Add the daily quote right under the title
    
    # Replace radio buttons with sidebar links
    st.sidebar.title("Navigation")
    
    # Using emojis as icons
    pages = {
        "New Entry": "📝",
        "Past Entries": "📚",
        "Insights": "📊",
        "Legacy DB Import": "⬇️"
    }
    
    # Create navigation links with icons
    for page_name, icon in pages.items():
        if st.sidebar.button(f"{icon} {page_name}", use_container_width=True):
            st.session_state.page = page_name
            st.rerun()

    # Set default page if not set
    
    # Set default page if not set
    if 'page' not in st.session_state:
        st.session_state.page = "New Entry"
    
    # Display the selected page
    if st.session_state.page == "New Entry":
        new_entry_page()
    elif st.session_state.page == "Past Entries":
        past_entries_page()
    elif st.session_state.page == "Insights":
        insights_page()
    elif st.session_state.page == "Legacy DB Import":
        import_legacy_page()


if __name__ == "__main__":
    logger.info("Starting Reflection Journal App...")
    main()