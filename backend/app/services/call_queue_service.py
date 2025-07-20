from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from app.schemas.call_queue import CallQueue, CallQueueCreate, CallQueueStatus
from app.core.dependencies import get_supabase_client
from app.core.exceptions import SupabaseException

logger = logging.getLogger(__name__)

class CallQueueService:
    def __init__(self):
        self.client = get_supabase_client()
    
    async def create_queue_item(self, item: CallQueueCreate) -> CallQueue:
        """API 호출 큐에 새 항목 추가"""
        try:
            queue_item = CallQueue(
                source_url=item.source_url,
                api_params=item.api_params,
                source_metadata=item.source_metadata
            )
            
            data = queue_item.model_dump()
            data['created_at'] = data['created_at'].isoformat()
            
            result = self.client.table('call_queue').insert(data).execute()
            
            if result.data:
                logger.info(f"📥 큐 항목 생성: {result.data[0]['id']}")
                return CallQueue(**result.data[0])
            else:
                raise SupabaseException("Failed to create queue item")
                
        except Exception as e:
            logger.error(f"큐 항목 생성 실패: {str(e)}")
            raise SupabaseException(f"Failed to create queue item: {str(e)}")
    
    async def get_pending_items(self, limit: int = 10) -> List[CallQueue]:
        """처리 대기 중인 항목들 조회"""
        try:
            result = self.client.table('call_queue')\
                .select("*")\
                .eq('status', CallQueueStatus.PENDING.value)\
                .order('created_at', desc=False)\
                .limit(limit)\
                .execute()
            
            return [CallQueue(**item) for item in result.data] if result.data else []
            
        except Exception as e:
            logger.error(f"대기 항목 조회 실패: {str(e)}")
            raise SupabaseException(f"Failed to get pending items: {str(e)}")
    
    async def update_status(self, item_id: str, status: CallQueueStatus, 
                          error: Optional[str] = None) -> bool:
        """큐 항목 상태 업데이트"""
        try:
            update_data = {
                'status': status.value,
                'updated_at': datetime.now().isoformat()
            }
            
            if status == CallQueueStatus.PROCESSING:
                update_data['scheduled_at'] = datetime.now().isoformat()
            elif status in [CallQueueStatus.COMPLETED, CallQueueStatus.ERROR]:
                update_data['completed_at'] = datetime.now().isoformat()
            
            if error:
                update_data['last_error'] = error
            
            result = self.client.table('call_queue')\
                .update(update_data)\
                .eq('id', item_id)\
                .execute()
            
            if result.data:
                logger.info(f"✅ 큐 항목 상태 업데이트: {item_id} -> {status.value}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"상태 업데이트 실패: {str(e)}")
            return False
    
    async def increment_retry_count(self, item_id: str) -> bool:
        """재시도 횟수 증가"""
        try:
            # 먼저 현재 값을 조회
            result = self.client.table('call_queue')\
                .select("retry_count")\
                .eq('id', item_id)\
                .single()\
                .execute()
            
            if result.data:
                current_count = result.data.get('retry_count', 0)
                
                # 재시도 횟수 증가
                update_result = self.client.table('call_queue')\
                    .update({'retry_count': current_count + 1})\
                    .eq('id', item_id)\
                    .execute()
                
                return bool(update_result.data)
            return False
            
        except Exception as e:
            logger.error(f"재시도 횟수 증가 실패: {str(e)}")
            return False