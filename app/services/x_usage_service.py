from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.core.dependencies import get_supabase_client
from supabase import Client
import logging
import calendar

logger = logging.getLogger(__name__)

class XUsageService:
    """X API 사용량 관리 서비스 - Free 티어 최적화"""
    
    MONTHLY_LIMIT = 10000  # Free 티어 월 한도
    SAFETY_MARGIN = 0.9    # 90%만 사용 (안전 마진)
    
    def __init__(self):
        self.client: Client = get_supabase_client()
    
    def _get_current_month_key(self) -> str:
        """현재 월 키 생성 (YYYY-MM 형식)"""
        return datetime.now().strftime('%Y-%m')
    
    def _get_days_remaining_in_month(self) -> int:
        """이번 달 남은 일수 계산"""
        now = datetime.now()
        _, last_day = calendar.monthrange(now.year, now.month)
        remaining_days = last_day - now.day + 1
        return max(remaining_days, 1)  # 최소 1일
    
    async def get_current_month_usage(self, user_nickname: str = "system") -> int:
        """현재 월의 총 사용량 조회"""
        try:
            month_key = self._get_current_month_key()
            
            result = self.client.table('x_api_usage')\
                .select("tweets_read")\
                .eq('user_nickname', user_nickname)\
                .eq('month_year', month_key)\
                .execute()
            
            total_usage = sum(row['tweets_read'] for row in result.data)
            logger.info(f"📊 X API 월간 사용량: {total_usage}/{self.MONTHLY_LIMIT} ({month_key})")
            
            return total_usage
            
        except Exception as e:
            logger.error(f"❌ 월간 사용량 조회 실패: {str(e)}")
            return 0
    
    async def get_today_usage(self, user_nickname: str = "system") -> int:
        """오늘의 사용량 조회"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            month_key = self._get_current_month_key()
            
            result = self.client.table('x_api_usage')\
                .select("tweets_read, created_at")\
                .eq('user_nickname', user_nickname)\
                .eq('month_year', month_key)\
                .execute()
            
            today_usage = 0
            for row in result.data:
                created_date = row['created_at'][:10]  # YYYY-MM-DD 부분만
                if created_date == today:
                    today_usage += row['tweets_read']
            
            logger.info(f"📅 X API 오늘 사용량: {today_usage}")
            return today_usage
            
        except Exception as e:
            logger.error(f"❌ 오늘 사용량 조회 실패: {str(e)}")
            return 0
    
    async def can_use_api(self, user_nickname: str = "system", tweets_needed: int = 5, force: bool = False) -> Dict[str, Any]:
        """API 사용 가능 여부 확인"""
        try:
            # 현재 월의 사용량 조회
            current_usage = await self.get_current_month_usage(user_nickname)
            
            # 남은 일수 계산
            days_remaining = self._get_days_remaining_in_month()
            
            # 안전 한도 계산
            safe_limit = int(self.MONTHLY_LIMIT * self.SAFETY_MARGIN)
            
            # 남은 할당량 계산
            remaining_quota = safe_limit - current_usage
            
            # 일일 할당량 계산
            daily_allowance = remaining_quota / days_remaining if days_remaining > 0 else 0
            
            # 오늘 사용량
            today_usage = await self.get_today_usage(user_nickname)
            
            # 월간 한도 절대 초과 불가
            monthly_exceeded = current_usage + tweets_needed > self.MONTHLY_LIMIT
            
            # 일일 할당량 초과 여부
            daily_exceeded = today_usage + tweets_needed > daily_allowance
            
            # 안전 한도 초과 여부
            safe_exceeded = current_usage + tweets_needed > safe_limit
            
            # 사용 가능 여부 판단
            if force:
                # 강제 모드: 월간 한도만 체크
                can_use = not monthly_exceeded
                if monthly_exceeded:
                    reason = "monthly_limit_exceeded"
                elif daily_exceeded:
                    reason = "daily_limit_ignored"
                else:
                    reason = "forced"
            else:
                # 일반 모드: 모든 제한 체크
                can_use = not (monthly_exceeded or daily_exceeded or safe_exceeded)
                if monthly_exceeded:
                    reason = "monthly_limit_exceeded"
                elif daily_exceeded:
                    reason = "daily_limit_exceeded"
                elif safe_exceeded:
                    reason = "safe_limit_exceeded"
                else:
                    reason = "allowed"
            
            result = {
                "can_use": can_use,
                "reason": reason,
                "force_mode": force,
                "current_usage": current_usage,
                "monthly_limit": self.MONTHLY_LIMIT,
                "safe_limit": safe_limit,
                "remaining_quota": remaining_quota,
                "daily_allowance": int(daily_allowance),
                "today_usage": today_usage,
                "days_remaining": days_remaining,
                "tweets_needed": tweets_needed,
                "monthly_exceeded": monthly_exceeded,
                "daily_exceeded": daily_exceeded,
                "safe_exceeded": safe_exceeded
            }
            
            if can_use:
                logger.info(f"✅ X API 사용 가능 - 오늘 {today_usage}/{int(daily_allowance)}, 월간 {current_usage}/{safe_limit}")
            else:
                logger.warning(f"⚠️ X API 사용 제한 - 오늘 {today_usage}/{int(daily_allowance)}, 월간 {current_usage}/{safe_limit}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ API 사용 가능 여부 확인 실패: {str(e)}")
            return {"can_use": False, "error": str(e)}
    
    async def record_usage(self, endpoint: str, tweets_count: int, requests_count: int = 1, user_nickname: str = "system"):
        """사용량 기록"""
        try:
            if tweets_count <= 0:
                return
            
            month_key = self._get_current_month_key()
            
            # 기존 기록 조회
            result = self.client.table('x_api_usage')\
                .select("*")\
                .eq('user_nickname', user_nickname)\
                .eq('endpoint', endpoint)\
                .eq('month_year', month_key)\
                .execute()
            
            if result.data:
                # 기존 기록 업데이트
                existing = result.data[0]
                new_tweets = existing['tweets_read'] + tweets_count
                new_requests = existing['requests_made'] + requests_count
                
                self.client.table('x_api_usage')\
                    .update({
                        'tweets_read': new_tweets,
                        'requests_made': new_requests,
                        'created_at': datetime.now().isoformat()
                    })\
                    .eq('id', existing['id'])\
                    .execute()
                
                logger.info(f"📝 X API 사용량 업데이트 - {endpoint}: +{tweets_count} 트윗 (총 {new_tweets})")
            else:
                # 새 기록 생성
                self.client.table('x_api_usage')\
                    .insert({
                        'user_nickname': user_nickname,
                        'endpoint': endpoint,
                        'tweets_read': tweets_count,
                        'requests_made': requests_count,
                        'month_year': month_key,
                        'created_at': datetime.now().isoformat()
                    })\
                    .execute()
                
                logger.info(f"📝 X API 사용량 기록 생성 - {endpoint}: {tweets_count} 트윗")
                
        except Exception as e:
            logger.error(f"❌ 사용량 기록 실패: {str(e)}")
            # 사용량 기록 실패해도 서비스는 계속 동작
    
    async def get_usage_stats(self, user_nickname: str = "system") -> Dict[str, Any]:
        """사용량 통계 조회"""
        try:
            month_key = self._get_current_month_key()
            
            result = self.client.table('x_api_usage')\
                .select("*")\
                .eq('user_nickname', user_nickname)\
                .eq('month_year', month_key)\
                .execute()
            
            total_tweets = sum(row['tweets_read'] for row in result.data)
            total_requests = sum(row['requests_made'] for row in result.data)
            
            usage_by_endpoint = {}
            for row in result.data:
                endpoint = row['endpoint']
                if endpoint not in usage_by_endpoint:
                    usage_by_endpoint[endpoint] = {'tweets': 0, 'requests': 0}
                usage_by_endpoint[endpoint]['tweets'] += row['tweets_read']
                usage_by_endpoint[endpoint]['requests'] += row['requests_made']
            
            return {
                "month": month_key,
                "total_tweets": total_tweets,
                "total_requests": total_requests,
                "usage_by_endpoint": usage_by_endpoint,
                "remaining": self.MONTHLY_LIMIT - total_tweets,
                "usage_percentage": (total_tweets / self.MONTHLY_LIMIT) * 100
            }
            
        except Exception as e:
            logger.error(f"❌ 사용량 통계 조회 실패: {str(e)}")
            return {"error": str(e)}