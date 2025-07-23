from typing import List, Dict, Any, Optional
from app.services.reddit_service import RedditService
from app.services.x_service import XService
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class MultiPlatformService:
    """멀티 플랫폼 통합 검색 서비스"""
    
    def __init__(self, thread_pool: Optional[ThreadPoolExecutor] = None, api_semaphore: Optional[asyncio.Semaphore] = None):
        try:
            self.reddit_service = RedditService(thread_pool=thread_pool)
            logger.info("✅ Reddit 서비스 초기화 완료")
        except Exception as e:
            logger.error(f"❌ Reddit 서비스 초기화 실패: {str(e)}")
            self.reddit_service = None
        
        try:
            self.x_service = XService(thread_pool=thread_pool)
            # USE_X_API가 false인 경우 메시지
            if self.x_service and not getattr(self.x_service, 'use_x_api', True):
                logger.info("ℹ️ X 서비스가 환경변수 설정에 의해 비활성화됨 (USE_X_API=false)")
            else:
                logger.info("✅ X 서비스 초기화 완료")
        except Exception as e:
            logger.error(f"❌ X 서비스 초기화 실패: {str(e)}")
            logger.warning("X API 자격 증명을 확인하세요. Reddit만 사용됩니다.")
            self.x_service = None
        
        self.thread_pool = thread_pool
        self.api_semaphore = api_semaphore
        
        logger.info("🌐 멀티 플랫폼 서비스 초기화 완료")
    
    async def search_all_platforms(
        self, 
        query: str, 
        sources: List[str], 
        user_nickname: str = "system",
        reddit_limit: int = 45,
        x_limit: int = 10  # X API 최소 요구사항
    ) -> List[Dict[str, Any]]:
        """모든 플랫폼에서 검색 - Reddit 90% + X 10% 비율"""
        
        logger.info(f"🔍 멀티 플랫폼 검색 시작: '{query}'")
        logger.info(f"   플랫폼: {sources}, Reddit 최대: {reddit_limit}개, X 최대: {x_limit}개")
        
        all_posts = []
        tasks = []
        
        # Reddit 검색 (무제한, 높은 비율)
        if 'reddit' in sources and self.reddit_service:
            logger.info(f"📱 Reddit 검색 예정: 최대 {reddit_limit}개 게시물")
            tasks.append(self._search_reddit(query, reddit_limit))
        
        # X 검색 (극도로 제한적, 낮은 비율)
        if 'x' in sources and self.x_service:
            logger.info(f"🐦 X 검색 예정: 최대 {x_limit}개 트윗 (사용량 체크 후)")
            tasks.append(self._search_x(query, x_limit, user_nickname))
        
        # 병렬 실행
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    platform = 'reddit' if i == 0 and 'reddit' in sources else 'x'
                    logger.error(f"❌ {platform} 검색 실패: {str(result)}")
                elif isinstance(result, list):
                    all_posts.extend(result)
        
        # 플랫폼별 통계
        reddit_count = len([p for p in all_posts if p.get('platform') == 'reddit'])
        x_count = len([p for p in all_posts if p.get('platform') == 'x'])
        
        logger.info(f"📊 멀티 플랫폼 검색 완료:")
        logger.info(f"   📱 Reddit: {reddit_count}개 게시물")
        logger.info(f"   🐦 X: {x_count}개 트윗")
        logger.info(f"   📈 총합: {len(all_posts)}개 콘텐츠")
        
        # 점수순으로 정렬 (높은 점수 먼저)
        all_posts.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return all_posts
    
    async def _search_reddit(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Reddit 검색 (내부 메서드)"""
        try:
            reddit_posts = await self.reddit_service.search_posts(
                query=query,
                limit=limit,
                time_filter='week'  # 기본적으로 1주일 내 게시물
            )
            
            # 플랫폼 정보 추가
            for post in reddit_posts:
                post['platform'] = 'reddit'
                post['type'] = 'post'
            
            logger.info(f"✅ Reddit 검색 완료: {len(reddit_posts)}개 게시물")
            return reddit_posts
            
        except Exception as e:
            logger.error(f"❌ Reddit 검색 실패: {str(e)}")
            return []
    
    async def _search_x(self, query: str, limit: int, user_nickname: str) -> List[Dict[str, Any]]:
        """X 검색 (내부 메서드)"""
        try:
            x_tweets = await self.x_service.search_tweets(
                query=query,
                max_results=limit,
                user_nickname=user_nickname
            )
            
            # Reddit 호환 형식으로 정규화
            normalized_tweets = self.x_service.normalize_for_analysis(x_tweets)
            
            logger.info(f"✅ X 검색 완료: {len(normalized_tweets)}개 트윗")
            return normalized_tweets
            
        except Exception as e:
            logger.error(f"❌ X 검색 실패: {str(e)}")
            return []
    
    async def search_trending_topics(self, sources: List[str], user_nickname: str = "system") -> List[Dict[str, Any]]:
        """트렌딩 토픽 검색 (플랫폼별 인기 키워드)"""
        
        logger.info(f"🔥 트렌딩 토픽 검색 시작: {sources}")
        all_trending = []
        
        # X 트렌딩 (매우 제한적으로)
        if 'x' in sources and self.x_service:
            try:
                # 인기 있는 일반적인 키워드들로 샘플링
                trending_keywords = ["AI", "tech", "news", "bitcoin", "stock"]
                
                for keyword in trending_keywords[:2]:  # 2개만 사용
                    tweets = await self.x_service.search_tweets(
                        query=keyword,
                        max_results=3,  # 키워드당 3개만
                        user_nickname=user_nickname
                    )
                    
                    if tweets:
                        normalized = self.x_service.normalize_for_analysis(tweets)
                        all_trending.extend(normalized)
                
            except Exception as e:
                logger.error(f"❌ X 트렌딩 검색 실패: {str(e)}")
        
        # Reddit 트렌딩 (더 많이)
        if 'reddit' in sources and self.reddit_service:
            try:
                # 인기 서브레딧에서 hot 게시물 수집
                hot_posts = await self.reddit_service.search_posts(
                    query="",  # 빈 쿼리로 전체 인기 게시물
                    limit=20,
                    time_filter='day'
                )
                
                for post in hot_posts:
                    post['platform'] = 'reddit'
                    post['type'] = 'trending'
                
                all_trending.extend(hot_posts)
                
            except Exception as e:
                logger.error(f"❌ Reddit 트렌딩 검색 실패: {str(e)}")
        
        logger.info(f"🔥 트렌딩 토픽 검색 완료: {len(all_trending)}개")
        return all_trending
    
    async def get_platform_stats(self, user_nickname: str = "system") -> Dict[str, Any]:
        """플랫폼별 사용 통계"""
        stats = {
            "reddit": {"available": self.reddit_service is not None, "status": "unlimited"},
            "x": {"available": self.x_service is not None, "status": "limited"}
        }
        
        # X API 사용량 통계
        if self.x_service:
            try:
                x_stats = await self.x_service.get_usage_stats(user_nickname)
                stats["x"]["usage"] = x_stats
            except Exception as e:
                logger.error(f"❌ X 사용량 통계 조회 실패: {str(e)}")
                stats["x"]["error"] = str(e)
        
        return stats
    
    def get_supported_platforms(self) -> List[str]:
        """지원 가능한 플랫폼 목록"""
        platforms = []
        
        if self.reddit_service:
            platforms.append("reddit")
        
        if self.x_service and getattr(self.x_service, 'use_x_api', False):
            platforms.append("x")
        
        return platforms
    
    def is_platform_available(self, platform: str) -> bool:
        """특정 플랫폼 사용 가능 여부"""
        if platform == "reddit":
            return self.reddit_service is not None
        elif platform == "x":
            return (
                self.x_service is not None and 
                getattr(self.x_service, 'use_x_api', False)
            )
        else:
            return False