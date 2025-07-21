from typing import Dict, Any, List, Optional
from app.services.reddit_service import RedditService
from app.services.llm_service import LLMService
from app.services.database_service import DatabaseService
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
        """검색 요청 처리 및 분석"""
        try:
            logger.info(f"🚀 분석 서비스 시작: '{request.query}' (사용자: {request.user_nickname})")
            
            # 진행상황 업데이트
            if progress_callback:
                await progress_callback("분석 준비 중", 0)
            
            # 1. 사용자 확인/생성
            logger.info(f"👤 사용자 확인/생성: {request.user_nickname}")
            user = await self.db_service.get_or_create_user(request.user_nickname)
            
            # 2. 한글 키워드를 영어로 번역
            if progress_callback:
                await progress_callback("키워드 번역 중", 5)
            
            logger.info(f"🌐 키워드 번역 시작: '{request.query}' (한국어 → 영어)")
            english_query = await self.llm_service.translate_to_english(request.query)
            logger.info(f"✅ 번역 완료: '{request.query}' → '{english_query}'")
            
            # 3. 키워드 확장 (선택적, 영어로)
            if progress_callback:
                await progress_callback("키워드 확장 중", 10)
                
            expanded_keywords = []
            if request.length in [ReportLength.moderate, ReportLength.detailed]:
                logger.info(f"🔍 키워드 확장 시작 (보고서 길이: {request.length.value})")
                expanded_keywords = await self.llm_service.expand_keywords(request.query)  # 내부에서 번역됨
                logger.info(f"📝 확장된 키워드 ({len(expanded_keywords)}개): {expanded_keywords}")
            
            # 4. 시간 범위 계산
            start_date, end_date, reddit_time_filter = self._calculate_time_range(request)
            if request.time_filter:
                logger.info(f"⏰ 시간 필터 적용: {request.time_filter.value} ({start_date.strftime('%Y-%m-%d %H:%M')} ~ {end_date.strftime('%Y-%m-%d %H:%M')})")
            
            # 5. 게시물 수집 (영어로)
            if progress_callback:
                await progress_callback("소셜 미디어 데이터 수집 중", 20)
            
            all_posts = []
            
            # Reddit 검색 (영어 키워드 사용)
            if "reddit" in request.sources:
                logger.info(f"🔍 Reddit 검색 시작: '{english_query}' (시간 필터: {reddit_time_filter})")
                
                # 영어 키워드로 검색
                posts = await self.reddit_service.search_posts(english_query, limit=30, time_filter=reddit_time_filter)
                all_posts.extend(posts)
                
                if progress_callback:
                    await progress_callback(f"Reddit에서 {len(posts)}개 게시물 수집", 40)
                
                # 확장된 키워드로 추가 검색
                if expanded_keywords:
                    logger.info(f"📈 확장된 키워드로 추가 검색 시작 ({len(expanded_keywords)}개 키워드)")
                    additional_posts = await self.reddit_service.search_with_keywords(
                        expanded_keywords, 
                        limit_per_keyword=10
                    )
                    all_posts.extend(additional_posts)
                    
                    if progress_callback:
                        await progress_callback(f"총 {len(all_posts)}개 게시물 수집 완료", 50)
            
            # 날짜 범위에 따른 게시물 필터링
            if request.time_filter:
                filtered_posts = []
                for post in all_posts:
                    post_date = datetime.fromtimestamp(post['created_utc'])
                    if start_date <= post_date <= end_date:
                        filtered_posts.append(post)
                
                logger.info(f"📅 날짜 필터링: {len(all_posts)}개 → {len(filtered_posts)}개 (범위: {start_date} ~ {end_date})")
                all_posts = filtered_posts
            
            # 게시물이 없으면 에러
            if not all_posts:
                logger.error("❌ 게시물을 찾을 수 없습니다")
                raise Exception("No posts found for the given query")
            
            # 중복 제거 및 정렬
            logger.info(f"🔄 게시물 중복 제거 및 정렬 시작 (원본: {len(all_posts)}개)")
            unique_posts = self._deduplicate_posts(all_posts)
            logger.info(f"✅ 중복 제거 완료: {len(unique_posts)}개 게시물")
            
            # 4. AI 분석 및 보고서 생성
            if progress_callback:
                await progress_callback("AI 분석 중", 60)
            
            logger.info(f"🤖 AI 분석 및 보고서 생성 시작 ({len(unique_posts)}개 게시물)")
            report_data = await self.llm_service.generate_report(
                posts=unique_posts,
                query=request.query,
                length=request.length
            )
            
            if progress_callback:
                await progress_callback("보고서 생성 완료", 80)
            
            # 5. 보고서 저장
            logger.info(f"💾 보고서 데이터베이스 저장 시작")
            report_create = ReportCreate(
                user_nickname=request.user_nickname,
                query_text=request.query,
                summary=report_data['summary'],
                full_report=report_data['full_report'],
                posts_collected=len(unique_posts),
                report_length=request.length.value,
                session_id=request.session_id
            )
            
            report_id = await self.db_service.save_report(report_create)
            logger.info(f"✅ 보고서 저장 완료: {report_id}")
            
            # 6. 각주 링크 저장
            footnote_mapping = report_data.get('footnote_mapping', [])
            if footnote_mapping:
                logger.info(f"🔗 각주 링크 저장 시작: {len(footnote_mapping)}개")
                await self.db_service.save_report_links(report_id, footnote_mapping)
                logger.info(f"✅ 각주 링크 저장 완료")
            
            if progress_callback:
                await progress_callback("저장 완료", 90)
            
            # 7. 스케줄 생성 (요청 시)
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
                    'sources': [s.value for s in request.sources],
                    'notification_enabled': bool(request.push_token)
                }
                schedule_id = await self.db_service.create_schedule(schedule_data)
                logger.info(f"✅ 스케줄 생성 완료: {schedule_id}")
            
            if progress_callback:
                await progress_callback("완료", 100)
            
            logger.info(f"🎉 분석 완료! 보고서 ID: {report_id}, 게시물 수: {len(unique_posts)}개")
            
            return {
                'report_id': report_id,
                'summary': report_data['summary'],
                'full_report': report_data['full_report'],
                'posts_collected': len(unique_posts),
                'schedule_id': schedule_id
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