from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.database_service import DatabaseService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class UserLogin(BaseModel):
    user_nickname: str

class UserRegister(BaseModel):
    user_nickname: str

@router.post("/users/login")
async def login_user(user_data: UserLogin):
    """사용자 로그인 (대소문자 구분 없음)"""
    try:
        logger.info(f"🔐 로그인 시도: {user_data.user_nickname}")
        
        db_service = DatabaseService()
        
        # 대소문자 구분 없이 검색
        result = db_service.client.table('users')\
            .select("*")\
            .ilike('nickname', user_data.user_nickname.strip())\
            .execute()
        
        if result.data and len(result.data) > 0:
            user = result.data[0]
            logger.info(f"✅ 로그인 성공: {user['nickname']}")
            return {
                "success": True,
                "user": {
                    "id": user['id'],
                    "nickname": user['nickname'],
                    "created_at": user['created_at']
                }
            }
        else:
            logger.warning(f"❌ 로그인 실패: 사용자를 찾을 수 없음 - {user_data.user_nickname}")
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그인 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/check-nickname")
async def check_nickname(nickname: str):
    """닉네임 중복 확인 (대소문자 구분 없음)"""
    try:
        logger.info(f"🔍 닉네임 중복 확인: {nickname}")
        
        db_service = DatabaseService()
        
        # 대소문자 구분 없이 검색
        result = db_service.client.table('users')\
            .select("nickname")\
            .ilike('nickname', nickname.strip())\
            .execute()
        
        is_available = len(result.data) == 0
        
        if is_available:
            logger.info(f"✅ 사용 가능한 닉네임: {nickname}")
        else:
            logger.info(f"❌ 이미 사용 중인 닉네임: {nickname} (실제 DB: {result.data[0]['nickname']})")
        
        return {"is_available": is_available}
        
    except Exception as e:
        logger.error(f"닉네임 확인 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/users/register")
async def register_user(user_data: UserRegister):
    """사용자 등록 (대소문자 구분 없이 중복 체크)"""
    try:
        logger.info(f"👤 사용자 등록 시도: {user_data.user_nickname}")
        
        db_service = DatabaseService()
        
        # 먼저 중복 확인 (대소문자 구분 없이)
        existing = db_service.client.table('users')\
            .select("nickname")\
            .ilike('nickname', user_data.user_nickname.strip())\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            logger.warning(f"❌ 등록 실패: 이미 존재하는 닉네임 - {user_data.user_nickname} (DB: {existing.data[0]['nickname']})")
            raise HTTPException(status_code=400, detail="이미 사용 중인 닉네임입니다")
        
        # 새 사용자 등록
        new_user = {
            'nickname': user_data.user_nickname.strip(),
            'approval_status': 'Y'  # 자동 승인
        }
        
        result = db_service.client.table('users').insert(new_user).execute()
        
        if result.data:
            user = result.data[0]
            logger.info(f"✅ 사용자 등록 성공: {user['nickname']}")
            return {
                "success": True,
                "user": {
                    "id": user['id'],
                    "nickname": user['nickname'],
                    "created_at": user['created_at']
                }
            }
        else:
            raise HTTPException(status_code=500, detail="사용자 등록에 실패했습니다")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 등록 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))