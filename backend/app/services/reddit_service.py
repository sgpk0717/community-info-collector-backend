import praw
from typing import List, Dict, Any, Optional
from app.core.dependencies import get_reddit_client
from app.core.exceptions import RedditAPIException
import logging
from datetime import datetime, timedelta
import asyncio
import re
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import time

logger = logging.getLogger(__name__)

# 루머 탐지용 키워드 세트
SPECULATIVE_WORDS = {
    'might', 'could', 'perhaps', 'likely', 'possibly', 'maybe', 'supposedly',
    'allegedly', 'rumor', 'rumour', 'unconfirmed', 'sources say', 'i heard',
    'word is', 'gossip', 'speculation', 'apparently', 'seems like',
    # 한국어 추측 표현
    '아마도', '아마', '~일 수도', '~인 것 같', '소문에', '카더라', '들었는데',
    '~라는 얘기', '~같다는', '추측', '예상', '~일지도'
}

NEGATIVE_EMOTION_WORDS = {
    'disaster', 'crisis', 'collapse', 'crash', 'terrible', 'awful', 'horrible',
    'devastating', 'nightmare', 'panic', 'fear', 'doom', 'failed', 'failure',
    'warning', 'danger', 'risk', 'threat', 'concerned', 'worried',
    # 한국어 부정적 감정 표현
    '재앙', '위기', '붕괴', '추락', '끔찍한', '무서운', '공포', '실패', '위험',
    '경고', '걱정', '우려', '문제', '심각한', '최악'
}

class RedditService:
    def __init__(self, thread_pool: Optional[ThreadPoolExecutor] = None):
        self.client = get_reddit_client()
        self.thread_pool = thread_pool
        
        # Rate Limit 관리를 위한 속성
        self.request_timestamps = deque(maxlen=60)  # 최근 60개 요청 시간 저장
        self.rate_limit_lock = asyncio.Lock()  # 동시성 제어
    
    def _calculate_rumor_score_sync(self, submission) -> float:
        """루머 점수 계산 (0-10 범위) - 동기 버전"""
        score = 0.0
        score_breakdown = []
        
        # 1. 논란성 지표 (upvote_ratio)
        if hasattr(submission, 'upvote_ratio') and submission.upvote_ratio < 0.7:
            controversy_score = (0.7 - submission.upvote_ratio) * 5  # 최대 3.5점
            score += controversy_score
            score_breakdown.append(f"논란성({submission.upvote_ratio:.2f}): +{controversy_score:.1f}")
        
        # 2. 언어학적 신호 탐지
        text = (submission.title + ' ' + (submission.selftext or '')).lower()
        
        # 추측성 단어 개수
        speculation_count = sum(1 for word in SPECULATIVE_WORDS if word in text)
        if speculation_count > 0:
            speculation_score = min(speculation_count * 1.5, 3.0)  # 최대 3점
            score += speculation_score
            score_breakdown.append(f"추측성({speculation_count}개): +{speculation_score:.1f}")
        
        # 부정적 감정 단어 개수
        negative_count = sum(1 for word in NEGATIVE_EMOTION_WORDS if word in text)
        if negative_count > 0:
            negative_score = min(negative_count * 1.0, 2.0)  # 최대 2점
            score += negative_score
            score_breakdown.append(f"부정감정({negative_count}개): +{negative_score:.1f}")
        
        # 3. 게시물 특성
        if hasattr(submission, 'is_self') and submission.is_self:
            score += 0.5  # 자체 게시물 (링크가 아닌 텍스트)
            score_breakdown.append(f"자체게시물: +0.5")
        
        # 4. 수집 벡터 가중치
        if hasattr(submission, '_collection_vector'):
            if submission._collection_vector == 'underground':
                score += 1.0  # 논란성 벡터에서 수집된 경우
                score_breakdown.append(f"논란성벡터: +1.0")
            elif submission._collection_vector == 'vanguard':
                score += 0.5  # 최신 벡터에서 수집된 경우
                score_breakdown.append(f"최신벡터: +0.5")
        
        final_score = min(score, 10.0)  # 최대 10점으로 제한
        
        # 루머 점수 계산 로그 (점수가 5 이상일 때만)
        if final_score >= 5.0:
            logger.info(f"🚨 높은 루머 점수 감지 [{final_score:.1f}/10] - {submission.title[:50]}...")
            logger.info(f"   세부사항: {', '.join(score_breakdown)}")
        
        return final_score
    
    def _extract_linguistic_flags_sync(self, text: str) -> List[str]:
        """언어학적 신호 플래그 추출 - 동기 버전"""
        flags = []
        text_lower = text.lower()
        
        # 추측성 언어 탐지
        speculation_words = [word for word in SPECULATIVE_WORDS if word in text_lower]
        if speculation_words:
            flags.append('speculation')
            logger.debug(f"🔍 추측성 언어 감지: {speculation_words[:3]}...")
        
        # 부정적 감정 탐지
        negative_words = [word for word in NEGATIVE_EMOTION_WORDS if word in text_lower]
        if negative_words:
            flags.append('negative_emotion')
            logger.debug(f"😠 부정적 감정 감지: {negative_words[:3]}...")
        
        # 비공식성 탐지 (느낌표, 대문자 과다 사용)
        exclamation_count = text.count('!')
        caps_words = re.findall(r'[A-Z]{3,}', text)
        if exclamation_count > 2 or len(caps_words) > 0:
            flags.append('informal')
            logger.debug(f"📢 비공식성 감지: 느낌표 {exclamation_count}개, 대문자 {len(caps_words)}개")
        
        return flags
    
    async def _process_submission_batch(self, submissions: List[Any]) -> List[Dict[str, Any]]:
        """게시물 배치를 병렬로 처리"""
        if not self.thread_pool:
            # 스레드풀이 없으면 동기적으로 처리
            return [self._process_submission_sync(sub) for sub in submissions]
        
        # 스레드풀에서 병렬 처리
        loop = asyncio.get_event_loop()
        tasks = [
            loop.run_in_executor(self.thread_pool, self._process_submission_sync, sub)
            for sub in submissions
        ]
        return await asyncio.gather(*tasks)
    
    def _process_submission_sync(self, submission) -> Dict[str, Any]:
        """단일 게시물 처리 - 동기 버전"""
        text_to_analyze = submission.title + ' ' + (submission.selftext or '')
        
        # CPU 집약적 작업들
        rumor_score = self._calculate_rumor_score_sync(submission)
        linguistic_flags = self._extract_linguistic_flags_sync(text_to_analyze)
        
        return {
            'id': submission.id,
            'title': submission.title,
            'selftext': submission.selftext,
            'score': submission.score,
            'num_comments': submission.num_comments,
            'created_utc': submission.created_utc,
            'author': str(submission.author),
            'subreddit': str(submission.subreddit),
            'url': f"https://reddit.com{submission.permalink}",
            'upvote_ratio': getattr(submission, 'upvote_ratio', 0.5),
            'is_self': getattr(submission, 'is_self', True),
            'collection_vector': getattr(submission, '_collection_vector', 'zeitgeist'),
            'rumor_score': rumor_score,
            'linguistic_flags': linguistic_flags
        }
        
    async def search_posts(self, query: str, limit: int = 50, time_filter: str = 'all') -> List[Dict[str, Any]]:
        """Reddit에서 키워드로 게시물 검색 - 다중 벡터 수집 전략
        
        Args:
            query: 검색 키워드
            limit: 최대 게시물 수
            time_filter: 시간 필터 ('hour', 'day', 'week', 'month', 'year', 'all')
        """
        try:
            # Rate limit 체크
            await self._check_rate_limit()
            
            logger.info(f"🔍 Reddit 검색 시작: '{query}' (최대 {limit}개 게시물, 기간: {time_filter})")
            
            # Reddit API 호출은 스레드풀에서 실행
            loop = asyncio.get_event_loop()
            
            def _search():
                # 다중 벡터 수집 전략 (시간 필터 적용)
                # 사용자 지정 time_filter가 있으면 모든 벡터에 적용
                if time_filter != 'all':
                    vectors = [
                        {'name': 'zeitgeist', 'sort': 'hot', 'time_filter': time_filter, 'limit': limit//3},
                        {'name': 'underground', 'sort': 'controversial', 'time_filter': time_filter, 'limit': limit//3},
                        {'name': 'vanguard', 'sort': 'new', 'time_filter': time_filter, 'limit': limit//3}
                    ]
                else:
                    # 기본 전략
                    vectors = [
                        {'name': 'zeitgeist', 'sort': 'hot', 'time_filter': 'week', 'limit': limit//3},
                        {'name': 'underground', 'sort': 'controversial', 'time_filter': 'month', 'limit': limit//3},
                        {'name': 'vanguard', 'sort': 'new', 'time_filter': 'all', 'limit': limit//3}
                    ]
                
                logger.info(f"📊 다중 벡터 수집 전략 시작 - 총 {len(vectors)}개 벡터")
                all_submissions = []
                
                for vector in vectors:
                    try:
                        logger.info(f"🎯 벡터 '{vector['name']}' 검색 시작 - 정렬: {vector['sort']}, 기간: {vector['time_filter']}, 제한: {vector['limit']}")
                        
                        subreddit = self.client.subreddit('all')
                        
                        # 벡터별 검색 수행
                        if vector['sort'] == 'hot':
                            search_results = subreddit.search(
                                query, 
                                limit=vector['limit'], 
                                sort='hot',
                                time_filter=vector['time_filter']
                            )
                        elif vector['sort'] == 'controversial':
                            search_results = subreddit.search(
                                query, 
                                limit=vector['limit'], 
                                sort='controversial',
                                time_filter=vector['time_filter']
                            )
                        else:  # new
                            search_results = subreddit.search(
                                query, 
                                limit=vector['limit'], 
                                sort='new',
                                time_filter=vector['time_filter']
                            )
                        
                        # 벡터 정보를 각 submission에 추가
                        vector_submissions = []
                        for submission in search_results:
                            submission._collection_vector = vector['name']
                            vector_submissions.append(submission)
                        
                        all_submissions.extend(vector_submissions)
                        logger.info(f"✅ 벡터 '{vector['name']}' 수집 완료: {len(vector_submissions)}개 게시물")
                        
                    except Exception as e:
                        logger.error(f"❌ 벡터 '{vector['name']}' 검색 실패: {str(e)}")
                        continue
                
                logger.info(f"📈 전체 벡터 수집 완료: 총 {len(all_submissions)}개 게시물")
                return all_submissions
            
            # Reddit API 검색을 스레드풀에서 실행
            if self.thread_pool:
                all_submissions = await loop.run_in_executor(self.thread_pool, _search)
            else:
                all_submissions = await loop.run_in_executor(None, _search)
            
            # 게시물 처리를 병렬로 수행
            posts = await self._process_submission_batch(all_submissions)
            
            logger.info(f"✅ Reddit 검색 완료 - 총 {len(posts)}개 게시물 수집")
            return posts
            
        except Exception as e:
            logger.error(f"Reddit search error: {str(e)}")
            raise RedditAPIException(f"Failed to search Reddit: {str(e)}")
    
    async def get_subreddit_info(self, subreddit_name: str) -> Dict[str, Any]:
        """특정 subreddit 정보 조회"""
        try:
            loop = asyncio.get_event_loop()
            
            def _get_info():
                subreddit = self.client.subreddit(subreddit_name)
                return {
                    'name': subreddit.display_name,
                    'title': subreddit.title,
                    'subscribers': subreddit.subscribers,
                    'description': subreddit.public_description,
                    'created_utc': subreddit.created_utc,
                    'url': f"https://reddit.com/r/{subreddit_name}"
                }
            
            if self.thread_pool:
                return await loop.run_in_executor(self.thread_pool, _get_info)
            else:
                return await loop.run_in_executor(None, _get_info)
            
        except Exception as e:
            logger.error(f"Failed to get subreddit info: {str(e)}")
            raise RedditAPIException(f"Failed to get subreddit info: {str(e)}")
            
    def _calculate_weighted_scores(self, posts: List[Dict[str, Any]], query_words: List[str]) -> List[Dict[str, Any]]:
        """검색어 일치도 및 기타 요소를 기반으로 가중치 점수 계산"""
        for post in posts:
            relevance_score = 0
            
            # 1. 제목에서 키워드 일치 확인 (가중치 2.0)
            title_lower = post['title'].lower()
            for word in query_words:
                if word.lower() in title_lower:
                    relevance_score += 2.0
            
            # 2. 본문에서 키워드 일치 확인 (가중치 1.0)
            if post.get('selftext'):
                selftext_lower = post['selftext'].lower()
                for word in query_words:
                    if word.lower() in selftext_lower:
                        relevance_score += 1.0
            
            # 3. Reddit 점수 정규화 (0-1 범위로, 가중치 0.5)
            reddit_score = post['score']
            normalized_reddit_score = min(reddit_score / 1000, 1.0) * 0.5
            relevance_score += normalized_reddit_score
            
            # 4. 댓글 수 정규화 (0-1 범위로, 가중치 0.3) 
            comments = post['num_comments']
            normalized_comments = min(comments / 100, 1.0) * 0.3
            relevance_score += normalized_comments
            
            # 5. 최신성 가중치 (24시간 이내면 보너스)
            created_time = datetime.fromtimestamp(post['created_utc'])
            hours_old = (datetime.now() - created_time).total_seconds() / 3600
            if hours_old < 24:
                relevance_score += 0.5
            elif hours_old < 48:
                relevance_score += 0.3
            
            post['weighted_score'] = relevance_score
            
        return posts
    
    async def _check_rate_limit(self):
        """Rate limit 확인 및 대기 (Reddit API: 60 requests/minute)"""
        async with self.rate_limit_lock:
            now = datetime.now()
            
            # 1분 이내의 요청만 유지
            while self.request_timestamps and (now - self.request_timestamps[0]) > timedelta(minutes=1):
                self.request_timestamps.popleft()
            
            # 59개 이상의 요청이 있으면 대기
            if len(self.request_timestamps) >= 59:
                # 가장 오래된 요청으로부터 1분 후까지 대기
                oldest_request = self.request_timestamps[0]
                wait_time = (oldest_request + timedelta(minutes=1) - now).total_seconds()
                
                if wait_time > 0:
                    logger.info(f"⏳ Reddit API Rate limit 도달. {wait_time:.1f}초 대기 중...")
                    await asyncio.sleep(wait_time)
            
            # 현재 요청 시간 기록
            self.request_timestamps.append(now)
    
    async def search_with_keywords(self, keywords: List[str], limit_per_keyword: int = 10) -> List[Dict[str, Any]]:
        """여러 키워드로 검색하여 게시물 수집 (Rate Limit 준수)"""
        all_posts = []
        total_keywords = len(keywords)
        
        logger.info(f"🔍 다중 키워드 검색 시작: {total_keywords}개 키워드")
        logger.info(f"   키워드 목록: {keywords[:5]}{'...' if len(keywords) > 5 else ''}")
        
        for i, keyword in enumerate(keywords):
            try:
                # Rate limit 체크
                await self._check_rate_limit()
                
                # 진행 상황 로그
                logger.info(f"🔎 [{i+1}/{total_keywords}] 키워드 '{keyword}' 검색 중...")
                
                # 실제 검색 수행 (각 키워드당 제한된 수만 수집)
                posts = await self.search_posts(keyword, limit=limit_per_keyword)
                all_posts.extend(posts)
                
                logger.info(f"✅ 키워드 '{keyword}' 검색 완료: {len(posts)}개 수집")
                
                # 진행률 표시
                if (i + 1) % 5 == 0 or (i + 1) == total_keywords:
                    logger.info(f"📊 진행률: {(i+1)/total_keywords*100:.1f}% 완료 ({i+1}/{total_keywords})")
                
            except Exception as e:
                logger.warning(f"⚠️ 키워드 '{keyword}' 검색 실패: {str(e)}")
                
                # Rate limit 에러인 경우 추가 대기
                if "rate limit" in str(e).lower():
                    logger.warning("🚨 Rate limit 에러 감지. 30초 추가 대기...")
                    await asyncio.sleep(30)
                
                continue
        
        logger.info(f"✅ 다중 키워드 검색 완료: 총 {len(all_posts)}개 게시물 수집")
        return all_posts