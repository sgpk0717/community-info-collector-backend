from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Community Info Collector API"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # API settings
    API_V1_STR: str = "/api/v1"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]  # 모든 origin 허용 (디버깅용)
    
    # Reddit API
    REDDIT_CLIENT_ID: str = os.getenv("REDDIT_CLIENT_ID", "")
    REDDIT_CLIENT_SECRET: str = os.getenv("REDDIT_CLIENT_SECRET", "")
    REDDIT_USER_AGENT: str = "community-info-collector/2.0"
    
    # OpenAI API
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    model_config = {"case_sensitive": True}

settings = Settings()