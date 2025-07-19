from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.router import api_router
import logging

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
        logging.StreamHandler()
    ]
)

# 루트 로거에 컬러 포맷터 적용
root_logger = logging.getLogger()
for handler in root_logger.handlers:
    handler.setFormatter(ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)

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

# 요청 로깅 미들웨어 추가
app.add_middleware(RequestLoggingMiddleware)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    logger.info("="*80)
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 서버 시작!")
    logger.info(f"🌍 환경: {settings.APP_ENV}")
    logger.info(f"📊 로그 레벨: {settings.LOG_LEVEL}")
    logger.info("="*80)
    logger.info("🎯 컬러 로깅 시스템 활성화됨")
    logger.info("🔍 Reddit API 연결 준비됨")
    logger.info("🤖 OpenAI API 연결 준비됨")
    logger.info("💾 Supabase 데이터베이스 연결 준비됨")
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