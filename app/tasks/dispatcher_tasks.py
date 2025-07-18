from app.core.celery_app import celery_app
from app.services.call_queue_service import CallQueueService
from app.tasks.api_tasks import make_api_call
import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@celery_app.task
def dispatch_pending_calls():
    """대기 중인 API 호출을 디스패치하는 태스크"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(_dispatch_pending_calls_async())
        return result
    finally:
        loop.close()

async def _dispatch_pending_calls_async():
    """비동기 디스패처 구현"""
    queue_service = CallQueueService()
    
    try:
        # API 속도 제한: 분당 60회 = 초당 1회
        MAX_CALLS_PER_SECOND = 1
        
        # 대기 중인 항목 조회
        pending_items = await queue_service.get_pending_items(limit=MAX_CALLS_PER_SECOND)
        
        if not pending_items:
            logger.debug("대기 중인 API 호출이 없습니다")
            return {'dispatched': 0}
        
        dispatched_count = 0
        
        # 각 항목을 Celery 태스크로 전송
        for item in pending_items:
            try:
                # make_api_call 태스크를 큐에 전송
                make_api_call.apply_async(
                    args=[item.id],
                    queue='api_calls',
                    countdown=dispatched_count  # 순차적 실행을 위한 지연
                )
                
                logger.info(f"📤 태스크 디스패치: {item.id}")
                dispatched_count += 1
                
            except Exception as e:
                logger.error(f"태스크 디스패치 실패: {str(e)}")
                continue
        
        return {
            'dispatched': dispatched_count,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"디스패처 오류: {str(e)}")
        return {'error': str(e)}

@celery_app.task
def cleanup_old_completed_tasks():
    """오래된 완료된 태스크 정리"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(_cleanup_old_tasks_async())
        return result
    finally:
        loop.close()

async def _cleanup_old_tasks_async():
    """30일 이상 지난 완료된 태스크 삭제"""
    queue_service = CallQueueService()
    
    try:
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        result = queue_service.client.table('call_queue')\
            .delete()\
            .eq('status', 'completed')\
            .lt('completed_at', cutoff_date)\
            .execute()
        
        deleted_count = len(result.data) if result.data else 0
        logger.info(f"🗑️ {deleted_count}개의 오래된 태스크 삭제됨")
        
        return {'deleted': deleted_count}
        
    except Exception as e:
        logger.error(f"정리 작업 실패: {str(e)}")
        return {'error': str(e)}