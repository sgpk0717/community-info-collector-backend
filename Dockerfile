FROM python:3.11.9-slim

# 빌드 시간 최적화를 위한 환경변수
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 (캐시 활용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일만 먼저 복사 (캐시 최적화)
COPY requirements.txt .

# pip 업그레이드 및 의존성 설치
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# 소스 코드 복사 (의존성 변경 없으면 캐시 사용)
COPY . .

# 포트 노출 (환경변수 사용)
EXPOSE $PORT

# 앱 실행 (환경변수 PORT 사용)
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT