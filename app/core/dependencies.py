from app.config import settings
import praw
import openai

def get_reddit_client() -> praw.Reddit:
    """Get Reddit client instance"""
    return praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT
    )

def setup_openai():
    """Setup OpenAI API key"""
    openai.api_key = settings.OPENAI_API_KEY