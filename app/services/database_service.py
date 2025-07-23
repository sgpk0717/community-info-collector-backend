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
            
            # keywords_used가 있으면 JSON 문자열로 변환
            if 'keywords_used' in report_dict and report_dict['keywords_used']:
                import json
                report_dict['keywords_used'] = json.dumps(report_dict['keywords_used'], ensure_ascii=False)
            
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
            
            # 각 보고서에 글자수 추가 및 keywords_used 파싱
            reports = result.data if result.data else []
            import json
            for report in reports:
                if report.get('full_report'):
                    report['report_char_count'] = len(report['full_report'])
                else:
                    report['report_char_count'] = 0
                
                # keywords_used가 JSON 문자열이면 파싱
                if report.get('keywords_used') and isinstance(report['keywords_used'], str):
                    try:
                        report['keywords_used'] = json.loads(report['keywords_used'])
                    except:
                        report['keywords_used'] = None
            
            return reports
            
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
                # created_utc 처리 (double precision 타입이므로 Unix timestamp로 저장)
                created_utc_value = None
                if link.get('created_utc'):
                    try:
                        created_utc = link['created_utc']
                        # 이미 Unix timestamp(숫자)인 경우 - 그대로 사용
                        if isinstance(created_utc, (int, float)):
                            created_utc_value = float(created_utc)
                        # ISO 문자열인 경우 - Unix timestamp로 변환
                        elif isinstance(created_utc, str):
                            try:
                                # ISO 형식 파싱
                                dt = datetime.fromisoformat(created_utc.replace('Z', '+00:00'))
                                created_utc_value = dt.timestamp()
                            except:
                                # 다른 날짜 형식 파싱 시도
                                from dateutil.parser import parse
                                dt = parse(created_utc)
                                created_utc_value = dt.timestamp()
                        else:
                            logger.warning(f"지원하지 않는 created_utc 형식: {type(created_utc)} - {created_utc}")
                    except Exception as e:
                        logger.warning(f"created_utc 변환 실패: {link['created_utc']} - {str(e)}")
                
                link_data = {
                    'report_id': report_id,
                    'footnote_number': link.get('footnote_number'),
                    'url': link.get('url', ''),
                    'title': link.get('title', ''),
                    'score': int(link.get('score', 0)) if link.get('score') is not None else 0,
                    'comments': int(link.get('comments', 0)) if link.get('comments') is not None else 0,
                    'created_utc': created_utc_value,  # Unix timestamp (숫자)로 저장
                    'subreddit': link.get('subreddit', ''),
                    'author': link.get('author', ''),
                    'position_in_report': link.get('position_in_report'),
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
    
    async def delete_reports(self, report_ids: List[str]) -> int:
        """보고서 일괄 삭제"""
        try:
            if not report_ids:
                return 0
            
            deleted_count = 0
            for report_id in report_ids:
                # report_links는 CASCADE 삭제되므로 reports만 삭제
                result = self.client.table('reports').delete().eq('id', report_id).execute()
                if result.data:
                    deleted_count += 1
                    logger.info(f"🗑️ 보고서 삭제: {report_id}")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Database error in delete_reports: {str(e)}")
            raise SupabaseException(f"Failed to delete reports: {str(e)}")