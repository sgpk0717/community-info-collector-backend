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