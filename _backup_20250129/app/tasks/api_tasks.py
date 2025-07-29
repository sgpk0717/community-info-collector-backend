from celery import Task
from app.core.celery_app import celery_app
from app.services.call_queue_service import CallQueueService
from app.services.reddit_service import RedditService
from app.schemas.call_queue import CallQueueStatus
import asyncio
import logging
from typing import Dict, Any
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class APICallTask(Task):
    """API 호출 태스크 기본 클래스"""
    autoretry_for = (aiohttp.ClientError, TimeoutError)
    retry_kwargs = {
        'max_retries': 3,
        'countdown': 60  # 60초 후 재시도
    }

@celery_app.task(base=APICallTask, bind=True)
def make_api_call(self, queue_item_id: str) -> Dict[str, Any]:
    """실제 API 호출을 수행하는 태스크"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(_make_api_call_async(queue_item_id))
        return result
    finally:
        loop.close()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((aiohttp.ClientError, TimeoutError))
)
async def _make_api_call_async(queue_item_id: str) -> Dict[str, Any]:
    """비동기 API 호출 구현"""
    queue_service = CallQueueService()
    reddit_service = RedditService()
    
    try:
        # 큐 항목 조회
        result = queue_service.client.table('call_queue')\
            .select("*")\
            .eq('id', queue_item_id)\
            .single()\
            .execute()
        
        if not result.data:
            raise ValueError(f"Queue item not found: {queue_item_id}")
        
        queue_item = result.data
        
        # 상태를 processing으로 업데이트
        await queue_service.update_status(queue_item_id, CallQueueStatus.PROCESSING)
        
        # Reddit API 호출
        logger.info(f"🔄 API 호출 시작: {queue_item['source_url']}")
        
        # URL에서 필요한 정보 추출하여 Reddit 데이터 수집
        if 'reddit.com' in queue_item['source_url']:
            # 서브레딧 정보 추출
            url_parts = queue_item['source_url'].split('/')
            if 'r' in url_parts:
                subreddit_idx = url_parts.index('r')
                if subreddit_idx + 1 < len(url_parts):
                    subreddit = url_parts[subreddit_idx + 1]
                    
                    # API 파라미터 적용
                    limit = queue_item['api_params'].get('limit', 25)
                    sort = queue_item['api_params'].get('sort', 'hot')
                    
                    # Reddit 서비스를 통해 데이터 수집
                    posts = await reddit_service.get_subreddit_posts(
                        subreddit=subreddit,
                        limit=limit,
                        sort=sort
                    )
                    
                    # 수집된 데이터 저장
                    saved_count = 0
                    for post in posts:
                        # source_contents 테이블에 저장
                        content_data = {
                            'source_id': post.get('id', ''),
                            'source_url': f"https://reddit.com{post.get('permalink', '')}",
                            'raw_text': f"{post.get('title', '')} {post.get('selftext', '')}",
                            'metadata': {
                                'author': post.get('author', ''),
                                'score': post.get('score', 0),
                                'num_comments': post.get('num_comments', 0),
                                'created_utc': post.get('created_utc', 0),
                                'subreddit': post.get('subreddit', ''),
                                'title': post.get('title', ''),
                                'queue_item_id': queue_item_id
                            }
                        }
                        
                        result = queue_service.client.table('source_contents').insert(content_data).execute()
                        if result.data:
                            saved_count += 1
                    
                    # 성공 상태로 업데이트
                    await queue_service.update_status(queue_item_id, CallQueueStatus.COMPLETED)
                    
                    logger.info(f"✅ API 호출 완료: {saved_count}개 게시물 수집")
                    return {
                        'status': 'success',
                        'posts_collected': saved_count,
                        'queue_item_id': queue_item_id
                    }
        
        # Reddit이 아닌 경우 에러
        raise ValueError(f"Unsupported URL: {queue_item['source_url']}")
        
    except Exception as e:
        logger.error(f"❌ API 호출 실패: {str(e)}")
        
        # 재시도 횟수 증가
        await queue_service.increment_retry_count(queue_item_id)
        
        # 에러 상태로 업데이트
        await queue_service.update_status(
            queue_item_id, 
            CallQueueStatus.ERROR,
            error=str(e)
        )
        
        # 재시도를 위해 예외 재발생
        raise