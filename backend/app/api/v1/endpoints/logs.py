from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
import os
import glob
from collections import deque
import aiofiles
import asyncio

router = APIRouter()

async def read_last_n_lines(file_path: str, n: int, offset: int = 0) -> tuple[List[str], int]:
    """
    대용량 파일에서도 효율적으로 마지막 n개 라인을 읽습니다.
    파일 끝에서부터 청크 단위로 읽어서 메모리 효율성을 높입니다.
    """
    chunk_size = 8192  # 8KB chunks
    lines = deque(maxlen=n + offset)
    
    async with aiofiles.open(file_path, 'rb') as file:
        # 파일 크기 구하기
        await file.seek(0, 2)  # 파일 끝으로 이동
        file_size = await file.tell()
        
        if file_size == 0:
            return [], 0
        
        # 파일 끝에서부터 청크 단위로 읽기
        position = file_size
        buffer = b""
        
        while position > 0 and len(lines) < n + offset:
            # 읽을 크기 계산
            read_size = min(chunk_size, position)
            position -= read_size
            
            # 해당 위치로 이동하여 읽기
            await file.seek(position)
            chunk = await file.read(read_size)
            
            # 버퍼에 추가 (역순)
            buffer = chunk + buffer
            
            # 라인 단위로 분리
            while b'\n' in buffer:
                line_end = buffer.rfind(b'\n')
                line = buffer[line_end + 1:]
                if line:  # 빈 라인이 아니면
                    try:
                        lines.appendleft(line.decode('utf-8').rstrip())
                    except UnicodeDecodeError:
                        # 깨진 문자 무시
                        pass
                buffer = buffer[:line_end]
        
        # 남은 버퍼 처리
        if buffer and len(lines) < n + offset:
            try:
                lines.appendleft(buffer.decode('utf-8').rstrip())
            except UnicodeDecodeError:
                pass
    
    # offset 적용
    result_lines = list(lines)
    if offset > 0:
        result_lines = result_lines[:-offset] if len(result_lines) > offset else []
    
    return result_lines[-n:], len(lines)

@router.get("/logs/tail")
async def tail_logs(
    lines: int = Query(default=100, ge=1, le=10000, description="읽을 로그 라인 수"),
    offset: int = Query(default=0, ge=0, description="끝에서부터의 오프셋 (0이면 가장 최신)")
):
    """
    최신 로그 파일의 마지막 n개 라인을 반환합니다.
    대용량 파일에서도 효율적으로 작동합니다.
    
    - **lines**: 읽을 로그 라인 수 (1-10000)
    - **offset**: 끝에서부터의 오프셋 (0이면 가장 최신)
    """
    try:
        # 로그 디렉토리 확인
        log_dir = "logs"
        if not os.path.exists(log_dir):
            raise HTTPException(status_code=404, detail="로그 디렉토리가 존재하지 않습니다")
        
        # 가장 최신 로그 파일 찾기
        log_files = glob.glob(os.path.join(log_dir, "app_*.log"))
        if not log_files:
            raise HTTPException(status_code=404, detail="로그 파일이 존재하지 않습니다")
        
        # 파일명으로 정렬 (최신 파일이 마지막)
        log_files.sort()
        latest_log = log_files[-1]
        
        # 효율적으로 마지막 라인들 읽기
        selected_lines, total_lines = await read_last_n_lines(latest_log, lines, offset)
        
        return {
            "filename": os.path.basename(latest_log),
            "lines": len(selected_lines),
            "offset": offset,
            "total_lines": total_lines,
            "content": selected_lines
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="로그 파일을 찾을 수 없습니다")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 읽기 실패: {str(e)}")

@router.get("/logs/files")
async def list_log_files():
    """
    사용 가능한 모든 로그 파일 목록을 반환합니다.
    """
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            return {"files": []}
        
        log_files = glob.glob(os.path.join(log_dir, "app_*.log*"))
        
        # 비동기로 파일 정보 수집
        async def get_file_info(file_path):
            loop = asyncio.get_event_loop()
            stat = await loop.run_in_executor(None, os.stat, file_path)
            return {
                "filename": os.path.basename(file_path),
                "size": stat.st_size,
                "modified": stat.st_mtime
            }
        
        files_info = await asyncio.gather(*[get_file_info(fp) for fp in log_files])
        
        # 수정 시간 기준으로 정렬 (최신 파일이 첫 번째)
        files_info.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"files": files_info}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 목록 조회 실패: {str(e)}")

@router.get("/logs/search")
async def search_logs(
    keyword: str = Query(..., description="검색할 키워드"),
    lines: int = Query(default=100, ge=1, le=10000, description="반환할 최대 라인 수")
):
    """
    로그 파일에서 특정 키워드를 검색합니다.
    스트리밍 방식으로 메모리 효율적으로 처리합니다.
    """
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            raise HTTPException(status_code=404, detail="로그 디렉토리가 존재하지 않습니다")
        
        # 가장 최신 로그 파일 찾기
        log_files = glob.glob(os.path.join(log_dir, "app_*.log"))
        if not log_files:
            raise HTTPException(status_code=404, detail="로그 파일이 존재하지 않습니다")
        
        log_files.sort()
        latest_log = log_files[-1]
        
        # 비동기로 키워드를 포함하는 라인 찾기
        matching_lines = []
        keyword_lower = keyword.lower()
        
        async with aiofiles.open(latest_log, 'r', encoding='utf-8') as file:
            async for line in file:
                if keyword_lower in line.lower():
                    matching_lines.append(line.rstrip())
                    if len(matching_lines) >= lines:
                        break
        
        return {
            "filename": os.path.basename(latest_log),
            "keyword": keyword,
            "found": len(matching_lines),
            "content": matching_lines
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 검색 실패: {str(e)}")

@router.get("/logs/stream")
async def stream_logs(
    lines: int = Query(default=50, ge=1, le=1000, description="스트리밍할 초기 라인 수")
):
    """
    로그를 실시간으로 스트리밍합니다. (Server-Sent Events)
    """
    from fastapi.responses import StreamingResponse
    import json
    
    async def log_streamer():
        log_dir = "logs"
        log_files = glob.glob(os.path.join(log_dir, "app_*.log"))
        if not log_files:
            yield f"data: {json.dumps({'error': '로그 파일이 없습니다'})}\n\n"
            return
        
        log_files.sort()
        latest_log = log_files[-1]
        
        # 초기 라인들 전송
        initial_lines, _ = await read_last_n_lines(latest_log, lines)
        for line in initial_lines:
            yield f"data: {json.dumps({'line': line})}\n\n"
        
        # 파일 변경 감지 및 새 라인 전송
        last_position = os.path.getsize(latest_log)
        
        while True:
            await asyncio.sleep(1)  # 1초마다 확인
            
            current_size = os.path.getsize(latest_log)
            if current_size > last_position:
                async with aiofiles.open(latest_log, 'r', encoding='utf-8') as file:
                    await file.seek(last_position)
                    async for line in file:
                        yield f"data: {json.dumps({'line': line.rstrip()})}\n\n"
                last_position = current_size
    
    return StreamingResponse(
        log_streamer(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )