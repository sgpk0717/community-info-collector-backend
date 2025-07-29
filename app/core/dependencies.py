from supabase import create_client, Client
from app.config import settings
import praw
from openai import OpenAI
import httpx
import ssl
import warnings
import urllib3

# SSL 경고 무시
warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)

def get_supabase_client() -> Client:
    """Get Supabase client instance"""
    # SSL 인증서 검증을 비활성화한 httpx 클라이언트 생성
    import os
    os.environ['HTTPX_SSL_VERIFY'] = 'false'
    
    return create_client(
        settings.SUPABASE_URL, 
        settings.SUPABASE_SERVICE_KEY
    )

def get_reddit_client() -> praw.Reddit:
    """Get Reddit client instance"""
    return praw.Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT
    )

def get_openai_client() -> OpenAI:
    """Get OpenAI client instance"""
    return OpenAI(api_key=settings.OPENAI_API_KEY)