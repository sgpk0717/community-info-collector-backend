from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.router import api_router
import logging
import sys

# 컬러 로깅 설정
class ColoredFormatter(logging.Formatter):
    """컬러 로그 포맷터"""
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

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 명시적으로 stdout 지정
    ],
    force=True  # 기존 로거 설정 덮어쓰기
)

# 루트 로거에 컬러 포맷터 적용
root_logger = logging.getLogger()
for handler in root_logger.handlers:
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
    logger.info("👋 안녕히 가세요!")
    logger.info("="*50)