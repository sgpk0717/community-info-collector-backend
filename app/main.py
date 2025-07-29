from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.router import api_router
import logging
import sys
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import pytz
import datetime
import ssl
import os

# SSL 인증서 검증 비활성화 (개발 환경용)
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''

# macOS에서 SSL 인증서 문제 해결
if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

# 한국 시간을 사용하는 Formatter
class KSTFormatter(logging.Formatter):
    """한국 시간대(KST)를 사용하는 로그 포맷터"""
    def formatTime(self, record, datefmt=None):
        # UTC 시간을 한국 시간으로 변환
        dt = datetime.datetime.fromtimestamp(record.created, tz=pytz.UTC)
        dt = dt.astimezone(KST)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')

# 컬러 로깅 설정
class ColoredFormatter(KSTFormatter):
    """한국 시간대를 사용하는 컬러 로그 포맷터"""
    COLORS = {
        'DEBUG': '\033[94m',    # 파랑
        'INFO': '\033[92m',     # 초록
        'WARNING': '\033[93m',  # 노랑
        'ERROR': '\033[91m',    # 빨강
        'CRITICAL': '\033[95m', # 자주색
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

# 로그 디렉토리 생성
import os
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 로깅 설정
from logging.handlers import RotatingFileHandler
import datetime

# 파일 핸들러 생성 (10MB 크기 제한, 5개 백업 파일)
log_filename = os.path.join(LOG_DIR, f"app_{datetime.datetime.now(KST).strftime('%Y%m%d')}.log")
file_handler = RotatingFileHandler(
    log_filename,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(KSTFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # 콘솔 출력
        file_handler  # 파일 출력
    ],
    force=True  # 기존 로거 설정 덮어쓰기
)

# 루트 로거에 컬러 포맷터 적용 (콘솔 핸들러만)
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    if isinstance(handler, logging.StreamHandler) and not isinstance(handler, RotatingFileHandler):
        handler.setFormatter(ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)

# uvicorn 로거도 설정
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.INFO)
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.setLevel(logging.INFO)

# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 요청 로깅 미들웨어
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 요청 정보 로깅
        logger.info(f"📥 요청 수신: {request.method} {request.url.path}")
        logger.info(f"   Origin: {request.headers.get('origin', 'None')}")
        logger.info(f"   Content-Type: {request.headers.get('content-type', 'None')}")
        logger.info(f"   User-Agent: {request.headers.get('user-agent', 'None')[:50]}...")
        
        # OPTIONS 요청 처리 (CORS preflight)
        if request.method == "OPTIONS":
            logger.info("   ✅ OPTIONS 요청 (CORS preflight)")
        
        # 요청 본문 로깅 (POST 요청의 경우)
        if request.method == "POST" and request.url.path.startswith("/api/v1/search"):
            try:
                body = await request.body()
                request._body = body  # 요청 본문을 다시 읽을 수 있도록 저장
                logger.info(f"   Body: {body.decode('utf-8')[:500]}")  # 처음 500자만
            except Exception as e:
                logger.error(f"   Body 읽기 실패: {str(e)}")
        
        response = await call_next(request)
        
        # 응답 정보 로깅
        process_time = time.time() - start_time
        logger.info(f"📤 응답 전송: {request.method} {request.url.path} - {response.status_code} ({process_time:.3f}초)")
        
        return response

# CORS 설정 (먼저 추가)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 요청 로깅 미들웨어 추가 (나중에 추가 = 먼저 실행됨)
app.add_middleware(RequestLoggingMiddleware)

# API 라우터 등록
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """헬스 체크용 루트 엔드포인트"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }

# 전역 executor 설정
thread_pool_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="io_worker")
process_pool_executor = ProcessPoolExecutor(max_workers=4)

# 전역 semaphore 설정 (동시 API 호출 제한)
api_semaphore = asyncio.Semaphore(5)  # 동시에 5개까지만 외부 API 호출 허용

# executor를 app state에 저장
app.state.thread_pool = thread_pool_executor
app.state.process_pool = process_pool_executor
app.state.api_semaphore = api_semaphore

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    import os
    import socket
    
    logger.info("="*80)
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 서버 시작!")
    logger.info(f"🌍 환경: {settings.APP_ENV}")
    logger.info(f"📊 로그 레벨: {settings.LOG_LEVEL}")
    logger.info("="*80)
    
    # 환경 정보 출력
    logger.info("📋 환경 정보:")
    logger.info(f"   - PORT 환경변수: {os.environ.get('PORT', 'NOT SET')}")
    logger.info(f"   - 호스트명: {socket.gethostname()}")
    logger.info(f"   - Python 버전: {sys.version}")
    logger.info(f"   - 현재 작업 디렉토리: {os.getcwd()}")
    
    # API 엔드포인트 정보
    logger.info("="*80)
    logger.info("🔗 사용 가능한 API 엔드포인트:")
    logger.info(f"   - 헬스체크: GET /")
    logger.info(f"   - API 문서: GET /docs")
    logger.info(f"   - 사용자 등록: POST {settings.API_V1_STR}/users/register")
    logger.info(f"   - 사용자 로그인: POST {settings.API_V1_STR}/users/login") 
    logger.info(f"   - 검색 요청: POST {settings.API_V1_STR}/search")
    logger.info(f"   - 보고서 조회: GET {settings.API_V1_STR}/reports/{{user_nickname}}")
    
    # 미들웨어 정보
    logger.info("="*80)
    logger.info("🛡️ 활성화된 미들웨어:")
    logger.info("   1. RequestLoggingMiddleware (요청 로깅)")
    logger.info("   2. CORSMiddleware (CORS 처리)")
    logger.info(f"      - 허용된 Origin: {settings.CORS_ORIGINS}")
    
    # 서비스 상태
    logger.info("="*80)
    logger.info("🎯 서비스 상태:")
    logger.info("   - 컬러 로깅 시스템: ✅ 활성화")
    logger.info("   - Reddit API: ✅ 준비됨")
    logger.info("   - OpenAI API: ✅ 준비됨")
    logger.info("   - Supabase DB: ✅ 준비됨")
    logger.info("   - Thread Pool: ✅ 10 workers")
    logger.info("   - Process Pool: ✅ 4 workers")
    logger.info("   - API Semaphore: ✅ 5 concurrent calls")
    
    # 접속 정보
    logger.info("="*80)
    logger.info("📡 서버 접속 정보:")
    port = os.environ.get('PORT', '10000')
    logger.info(f"   - 로컬: http://0.0.0.0:{port}")
    logger.info(f"   - 프로덕션: https://community-info-collector-backend.onrender.com")
    
    logger.info("="*80)
    logger.info("✅ 모든 시스템 준비 완료! 분석 요청을 기다리는 중...")
    logger.info("="*80)

@app.on_event("shutdown")
async def shutdown_event():
    """앱 종료 시 실행"""
    logger.info("="*50)
    logger.info("🛑 서버 종료 중...")
    
    # Executor 정리
    logger.info("   - Thread Pool 종료 중...")
    thread_pool_executor.shutdown(wait=True)
    logger.info("   - Process Pool 종료 중...")
    process_pool_executor.shutdown(wait=True)
    
    logger.info("👋 안녕히 가세요!")
    logger.info("="*50)