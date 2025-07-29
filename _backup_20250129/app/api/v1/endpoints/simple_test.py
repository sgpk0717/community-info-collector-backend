from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from app.services.memory_storage import memory_storage
from app.services.llm_service import LLMService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class SimpleSearchRequest(BaseModel):
    query: str
    user_nickname: str

class SimpleSearchResponse(BaseModel):
    success: bool
    message: str
    report_id: str
    summary: str

@router.post("/simple-search", response_model=SimpleSearchResponse)
async def simple_search(request: SimpleSearchRequest):
    """간단한 검색 및 보고서 생성 (테스트용)"""
    try:
        logger.info(f"🔍 간단한 검색 요청: {request.query} by {request.user_nickname}")
        
        # 사용자 생성 (없으면)
        user = memory_storage.get_user(request.user_nickname)
        if not user:
            memory_storage.create_user(request.user_nickname)
        
        # 더미 게시물 데이터
        dummy_posts = [
            {
                "id": "test1",
                "title": f"Test post about {request.query}",
                "selftext": f"This is a test post discussing {request.query}. It contains relevant information.",
                "score": 150,
                "num_comments": 25,
                "subreddit": "technology",
                "author": "testuser1",
                "created_utc": "2025-01-16T10:00:00Z",
                "url": "https://reddit.com/r/technology/test1"
            },
            {
                "id": "test2", 
                "title": f"Another perspective on {request.query}",
                "selftext": f"Here's another view about {request.query}. Different opinions are shared here.",
                "score": 89,
                "num_comments": 12,
                "subreddit": "technology",
                "author": "testuser2",
                "created_utc": "2025-01-16T09:30:00Z",
                "url": "https://reddit.com/r/technology/test2"
            }
        ]
        
        # LLM 서비스로 보고서 생성
        llm_service = LLMService()
        
        # 간단한 보고서 생성
        simple_report = f"""# {request.query} 분석 보고서

## 핵심 요약
'{request.query}'에 대한 커뮤니티 반응을 분석한 결과, 다음과 같은 주요 의견들이 발견되었습니다.

## 주요 토픽
1. **기술적 측면**: 사용자들은 주로 기술적 가능성에 대해 논의하고 있습니다.
2. **사회적 영향**: 해당 주제가 사회에 미칠 영향에 대한 의견이 다양합니다.

## 커뮤니티 반응
- 긍정적 반응: 60%
- 부정적 반응: 25%
- 중립적 반응: 15%

## 종합 분석
전반적으로 '{request.query}'에 대한 커뮤니티의 관심이 높으며, 다양한 관점에서 활발한 토론이 이루어지고 있습니다.

*이 보고서는 테스트용 더미 데이터로 생성되었습니다.*
"""
        
        summary = f"'{request.query}'에 대한 커뮤니티 분석 결과, 전반적으로 긍정적인 반응(60%)을 보이고 있으며, 기술적 측면과 사회적 영향에 대한 다양한 의견이 제시되고 있습니다."
        
        # 보고서 저장
        report_id = memory_storage.save_report(
            user_nickname=request.user_nickname,
            query=request.query,
            summary=summary,
            full_report=simple_report,
            posts_collected=len(dummy_posts)
        )
        
        logger.info(f"✅ 간단한 보고서 생성 완료: {report_id}")
        
        return SimpleSearchResponse(
            success=True,
            message="보고서 생성 완료",
            report_id=report_id,
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"❌ 간단한 검색 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")

@router.get("/reports/{user_nickname}")
async def get_user_reports(user_nickname: str):
    """사용자 보고서 목록 조회"""
    try:
        reports = memory_storage.get_user_reports(user_nickname)
        
        return {
            "success": True,
            "reports": reports,
            "count": len(reports)
        }
        
    except Exception as e:
        logger.error(f"❌ 보고서 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"보고서 조회 실패: {str(e)}")

@router.get("/reports/detail/{report_id}")
async def get_report_detail(report_id: str):
    """보고서 상세 조회"""
    try:
        report = memory_storage.get_report_by_id(report_id)
        
        if not report:
            raise HTTPException(status_code=404, detail="보고서를 찾을 수 없습니다")
        
        return {
            "success": True,
            "report": report
        }
        
    except Exception as e:
        logger.error(f"❌ 보고서 상세 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"보고서 상세 조회 실패: {str(e)}")

@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "message": "Simple test API is working!",
        "stored_reports": len(memory_storage.reports),
        "stored_users": len(memory_storage.users)
    }