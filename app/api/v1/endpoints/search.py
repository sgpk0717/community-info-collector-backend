from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect
from app.schemas.search import SearchRequest, SearchResponse, ProgressUpdate
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

@router.post("/search", response_model=SearchResponse)
async def search_and_analyze(
    request: SearchRequest,
    background_tasks: BackgroundTasks
):
    """키워드 기반 커뮤니티 분석 요청"""
    logger.info(f"🔍 검색 요청 수신 - 키워드: {request.query}, 사용자: {request.user_nickname}")
    logger.info(f"   소스: {request.sources}, 길이: {request.length}")
    
    try:
        # 세션 ID 생성 (클라이언트가 제공하지 않은 경우)
        session_id = request.session_id or str(uuid4())
        query_id = str(uuid4())
        
        # 즉시 응답 반환
        response = SearchResponse(
            status="processing",
            session_id=session_id,
            query_id=query_id,
            posts_collected=0,
            estimated_time=120,  # 예상 시간 2분
            message="분석을 시작했습니다. 진행 상황은 WebSocket을 통해 확인하세요."
        )
        
        # 백그라운드 작업 추가
        background_tasks.add_task(
            process_analysis_task,
            request,
            session_id,
            query_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Search endpoint error: {str(e)}")
        return SearchResponse(
            status="error",
            session_id="",
            query_id="",
            posts_collected=0,
            estimated_time=0,
            message=f"요청 처리 중 오류가 발생했습니다: {str(e)}"
        )

async def process_analysis_task(request: SearchRequest, session_id: str, query_id: str):
    """백그라운드에서 실제 분석 수행"""
    logger.info(f"🚀 백그라운드 분석 시작 - 세션: {session_id}, 쿼리: {query_id}")
    logger.info(f"   키워드: {request.query}, 사용자: {request.user_nickname}")
    
    try:
        analysis_service = AnalysisService()
        
        # 진행상황 업데이트 콜백
        async def update_progress(message: str, progress: int):
            update = ProgressUpdate(
                stage="analyzing" if progress < 100 else "completed",
                message=message,
                progress=progress
            )
            
            # 진행 상태 저장
            progress_store[session_id] = update
            
            # WebSocket으로 전송
            await websocket_manager.send_progress(session_id, update.model_dump())
        
        # 분석 수행
        result = await analysis_service.process_search_request(request, update_progress)
        
        # 완료 메시지
        final_update = ProgressUpdate(
            stage="completed",
            message="분석이 완료되었습니다",
            progress=100
        )
        progress_store[session_id] = final_update
        await websocket_manager.send_progress(session_id, final_update.model_dump())
        
        # 푸시 알림 발송 (구현 필요)
        if request.push_token:
            # TODO: 푸시 알림 서비스 구현
            pass
            
    except Exception as e:
        logger.error(f"Background analysis error: {str(e)}")
        
        # 에러 상태 업데이트
        error_update = ProgressUpdate(
            stage="error",
            message=f"분석 중 오류 발생: {str(e)}",
            progress=0
        )
        progress_store[session_id] = error_update
        await websocket_manager.send_progress(session_id, error_update.model_dump())

@router.websocket("/ws/progress/{session_id}")
async def websocket_progress(websocket: WebSocket, session_id: str):
    """진행 상황 WebSocket 연결"""
    await websocket_manager.connect(session_id, websocket)
    
    try:
        # 현재 진행 상태가 있으면 즉시 전송
        if session_id in progress_store:
            await websocket.send_json(progress_store[session_id].model_dump())
        
        # 연결 유지
        while True:
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        websocket_manager.disconnect(session_id)