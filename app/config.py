from pydantic import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Community Info Collector API"
    APP_VERSION: str = "2.0.0"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # API settings
    API_V1_STR: str = "/api/v1"
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8081", "https://community-info-collector-backend.onrender.com"]
    
    # Reddit API
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "community-info-collector/2.0"
    
    # OpenAI API
    OPENAI_API_KEY: str = ""
    
    class Config:
        case_sensitive = True

settings = Settings()