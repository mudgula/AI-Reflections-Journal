import logging
import random
from langchain_ollama.llms import OllamaLLM
import streamlit as st
from langchain_core.prompts import PromptTemplate
import urllib.request, json

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, provider="ollama"):
        try:
            self.provider = provider
            # Get settings from .streamlit/secrets.toml
            llm_secrets = st.secrets.get("llm", {})
            ollama_model = llm_secrets.get("ollama_model", "llama3.2:1b")
            
            if provider == "ollama":
                self.llm = OllamaLLM(
                    model=ollama_model,
                    base_url="http://localhost:11434",
                )
            logger.info(f"AI Service initialized successfully with {provider}")
        except Exception as e:
            logger.error(f"Error initializing AI service: {str(e)}")
            self.llm = None

    def generate_daily_quote(self):
        # Primary method: fetch a random quote from ZenQuotes API
        try:
            import requests  # Imported here to avoid unnecessary dependency if not used
            response = requests.get('https://zenquotes.io/api/random', timeout=5)
            response.raise_for_status()
            data = response.json()
            # Expected format: [{"q": "Quote", "a": "Author", ...}]
            if isinstance(data, list) and data:
                quote = data[0].get('q')
                author = data[0].get('a')
                if quote and author:
                    return f'"{quote}" - {author}', "ZenQuotes"
        except Exception as api_err:
            logger.warning(f"ZenQuotes API failed ({api_err}); falling back to LLM.")
        # Fallback: use the LLM to generate a quote
        try:
            if not self.llm:
                raise Exception("LLM not initialized")
            prompt = PromptTemplate(
                input_variables=[],
                template="""Generate an inspiring and thoughtful quote about self-reflection, mindfulness, or personal growth.
                The quote should be brief (max 2-3 sentences) and include the author. The quote must be from a real person and not made up.
                No Steve Jobs quotes.
                Format: \"Quote\" - Author"""
            )
            llm_response = self.llm.invoke(prompt.format())
            return llm_response.strip(), "AI"
        except Exception as e:
            logger.error(f"Error generating quote via LLM: {str(e)}")
            fallback_quotes = [
                '"The only journey is the one within." - Rainer Maria Rilke',
                '"Know thyself." - Socrates',
                '"Self-awareness is the key to self-mastery." - Gretchen Rubin',
                '"Reflection is the lamp of the heart." - Al-Ghazali'
            ]
            return random.choice(fallback_quotes), "Fallback"


    def analyze_entry(self, content, mood, mood_factors):
        try:
            if not self.llm:
                raise Exception("LLM not initialized")

            prompt = PromptTemplate(
                input_variables=["content", "mood", "factors"],
                template="""Act as an empathetic therapist or personal development coach. 
                Analyze the following journal entry and provide thoughtful insights, validation, 
                and gentle suggestions for growth (3-4 sentences max). Finally, ask one open-ended
                question intended to inspire reflection.

                Journal Entry: {content}
                Mood Level (1-5): {mood}
                Influencing Factors: {factors}

                Provide your response in this format:
                🤔 [Your therapeutic insight and suggestion here]"""
            )
            
            response = self.llm.invoke(
                prompt.format(
                    content=content,
                    mood=mood,
                    factors=mood_factors if mood_factors else "None specified"
                )
            )
            return response.strip()  # String from Ollama
            
        except Exception as e:
            logger.error(f"Error analyzing entry: {str(e)}")
            return "I'm currently unable to provide insights, but I appreciate you sharing your thoughts. Consider reflecting on what you've written and be kind to yourself. 🌱"