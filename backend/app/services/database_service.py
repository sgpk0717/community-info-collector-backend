from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime
from supabase import Client
from app.core.dependencies import get_supabase_client
from app.core.exceptions import SupabaseException
from app.schemas.report import ReportCreate
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.client: Client = get_supabase_client()
    
    async def get_or_create_user(self, user_nickname: str) -> Dict[str, Any]:
        """사용자 조회 또는 생성"""
        try:
            # 먼저 사용자 조회 (nickname 컬럼 사용)
            result = self.client.table('users').select("*").eq('nickname', user_nickname).execute()
            
            if result.data:
                return result.data[0]
            
            # 사용자가 없으면 생성
            new_user = {
                'nickname': user_nickname,
                'approval_status': 'Y',  # 기본값으로 승인 상태
                'created_at': datetime.now().isoformat(),
                'last_access': datetime.now().isoformat()
            }
            
            result = self.client.table('users').insert(new_user).execute()
            
            if result.data:
                return result.data[0]
            else:
                raise SupabaseException("Failed to create user")
                
        except Exception as e:
            logger.error(f"Database error in get_or_create_user: {str(e)}")
            raise SupabaseException(f"Database operation failed: {str(e)}")
    
    async def save_report(self, report_data: ReportCreate) -> str:
        """보고서 저장"""
        try:
            report_dict = report_data.model_dump()
            report_dict['id'] = str(uuid4())
            report_dict['created_at'] = datetime.now().isoformat()
            
            result = self.client.table('reports').insert(report_dict).execute()
            
            if result.data:
                return result.data[0]['id']
            else:
                raise SupabaseException("Failed to save report")
                
        except Exception as e:
            logger.error(f"Database error in save_report: {str(e)}")
            raise SupabaseException(f"Failed to save report: {str(e)}")
    
    async def get_user_reports(self, user_nickname: str) -> List[Dict[str, Any]]:
        """사용자의 보고서 목록 조회"""
        try:
            result = self.client.table('reports')\
                .select("*")\
                .ilike('user_nickname', user_nickname)\
                .order('created_at', desc=True)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Database error in get_user_reports: {str(e)}")
            raise SupabaseException(f"Failed to get reports: {str(e)}")
    
    async def create_schedule(self, schedule_data: Dict[str, Any]) -> int:
        """스케줄 생성"""
        try:
            schedule_data['created_at'] = datetime.now().isoformat()
            schedule_data['status'] = 'active'
            schedule_data['completed_reports'] = 0
            schedule_data['is_executing'] = False
            
            if 'sources' in schedule_data and isinstance(schedule_data['sources'], list):
                schedule_data['sources'] = schedule_data['sources']
            
            result = self.client.table('schedules').insert(schedule_data).execute()
            
            if result.data:
                return result.data[0]['id']
            else:
                raise SupabaseException("Failed to create schedule")
                
        except Exception as e:
            logger.error(f"Database error in create_schedule: {str(e)}")
            raise SupabaseException(f"Failed to create schedule: {str(e)}")
    
    async def save_report_links(self, report_id: str, footnote_mapping: List[Dict[str, Any]]) -> None:
        """보고서 각주 링크 저장"""
        try:
            if not footnote_mapping:
                logger.info("📝 저장할 각주 링크가 없습니다")
                return
            
            # 각주 링크 데이터 준비
            links_data = []
            for link in footnote_mapping:
                # created_utc를 Unix timestamp로 변환
                created_utc_value = None
                if link.get('created_utc'):
                    try:
                        # ISO 문자열을 datetime으로 파싱 후 timestamp로 변환
                        dt = datetime.fromisoformat(link['created_utc'].replace('Z', '+00:00'))
                        created_utc_value = dt.timestamp()
                    except:
                        logger.warning(f"created_utc 변환 실패: {link['created_utc']}")
                
                link_data = {
                    'report_id': report_id,
                    'footnote_number': link['footnote_number'],
                    'url': link['url'],
                    'title': link['title'],
                    'score': link['score'],
                    'comments': link['comments'],
                    'created_utc': created_utc_value,  # Unix timestamp로 저장
                    'subreddit': link['subreddit'],
                    'author': link['author'],
                    'position_in_report': link['position_in_report'],
                    'created_at': datetime.now().isoformat()
                }
                links_data.append(link_data)
            
            # 배치 삽입
            result = self.client.table('report_links').insert(links_data).execute()
            
            if result.data:
                logger.info(f"✅ {len(result.data)}개 각주 링크 저장 완료")
            else:
                raise SupabaseException("Failed to save report links")
                
        except Exception as e:
            logger.error(f"Database error in save_report_links: {str(e)}")
            raise SupabaseException(f"Failed to save report links: {str(e)}")
    
    async def get_report_links(self, report_id: str) -> List[Dict[str, Any]]:
        """보고서 각주 링크 조회"""
        try:
            result = self.client.table('report_links')\
                .select("*")\
                .eq('report_id', report_id)\
                .order('footnote_number', desc=False)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Database error in get_report_links: {str(e)}")
            raise SupabaseException(f"Failed to get report links: {str(e)}")