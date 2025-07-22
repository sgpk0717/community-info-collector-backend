from typing import Dict, Any, List, Optional
from app.services.reddit_service import RedditService
from app.services.llm_service import LLMService
from app.services.database_service import DatabaseService
from app.services.relevance_filtering_service import RelevanceFilteringService
from app.services.topic_clustering_service import TopicClusteringService
from app.services.orchestrator_service import OrchestratorService
from app.schemas.search import SearchRequest, ReportLength, TimeFilter
from app.schemas.report import ReportCreate
import logging
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(self, thread_pool: Optional[ThreadPoolExecutor] = None, api_semaphore: Optional[asyncio.Semaphore] = None):
        self.reddit_service = RedditService(thread_pool=thread_pool)
        self.llm_service = LLMService(api_semaphore=api_semaphore)
        self.relevance_service = RelevanceFilteringService(thread_pool=thread_pool, api_semaphore=api_semaphore)
        self.clustering_service = TopicClusteringService(thread_pool=thread_pool, api_semaphore=api_semaphore)
        self.orchestrator_service = OrchestratorService(thread_pool=thread_pool, api_semaphore=api_semaphore)
        self.db_service = DatabaseService()
        self.thread_pool = thread_pool
        self.api_semaphore = api_semaphore
    
    def _calculate_time_range(self, request: SearchRequest) -> tuple[datetime, datetime, str]:
        """시간 필터에 따른 날짜 범위 계산"""
        now = datetime.now()
        
        if request.time_filter == TimeFilter.custom and request.start_date and request.end_date:
            return request.start_date, request.end_date, 'all'
        
        # 시간 필터별 계산
        time_ranges = {
            TimeFilter.hour_1: (now - timedelta(hours=1), 'hour'),
            TimeFilter.hour_3: (now - timedelta(hours=3), 'hour'),
            TimeFilter.hour_6: (now - timedelta(hours=6), 'day'),
            TimeFilter.hour_12: (now - timedelta(hours=12), 'day'),
            TimeFilter.day_1: (now - timedelta(days=1), 'day'),
            TimeFilter.day_3: (now - timedelta(days=3), 'week'),
            TimeFilter.week_1: (now - timedelta(weeks=1), 'week'),
            TimeFilter.month_1: (now - timedelta(days=30), 'month'),
        }
        
        if request.time_filter and request.time_filter in time_ranges:
            start_time, reddit_filter = time_ranges[request.time_filter]
            return start_time, now, reddit_filter
        
        # 기본값: 전체 기간
        return datetime.min, now, 'all'
        
    async def process_search_request(self, request: SearchRequest, progress_callback=None) -> Dict[str, Any]:
        """검색 요청 처리 및 분석 - 오케스트레이터 사용"""
        try:
            logger.info(f"🚀 분석 서비스 시작: '{request.query}' (사용자: {request.user_nickname})")
            
            # 진행상황 업데이트
            if progress_callback:
                await progress_callback("분석 준비 중", 0)
            
            # 1. 사용자 확인/생성
            logger.info(f"👤 사용자 확인/생성: {request.user_nickname}")
            user = await self.db_service.get_or_create_user(request.user_nickname)
            
            # 2. 오케스트레이터를 통한 전체 분석 수행
            logger.info("🎼 오케스트레이터 기반 분석 시작")
            orchestration_result = await self.orchestrator_service.orchestrate_analysis(
                request,
                progress_callback
            )
            
            # 3. 보고서 저장
            if progress_callback:
                await progress_callback("보고서 저장 중", 80)
            
            report_data = orchestration_result['report']
            metadata = orchestration_result['metadata']
            
            logger.info(f"💾 보고서 데이터베이스 저장 시작")
            
            # 키워드 정보 생성
            keywords_used = []
            keyword_stats = metadata.get('keyword_stats', {})
            
            for idx, kw in enumerate(metadata['expanded_keywords'][:10]):
                # 키워드별 통계 정보 가져오기
                kw_stat = keyword_stats.get(kw, {})
                
                keywords_used.append({
                    'keyword': kw,
                    'translated_keyword': None,
                    'posts_found': kw_stat.get('posts_found', 0),
                    'sample_titles': kw_stat.get('sample_titles', [])
                })
            
            report_create = ReportCreate(
                user_nickname=request.user_nickname,
                query_text=request.query,
                summary=report_data['summary'],
                full_report=report_data['full_report'],
                posts_collected=metadata['filtered_count'],
                report_length=request.length.value,
                session_id=request.session_id,
                keywords_used=keywords_used
            )
            
            report_id = await self.db_service.save_report(report_create)
            logger.info(f"✅ 보고서 저장 완료: {report_id}")
            
            # 각주 매핑 저장 (있을 경우)
            footnote_mapping = report_data.get('footnote_mapping', [])
            if footnote_mapping:
                logger.info(f"🔗 각주 매핑 저장 시작: {len(footnote_mapping)}개")
                await self.db_service.save_report_links(report_id, footnote_mapping)
                logger.info(f"✅ 각주 매핑 저장 완료")
            
            # 4. 스케줄 생성 (요청 시)
            schedule_id = None
            if request.schedule_yn == "Y":
                logger.info(f"📅 스케줄 생성 시작 (주기: {request.schedule_period}분, 횟수: {request.schedule_count}회)")
                schedule_data = {
                    'user_nickname': request.user_nickname,
                    'keyword': request.query,
                    'interval_minutes': request.schedule_period,
                    'total_reports': request.schedule_count,
                    'next_run': request.schedule_start_time.isoformat() if request.schedule_start_time else None,
                    'report_length': request.length.value,
                    'sources': request.sources,
                    'notification_enabled': bool(request.push_token)
                }
                schedule_id = await self.db_service.create_schedule(schedule_data)
                logger.info(f"✅ 스케줄 생성 완료: {schedule_id}")
            
            if progress_callback:
                await progress_callback("완료", 100)
            
            logger.info(f"🎉 분석 완료! 보고서 ID: {report_id}")
            
            return {
                'report_id': report_id,
                'summary': report_data['summary'],
                'full_report': report_data['full_report'],
                'posts_collected': metadata['filtered_count'],
                'schedule_id': schedule_id,
                'quality_metrics': report_data.get('quality_metrics', {})
            }
            
        except Exception as e:
            logger.error(f"❌ 분석 서비스 오류: {str(e)}")
            raise
    
    def _deduplicate_posts(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 게시물 제거"""
        seen_ids = set()
        unique_posts = []
        duplicates_removed = 0
        
        for post in posts:
            if post['id'] not in seen_ids:
                seen_ids.add(post['id'])
                unique_posts.append(post)
            else:
                duplicates_removed += 1
        
        # 점수 기준 정렬
        unique_posts.sort(key=lambda x: x['score'], reverse=True)
        
        if duplicates_removed > 0:
            logger.info(f"🔄 중복 제거 완료: {duplicates_removed}개 게시물 제거")
        
        # 상위 게시물 정보 로그
        if unique_posts:
            top_post = unique_posts[0]
            logger.info(f"🏆 최고 점수 게시물: {top_post['score']}점 - {top_post['title'][:50]}...")
        
        return unique_posts