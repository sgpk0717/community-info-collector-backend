FROM python:3.11.9-slim

# Python 버전 확인
RUN python --version

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 복사
COPY requirements.txt .

# pip 업그레이드 및 의존성 설치
RUN python -m pip install --no-cache-dir --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 포트 노출 (환경변수 사용)
EXPOSE $PORT

# 앱 실행 (환경변수 PORT 사용)
CMD python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT