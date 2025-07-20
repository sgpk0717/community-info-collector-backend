from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum
import json

class ReportLength(str, Enum):
    simple = "simple"
    moderate = "moderate"
    detailed = "detailed"

class SearchSource(str, Enum):
    reddit = "reddit"
    threads = "threads"
    twitter = "twitter"

class SearchRequest(BaseModel):
    query: str = Field(..., description="검색할 키워드")
    sources: List[SearchSource] = Field(default=[SearchSource.reddit], description="검색할 소셜 미디어 플랫폼 목록")
    user_nickname: str = Field(..., description="사용자 닉네임")
    session_id: Optional[str] = Field(None, description="클라이언트 세션 ID")
    push_token: Optional[str] = Field(None, description="푸시 알림 토큰")
    length: ReportLength = Field(default=ReportLength.moderate, description="보고서 길이")
    schedule_yn: str = Field(default="N", pattern="^[YN]$", description="스케줄링 여부")
    schedule_period: Optional[int] = Field(None, gt=0, description="스케줄링 주기(분)")
    schedule_count: Optional[int] = Field(None, gt=0, description="스케줄링 반복 횟수")
    schedule_start_time: Optional[datetime] = Field(None, description="스케줄링 시작 시간")

class SearchResponse(BaseModel):
    status: str = Field(..., description="처리 상태")
    session_id: str = Field(..., description="세션 ID")
    query_id: str = Field(..., description="쿼리 ID")
    summary: Optional[str] = Field(None, description="요약 보고서")
    full_report: Optional[str] = Field(None, description="전체 보고서")
    posts_collected: int = Field(default=0, description="수집된 게시물 수")
    estimated_time: int = Field(..., description="예상 처리 시간(초)")
    message: Optional[str] = Field(None, description="상태 메시지")
    schedule_id: Optional[int] = Field(None, description="스케줄 ID")

class ProgressUpdate(BaseModel):
    stage: str = Field(..., description="현재 단계")
    message: str = Field(..., description="진행 메시지")
    progress: int = Field(..., ge=0, le=100, description="진행률")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="타임스탬프")