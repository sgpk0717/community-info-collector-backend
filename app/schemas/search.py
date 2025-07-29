from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union
from datetime import datetime, timedelta
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

class TimeFilter(str, Enum):
    """시간 필터 옵션"""
    hour_1 = "1h"      # 최근 1시간
    hour_3 = "3h"      # 최근 3시간
    hour_6 = "6h"      # 최근 6시간
    hour_12 = "12h"    # 최근 12시간
    day_1 = "1d"       # 최근 24시간
    day_3 = "3d"       # 최근 3일
    week_1 = "1w"      # 최근 1주일
    month_1 = "1m"     # 최근 1개월
    custom = "custom"  # 사용자 지정 기간

class SearchRequest(BaseModel):
    query: str = Field(..., description="검색할 키워드")
    sources: List[SearchSource] = Field(default=[SearchSource.reddit], description="검색할 소셜 미디어 플랫폼 목록")
    user_nickname: str = Field(..., description="사용자 닉네임")
    session_id: Optional[str] = Field(None, description="클라이언트 세션 ID")
    push_token: Optional[str] = Field(None, description="푸시 알림 토큰")
    length: ReportLength = Field(default=ReportLength.moderate, description="보고서 길이")
    
    # 시간 필터 옵션
    time_filter: Optional[TimeFilter] = Field(None, description="시간 필터 옵션")
    start_date: Optional[datetime] = Field(None, description="검색 시작 날짜 (custom 모드)")
    end_date: Optional[datetime] = Field(None, description="검색 종료 날짜 (custom 모드)")
    
    # 스케줄링 옵션
    schedule_yn: str = Field(default="N", pattern="^[YN]$", description="스케줄링 여부")
    schedule_period: Optional[int] = Field(None, gt=0, description="스케줄링 주기(분)")
    schedule_count: Optional[int] = Field(None, gt=0, description="스케줄링 반복 횟수")
    schedule_start_time: Optional[datetime] = Field(None, description="스케줄링 시작 시간")
    
    @validator('start_date', 'end_date')
    def validate_custom_dates(cls, v, values):
        """custom 모드일 때만 날짜 검증"""
        if 'time_filter' in values and values['time_filter'] == TimeFilter.custom:
            if v is None:
                raise ValueError('custom 모드에서는 시작/종료 날짜가 필요합니다')
        return v

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