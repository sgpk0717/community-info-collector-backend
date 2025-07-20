import praw
from typing import List, Dict, Any, Optional
from app.core.dependencies import get_reddit_client
from app.core.exceptions import RedditAPIException
import logging
from datetime import datetime
import asyncio
import re

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
    def __init__(self):
        self.client = get_reddit_client()
    
    def _calculate_rumor_score(self, submission) -> float:
        """루머 점수 계산 (0-10 범위)"""
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
    
    def _extract_linguistic_flags(self, text: str) -> List[str]:
        """언어학적 신호 플래그 추출"""
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
        
    async def search_posts(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Reddit에서 키워드로 게시물 검색 - 다중 벡터 수집 전략"""
        try:
            logger.info(f"🔍 Reddit 검색 시작: '{query}' (최대 {limit}개 게시물)")
            posts = []
            
            # Reddit API는 동기식이므로 asyncio의 run_in_executor 사용
            loop = asyncio.get_event_loop()
            
            def _search():
                # 다중 벡터 수집 전략
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
                        
                        vector_count = 0
                        for submission in search_results:
                            # 수집 벡터 정보 추가
                            submission._collection_vector = vector['name']
                            all_submissions.append(submission)
                            vector_count += 1
                            
                        logger.info(f"✅ 벡터 '{vector['name']}' 완료 - {vector_count}개 게시물 수집")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ 벡터 '{vector['name']}' 검색 실패: {str(e)}")
                        continue
                
                logger.info(f"📝 게시물 분석 및 중복 제거 시작 - 총 {len(all_submissions)}개 게시물")
                
                # 중복 제거 및 포맷팅
                seen_ids = set()
                processed_count = 0
                
                for submission in all_submissions:
                    if submission.id not in seen_ids:
                        seen_ids.add(submission.id)
                        
                        # 루머 점수 계산
                        rumor_score = self._calculate_rumor_score(submission)
                        
                        # 언어학적 플래그 추출
                        text_to_analyze = submission.title + ' ' + (submission.selftext or '')
                        linguistic_flags = self._extract_linguistic_flags(text_to_analyze)
                        
                        post_data = {
                            'id': submission.id,
                            'title': submission.title,
                            'selftext': submission.selftext[:1000] if submission.selftext else '',
                            'score': submission.score,
                            'upvote_ratio': submission.upvote_ratio,
                            'num_comments': submission.num_comments,
                            'created_utc': datetime.fromtimestamp(submission.created_utc).isoformat(),
                            'subreddit': submission.subreddit.display_name,
                            'author': str(submission.author) if submission.author else '[deleted]',
                            'url': f"https://reddit.com{submission.permalink}",
                            'is_self': submission.is_self,
                            # 새로 추가된 필드들
                            'collection_vector': getattr(submission, '_collection_vector', 'unknown'),
                            'rumor_score': round(rumor_score, 1),
                            'linguistic_flags': linguistic_flags
                        }
                        
                        posts.append(post_data)
                        processed_count += 1
                        
                        # 진행상황 로그 (10개마다)
                        if processed_count % 10 == 0:
                            logger.info(f"⏳ 게시물 처리 중... ({processed_count}/{len(all_submissions)})")
                        
                        if len(posts) >= limit:
                            break
                
                # 수집된 게시물 통계 로그
                vector_stats = {}
                for post in posts:
                    vector = post['collection_vector']
                    vector_stats[vector] = vector_stats.get(vector, 0) + 1
                
                logger.info(f"📊 벡터별 수집 통계: {vector_stats}")
                
                return posts
            
            # 동기 함수를 비동기로 실행
            posts = await loop.run_in_executor(None, _search)
            
            logger.info(f"🎉 Reddit 검색 완료 - 총 {len(posts)}개 게시물 수집")
            return posts
            
        except Exception as e:
            logger.error(f"❌ Reddit API 오류: {str(e)}")
            raise RedditAPIException(f"Failed to search Reddit: {str(e)}")
    
    async def get_post_comments(self, post_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """특정 게시물의 댓글 가져오기 - 루머 점수 포함"""
        try:
            logger.info(f"💬 댓글 가져오기 시작: {post_id} (최대 {limit}개)")
            comments = []
            
            loop = asyncio.get_event_loop()
            
            def _get_comments():
                submission = self.client.submission(id=post_id)
                submission.comments.replace_more(limit=0)  # 'load more comments' 제거
                
                logger.info(f"🔄 댓글 분석 시작...")
                
                comment_list = []
                processed_count = 0
                
                for comment in submission.comments.list()[:limit]:
                    if hasattr(comment, 'body'):
                        # 댓글 루머 점수 계산
                        comment_rumor_score = self._calculate_comment_rumor_score(comment)
                        
                        # 언어학적 플래그 추출
                        linguistic_flags = self._extract_linguistic_flags(comment.body)
                        
                        comment_data = {
                            'id': comment.id,
                            'body': comment.body[:500],  # 댓글 내용 제한
                            'score': comment.score,
                            'created_utc': datetime.fromtimestamp(comment.created_utc).isoformat(),
                            'author': str(comment.author) if comment.author else '[deleted]',
                            # 새로 추가된 필드들
                            'is_controversial': getattr(comment, 'controversiality', 0) == 1,
                            'rumor_score': round(comment_rumor_score, 1),
                            'linguistic_flags': linguistic_flags
                        }
                        comment_list.append(comment_data)
                        processed_count += 1
                        
                        # 높은 루머 점수 댓글 알림
                        if comment_rumor_score >= 7.0:
                            logger.warning(f"🚨 높은 루머 점수 댓글 발견 [{comment_rumor_score:.1f}/10]: {comment.body[:50]}...")
                
                logger.info(f"✅ 댓글 분석 완료 - {processed_count}개 댓글 처리")
                return comment_list
            
            comments = await loop.run_in_executor(None, _get_comments)
            
            logger.info(f"💬 댓글 가져오기 완료 - {len(comments)}개 댓글")
            return comments
            
        except Exception as e:
            logger.error(f"❌ 댓글 가져오기 실패 {post_id}: {str(e)}")
            return []
    
    def _calculate_comment_rumor_score(self, comment) -> float:
        """댓글 루머 점수 계산"""
        score = 0.0
        
        # 1. 논란성 지표
        if hasattr(comment, 'controversiality') and comment.controversiality == 1:
            score += 3.0
        
        # 2. 언어학적 신호 탐지
        text = comment.body.lower()
        
        # 추측성 단어 개수
        speculation_count = sum(1 for word in SPECULATIVE_WORDS if word in text)
        score += min(speculation_count * 1.5, 3.0)
        
        # 부정적 감정 단어 개수
        negative_count = sum(1 for word in NEGATIVE_EMOTION_WORDS if word in text)
        score += min(negative_count * 1.0, 2.0)
        
        # 3. 댓글 특성
        if hasattr(comment, 'score') and comment.score < 0:
            score += 1.0  # 부정적인 점수
        
        return min(score, 10.0)
    
    async def search_with_keywords(self, keywords: List[str], limit_per_keyword: int = 10) -> List[Dict[str, Any]]:
        """여러 키워드로 검색 (확장된 키워드 사용)"""
        logger.info(f"🔍 다중 키워드 검색 시작: {keywords} (키워드당 최대 {limit_per_keyword}개)")
        
        all_posts = []
        seen_ids = set()
        
        for i, keyword in enumerate(keywords):
            try:
                logger.info(f"🎯 키워드 {i+1}/{len(keywords)} 검색: '{keyword}'")
                posts = await self.search_posts(keyword, limit=limit_per_keyword)
                
                new_posts = 0
                for post in posts:
                    if post['id'] not in seen_ids:
                        seen_ids.add(post['id'])
                        all_posts.append(post)
                        new_posts += 1
                        
                logger.info(f"✅ 키워드 '{keyword}' 완료 - {new_posts}개 새로운 게시물 추가")
                        
            except Exception as e:
                logger.warning(f"⚠️ 키워드 '{keyword}' 검색 실패: {str(e)}")
                continue
        
        # 점수 기준으로 정렬
        all_posts.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"🎉 다중 키워드 검색 완료 - 총 {len(all_posts)}개 게시물 (중복 제거됨)")
        return all_posts