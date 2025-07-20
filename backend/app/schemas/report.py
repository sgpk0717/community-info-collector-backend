from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

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