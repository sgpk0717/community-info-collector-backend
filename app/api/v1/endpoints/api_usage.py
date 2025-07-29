from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = APIRouter()

# X API 사용량 상태를 메모리에 저장 (실제로는 DB나 Redis 사용 권장)
x_api_usage = {
    "used": 0,
    "limit": 50000,
    "reset_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
}

@router.get("/x-api-usage", response_model=Dict[str, Any])
async def get_x_api_usage():
    """X(Twitter) API 사용량 정보 조회"""
    try:
        logger.info("X API 사용량 조회 요청")
        
        # 실제로는 X API 사용량을 추적하는 서비스나 DB에서 가져와야 함
        # 여기서는 시뮬레이션된 데이터 반환
        return {
            "used": x_api_usage["used"],
            "limit": x_api_usage["limit"],
            "reset_date": x_api_usage["reset_date"],
            "percentage": round((x_api_usage["used"] / x_api_usage["limit"]) * 100, 2)
        }
        
    except Exception as e:
        logger.error(f"X API 사용량 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="X API 사용량 조회에 실패했습니다")

@router.post("/x-api-usage/increment", response_model=Dict[str, Any])
async def increment_x_api_usage(count: int = 1):
    """X API 사용량 증가 (내부 서비스용)"""
    try:
        x_api_usage["used"] += count
        logger.info(f"X API 사용량 증가: {count}개 (현재: {x_api_usage['used']}/{x_api_usage['limit']})")
        
        return {
            "used": x_api_usage["used"],
            "limit": x_api_usage["limit"],
            "reset_date": x_api_usage["reset_date"],
            "percentage": round((x_api_usage["used"] / x_api_usage["limit"]) * 100, 2)
        }
        
    except Exception as e:
        logger.error(f"X API 사용량 업데이트 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="X API 사용량 업데이트에 실패했습니다")