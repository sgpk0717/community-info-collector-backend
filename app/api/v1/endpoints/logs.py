from fastapi import APIRouter, Query, HTTPException
from typing import List
import os
import glob
from collections import deque

router = APIRouter()

@router.get("/logs/tail")
async def tail_logs(
    lines: int = Query(default=100, ge=1, le=10000, description="읽을 로그 라인 수")
):
    """
    최신 로그 파일의 마지막 n개 라인을 반환합니다.
    
    - **lines**: 읽을 로그 라인 수 (1-10000)
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
        
        # tail 구현 - 마지막 n개 라인 읽기
        with open(latest_log, 'r', encoding='utf-8') as file:
            # deque를 사용하여 효율적으로 마지막 n개 라인만 유지
            tail_lines = deque(file, maxlen=lines)
        
        return {
            "filename": os.path.basename(latest_log),
            "lines": lines,
            "content": list(tail_lines)
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
        files_info = []
        
        for file_path in log_files:
            stat = os.stat(file_path)
            files_info.append({
                "filename": os.path.basename(file_path),
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
        
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
        
        # 키워드를 포함하는 라인 찾기
        matching_lines = []
        with open(latest_log, 'r', encoding='utf-8') as file:
            for line in file:
                if keyword.lower() in line.lower():
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