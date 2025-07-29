from fastapi import APIRouter
from typing import List, Dict, Any
from app.services.multi_platform_service import MultiPlatformService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/platforms/available", response_model=Dict[str, Any])
async def get_available_platforms():
    """현재 사용 가능한 플랫폼 목록 반환"""
    try:
        multi_service = MultiPlatformService()
        supported_platforms = multi_service.get_supported_platforms()
        
        # 플랫폼별 상태 정보
        platform_info = []
        
        # Reddit
        if multi_service.is_platform_available("reddit"):
            platform_info.append({
                "value": "reddit",
                "label": "Reddit",
                "icon": "🟢",
                "enabled": True,
                "status": "unlimited"
            })
        
        # X (Twitter)
        if multi_service.is_platform_available("x"):
            platform_info.append({
                "value": "x",
                "label": "X (Twitter)",
                "icon": "🐦",
                "enabled": True,
                "badge": "Limited",
                "status": "limited",
                "monthly_limit": 10000
            })
        
        return {
            "success": True,
            "platforms": platform_info,
            "supported": supported_platforms
        }
        
    except Exception as e:
        logger.error(f"❌ 플랫폼 정보 조회 실패: {str(e)}")
        return {
            "success": False,
            "platforms": [
                {
                    "value": "reddit",
                    "label": "Reddit",
                    "icon": "🟢",
                    "enabled": True,
                    "status": "unlimited"
                }
            ],
            "supported": ["reddit"],
            "error": str(e)
        }

@router.get("/platforms/x/usage", response_model=Dict[str, Any])
async def get_x_usage_stats():
    """X API 사용량 통계 조회"""
    try:
        multi_service = MultiPlatformService()
        
        if not multi_service.is_platform_available("x"):
            return {
                "success": False,
                "error": "X API is not available",
                "use_x_api": False
            }
        
        stats = await multi_service.x_service.get_usage_stats()
        
        return {
            "success": True,
            "usage": stats,
            "use_x_api": True
        }
        
    except Exception as e:
        logger.error(f"❌ X API 사용량 조회 실패: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/platforms/x/availability", response_model=Dict[str, Any])
async def check_x_availability():
    """X API 사용 가능 여부 및 현재 상태 확인"""
    try:
        multi_service = MultiPlatformService()
        
        if not multi_service.is_platform_available("x"):
            return {
                "success": False,
                "available": False,
                "reason": "X API is disabled",
                "use_x_api": False,
                "error": "X API service is not available. Check configuration or Python compatibility."
            }
        
        # 사용 가능 여부 확인 (기본 5개 트윗 기준)
        availability = await multi_service.x_service.usage_service.can_use_api(
            tweets_needed=10
        )
        
        return {
            "success": True,
            "available": availability["can_use"],
            "reason": availability.get("reason", "unknown"),
            "use_x_api": True,
            "current_usage": availability.get("current_usage", 0),
            "monthly_limit": availability.get("monthly_limit", 10000),
            "daily_allowance": availability.get("daily_allowance", 0),
            "today_usage": availability.get("today_usage", 0),
            "remaining_quota": availability.get("remaining_quota", 0),
            "days_remaining": availability.get("days_remaining", 0)
        }
        
    except Exception as e:
        logger.error(f"❌ X API 가용성 확인 실패: {str(e)}")
        return {
            "success": False,
            "available": False,
            "error": str(e)
        }