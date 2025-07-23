import tweepy
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.services.x_usage_service import XUsageService

logger = logging.getLogger(__name__)

class XService:
    """X(Twitter) API 서비스 - Free 티어 최적화"""
    
    def __init__(self, thread_pool: Optional[ThreadPoolExecutor] = None):
        # X API 사용 여부 확인
        self.use_x_api = os.getenv('USE_X_API', 'false').lower() == 'true'
        
        if not self.use_x_api:
            logger.warning("⚠️ X API가 비활성화되어 있습니다 (USE_X_API=false)")
            self.client = None
            self.usage_service = None
            self.thread_pool = thread_pool
            return
        
        # 환경변수에서 API 키 로드
        self.bearer_token = os.getenv('X_BEARER_TOKEN')
        self.api_key = os.getenv('X_API_KEY')
        self.api_secret = os.getenv('X_API_SECRET')
        self.access_token = os.getenv('X_ACCESS_TOKEN')
        self.access_token_secret = os.getenv('X_ACCESS_TOKEN_SECRET')
        
        if not all([self.bearer_token, self.api_key, self.api_secret, self.access_token, self.access_token_secret]):
            raise ValueError("X API 자격 증명이 완전하지 않습니다. .env 파일을 확인하세요.")
        
        # Tweepy 클라이언트 초기화
        self.client = tweepy.Client(
            bearer_token=self.bearer_token,
            consumer_key=self.api_key,
            consumer_secret=self.api_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret,
            wait_on_rate_limit=True  # Rate limit 시 자동 대기
        )
        
        self.usage_service = XUsageService()
        self.thread_pool = thread_pool
        
        logger.info("🐦 X API 서비스 초기화 완료")
    
    def _process_tweet(self, tweet, keyword_source: str = None) -> Dict[str, Any]:
        """트윗 데이터를 표준 형식으로 변환"""
        try:
            return {
                'id': tweet.id,
                'type': 'tweet',
                'text': tweet.text or '',
                'author_username': tweet.author_id,  # username은 별도 조회 필요
                'author_name': '',  # 별도 조회 필요
                'retweet_count': tweet.public_metrics.get('retweet_count', 0) if hasattr(tweet, 'public_metrics') else 0,
                'like_count': tweet.public_metrics.get('like_count', 0) if hasattr(tweet, 'public_metrics') else 0,
                'reply_count': tweet.public_metrics.get('reply_count', 0) if hasattr(tweet, 'public_metrics') else 0,
                'created_utc': tweet.created_at.timestamp() if hasattr(tweet, 'created_at') and tweet.created_at else datetime.now().timestamp(),
                'url': f"https://twitter.com/user/status/{tweet.id}",
                'lang': tweet.lang if hasattr(tweet, 'lang') else 'en',
                'keyword_source': keyword_source,
                'score': tweet.public_metrics.get('like_count', 0) + tweet.public_metrics.get('retweet_count', 0) * 2 if hasattr(tweet, 'public_metrics') else 0,
                'platform': 'x'
            }
        except Exception as e:
            logger.error(f"❌ 트윗 처리 실패: {str(e)}")
            return None
    
    async def search_tweets(self, query: str, max_results: int = 10, user_nickname: str = "system") -> List[Dict[str, Any]]:
        """트윗 검색 - 사용량 체크 후 실행"""
        # X API가 비활성화된 경우 빈 리스트 반환
        if not self.use_x_api:
            logger.info("🚫 X API가 비활성화되어 있어 검색을 건너뜁니다")
            return []
        
        try:
            logger.info(f"🔍 X API 검색 시작: '{query}' (최대 {max_results}개)")
            
            # 1. 사용량 체크
            usage_check = await self.usage_service.can_use_api(user_nickname, max_results)
            
            if not usage_check.get('can_use', False):
                logger.warning(f"⚠️ X API 사용 제한 - {usage_check}")
                return []
            
            # 2. Free 티어 제한 적용 (최소 10개, 최대 100개)
            max_results = max(10, min(max_results, 100))  # Free 티어는 10-100개
            
            # 3. 실제 API 호출 (스레드풀에서 실행)
            loop = asyncio.get_event_loop()
            
            def _search():
                try:
                    # 최근 7일 내 트윗만 검색 (Free 티어 제한)
                    tweets = self.client.search_recent_tweets(
                        query=query,
                        max_results=max_results,
                        tweet_fields=['created_at', 'author_id', 'public_metrics', 'lang', 'context_annotations'],
                        expansions=['author_id'],
                        user_fields=['username', 'name']
                    )
                    return tweets
                except tweepy.TooManyRequests:
                    logger.warning("⚠️ X API Rate limit 도달")
                    return None
                except tweepy.Unauthorized:
                    logger.error("❌ X API 인증 실패 - API 키를 확인하세요")
                    return None
                except Exception as e:
                    logger.error(f"❌ X API 호출 실패: {str(e)}")
                    return None
            
            if self.thread_pool:
                tweets_response = await loop.run_in_executor(self.thread_pool, _search)
            else:
                tweets_response = await loop.run_in_executor(None, _search)
            
            if not tweets_response or not tweets_response.data:
                logger.info("📭 X API에서 트윗을 찾을 수 없습니다")
                return []
            
            # 4. 트윗 데이터 처리
            processed_tweets = []
            for tweet in tweets_response.data:
                processed_tweet = self._process_tweet(tweet, keyword_source=query)
                if processed_tweet:
                    processed_tweets.append(processed_tweet)
            
            # 5. 사용량 기록
            await self.usage_service.record_usage(
                endpoint='search',
                tweets_count=len(processed_tweets),
                requests_count=1,
                user_nickname=user_nickname
            )
            
            logger.info(f"✅ X API 검색 완료: {len(processed_tweets)}개 트윗 수집")
            return processed_tweets
            
        except Exception as e:
            logger.error(f"❌ X API 검색 실패: {str(e)}")
            return []
    
    async def get_user_tweets(self, username: str, max_results: int = 5, user_nickname: str = "system") -> List[Dict[str, Any]]:
        """특정 사용자의 최근 트윗 조회"""
        # X API가 비활성화된 경우 빈 리스트 반환
        if not self.use_x_api:
            logger.info("🚫 X API가 비활성화되어 있어 사용자 트윗 조회를 건너뜁니다")
            return []
        
        try:
            logger.info(f"👤 X API 사용자 트윗 조회: @{username} (최대 {max_results}개)")
            
            # 1. 사용량 체크
            usage_check = await self.usage_service.can_use_api(user_nickname, max_results)
            
            if not usage_check.get('can_use', False):
                logger.warning(f"⚠️ X API 사용 제한 - {usage_check}")
                return []
            
            # 2. Free 티어 제한 적용 (최소 10개)
            max_results = max(10, min(max_results, 100))  # 사용자 타임라인도 최소 10개
            
            # 3. 실제 API 호출
            loop = asyncio.get_event_loop()
            
            def _get_user_tweets():
                try:
                    # 먼저 사용자 ID 조회
                    user = self.client.get_user(username=username)
                    if not user.data:
                        return None
                    
                    # 사용자의 최근 트윗 조회
                    tweets = self.client.get_users_tweets(
                        id=user.data.id,
                        max_results=max_results,
                        tweet_fields=['created_at', 'public_metrics', 'lang'],
                        exclude=['retweets', 'replies']  # 리트윗과 답글 제외
                    )
                    return tweets
                except Exception as e:
                    logger.error(f"❌ 사용자 트윗 조회 실패: {str(e)}")
                    return None
            
            if self.thread_pool:
                tweets_response = await loop.run_in_executor(self.thread_pool, _get_user_tweets)
            else:
                tweets_response = await loop.run_in_executor(None, _get_user_tweets)
            
            if not tweets_response or not tweets_response.data:
                logger.info(f"📭 @{username}의 트윗을 찾을 수 없습니다")
                return []
            
            # 4. 트윗 데이터 처리
            processed_tweets = []
            for tweet in tweets_response.data:
                processed_tweet = self._process_tweet(tweet, keyword_source=f"@{username}")
                if processed_tweet:
                    processed_tweets.append(processed_tweet)
            
            # 5. 사용량 기록
            await self.usage_service.record_usage(
                endpoint='user_timeline',
                tweets_count=len(processed_tweets),
                requests_count=2,  # 사용자 조회 + 트윗 조회
                user_nickname=user_nickname
            )
            
            logger.info(f"✅ @{username} 트윗 조회 완료: {len(processed_tweets)}개 트윗 수집")
            return processed_tweets
            
        except Exception as e:
            logger.error(f"❌ 사용자 트윗 조회 실패: {str(e)}")
            return []
    
    async def get_usage_stats(self, user_nickname: str = "system") -> Dict[str, Any]:
        """현재 사용량 통계 조회"""
        if not self.use_x_api:
            return {"error": "X API is disabled", "use_x_api": False}
        return await self.usage_service.get_usage_stats(user_nickname)
    
    def normalize_for_analysis(self, tweets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """트윗 데이터를 분석용 표준 형식으로 변환 (Reddit 호환)"""
        normalized = []
        
        for tweet in tweets:
            try:
                normalized_tweet = {
                    'id': str(tweet['id']),
                    'title': tweet['text'][:100] + '...' if len(tweet['text']) > 100 else tweet['text'],  # 제목으로 사용
                    'selftext': tweet['text'],  # 본문
                    'score': tweet['score'],  # 좋아요 + 리트윗*2
                    'num_comments': tweet['reply_count'],
                    'created_utc': tweet['created_utc'],
                    'author': tweet['author_username'],
                    'subreddit': 'twitter',  # 플랫폼 식별용
                    'url': tweet['url'],
                    'keyword_source': tweet['keyword_source'],
                    'platform': 'x',
                    'type': 'tweet'
                }
                normalized.append(normalized_tweet)
            except Exception as e:
                logger.error(f"❌ 트윗 정규화 실패: {str(e)}")
                continue
        
        return normalized