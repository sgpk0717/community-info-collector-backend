from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

class KeywordInfo(BaseModel):
    keyword: str
    translated_keyword: Optional[str] = None
    posts_found: int = 0
    sample_titles: List[str] = []

class Report(BaseModel):
    id: UUID
    created_at: datetime
    user_nickname: Optional[str]
    query_text: str
    summary: Optional[str]
    full_report: Optional[str]
    posts_collected: int = 0
    report_length: str = "moderate"
    session_id: Optional[str]
    report_char_count: Optional[int] = Field(None, description="보고서 총 글자수")

class ReportCreate(BaseModel):
    user_nickname: Optional[str]
    query_text: str
    summary: Optional[str]
    full_report: Optional[str]
    posts_collected: int = 0
    report_length: str = "moderate"
    session_id: Optional[str]

class ReportList(BaseModel):
    reports: List[Report]
    total: int