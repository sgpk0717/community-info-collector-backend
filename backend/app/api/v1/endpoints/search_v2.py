from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect
from app.schemas.search import SearchRequest, SearchResponse, ProgressUpdate
from app.schemas.call_queue import CallQueueCreate
from app.services.call_queue_service import CallQueueService
from app.services.analysis_service import AnalysisService
from app.utils.websocket_manager import WebSocketManager
import logging
from uuid import uuid4
from typing import Dict, Any
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# WebSocket 매니저 (진행상황 업데이트용)
websocket_manager = WebSocketManager()

# 진행 상태 저장용 (실제로는 Redis 등 사용 권장)
progress_store: Dict[str, ProgressUpdate] = {}

@router.post("/search-v2", response_model=SearchResponse)
async def search_and_analyze_v2(
    request: SearchRequest,
    background_tasks: BackgroundTasks
):
    """CallQueue를 사용한 개선된 키워드 기반 커뮤니티 분석"""
    try:
        # 세션 ID 생성
        session_id = request.session_id or str(uuid4())
        query_id = str(uuid4())
        
        logger.info(f"🚀 새로운 분석 요청: {request.query}")
        
        # CallQueue에 데이터 수집 작업 추가
        queue_service = CallQueueService()
        
        # Reddit 검색을 위한 큐 항목 생성
        subreddits = ['stocks', 'wallstreetbets', 'investing', 'StockMarket']  # 기본 서브레딧
        queue_items = []
        
        for subreddit in subreddits:
            queue_item = CallQueueCreate(
                source_url=f"https://reddit.com/r/{subreddit}",
                api_params={
                    'query': request.query,
                    'limit': 50,
                    'sort': 'relevance',
                    'time_filter': 'week'
                },
                source_metadata={
                    'session_id': session_id,
                    'query_id': query_id,
                    'user_nickname': request.user_nickname,
                    'report_length': request.length
                }
            )
            
            created_item = await queue_service.create_queue_item(queue_item)
            queue_items.append(created_item)
        
        logger.info(f"📥 {len(queue_items)}개의 수집 작업이 큐에 추가됨")
        
        # 초기 진행상황 업데이트
        initial_update = ProgressUpdate(
            stage="collecting",
            message="데이터 수집을 시작했습니다...",
            progress=5
        )
        progress_store[session_id] = initial_update
        await websocket_manager.send_progress(session_id, initial_update.model_dump())
        
        # 즉시 응답 반환
        response = SearchResponse(
            status="processing",
            session_id=session_id,
            query_id=query_id,
            posts_collected=0,
            estimated_time=180,  # 예상 시간 3분
            message="분석이 시작되었습니다. 진행 상황은 WebSocket을 통해 확인하세요."
        )
        
        # 백그라운드에서 수집 상태 모니터링 및 분석 진행
        background_tasks.add_task(
            monitor_and_analyze,
            queue_items,
            request,
            session_id,
            query_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Search v2 endpoint error: {str(e)}")
        return SearchResponse(
            status="error",
            session_id="",
            query_id="",
            posts_collected=0,
            estimated_time=0,
            message=f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        )

async def monitor_and_analyze(queue_items, request: SearchRequest, session_id: str, query_id: str):
    """수집 상태를 모니터링하고 완료되면 분석 수행"""
    try:
        queue_service = CallQueueService()
        
        # 모든 큐 항목이 완료될 때까지 대기
        total_items = len(queue_items)
        completed_items = 0
        
        while completed_items < total_items:
            await asyncio.sleep(5)  # 5초마다 확인
            
            completed_count = 0
            for item in queue_items:
                # 각 항목의 상태 확인
                result = queue_service.client.table('call_queue')\
                    .select("status")\
                    .eq('id', item.id)\
                    .single()\
                    .execute()
                
                if result.data and result.data.get('status') in ['completed', 'error', 'failed_permanent']:
                    completed_count += 1
            
            if completed_count > completed_items:
                completed_items = completed_count
                progress = int((completed_items / total_items) * 40) + 5  # 5-45% 진행률
                
                await websocket_manager.send_progress(session_id, {
                    'stage': 'collecting',
                    'message': f'데이터 수집 중... ({completed_items}/{total_items})',
                    'progress': progress
                })
        
        # 수집된 데이터 조회
        result = queue_service.client.table('source_contents')\
            .select("*")\
            .eq('metadata->>session_id', session_id)\
            .execute()
        
        collected_posts = result.data if result.data else []
        logger.info(f"📊 총 {len(collected_posts)}개의 게시물 수집 완료")
        
        # 진행상황 업데이트: 분석 시작
        await websocket_manager.send_progress(session_id, {
            'stage': 'analyzing',
            'message': '수집된 데이터를 분석하고 있습니다...',
            'progress': 50
        })
        
        # 여기서 Phase 2, 3, 4의 분석 프로세스를 호출할 예정
        # 현재는 기존 분석 서비스 사용
        analysis_service = AnalysisService()
        
        # 수집된 데이터를 기존 형식으로 변환
        posts_for_analysis = []
        for post in collected_posts:
            posts_for_analysis.append({
                'id': post['source_id'],
                'title': post['metadata'].get('title', ''),
                'selftext': post['raw_text'],
                'author': post['metadata'].get('author', ''),
                'score': post['metadata'].get('score', 0),
                'num_comments': post['metadata'].get('num_comments', 0),
                'created_utc': post['metadata'].get('created_utc', 0),
                'subreddit': post['metadata'].get('subreddit', ''),
                'permalink': post['source_url']
            })
        
        # 기존 분석 서비스로 보고서 생성 (추후 멀티 에이전트로 교체)
        if posts_for_analysis:
            # 임시로 request 객체 수정
            modified_request = SearchRequest(
                query=request.query,
                sources=request.sources,
                user_nickname=request.user_nickname,
                session_id=session_id,
                push_token=request.push_token,
                length=request.length
            )
            
            # progress 콜백 정의
            async def update_progress(message: str, progress: int):
                await websocket_manager.send_progress(session_id, {
                    'stage': 'analyzing',
                    'message': message,
                    'progress': 50 + int(progress * 0.5)  # 50-100% 범위
                })
            
            # 분석 수행
            result = await analysis_service.process_search_request(modified_request, update_progress)
            
            # 완료 메시지
            await websocket_manager.send_progress(session_id, {
                'stage': 'completed',
                'message': '분석이 완료되었습니다!',
                'progress': 100
            })
        else:
            await websocket_manager.send_progress(session_id, {
                'stage': 'completed',
                'message': '수집된 데이터가 없습니다.',
                'progress': 100
            })
            
    except Exception as e:
        logger.error(f"Monitor and analyze error: {str(e)}")
        await websocket_manager.send_progress(session_id, {
            'stage': 'error',
            'message': f'분석 중 오류가 발생했습니다: {str(e)}',
            'progress': 0
        })

@router.websocket("/ws/progress/{session_id}")
async def websocket_progress(websocket: WebSocket, session_id: str):
    """진행 상황 실시간 업데이트용 WebSocket"""
    await websocket_manager.connect(session_id, websocket)
    try:
        # 현재 진행 상태가 있다면 즉시 전송
        if session_id in progress_store:
            await websocket.send_json(progress_store[session_id].model_dump())
        
        # 연결 유지
        while True:
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(session_id)