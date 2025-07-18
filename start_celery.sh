#!/bin/bash

# Celery 워커 시작 스크립트

echo "🚀 Starting Celery Worker..."

# 환경 변수 로드
source venv/bin/activate
export $(cat .env | xargs)

# Celery 워커 시작 (API 호출 큐)
celery -A app.core.celery_app:celery_app worker \
    --loglevel=info \
    --queues=api_calls \
    --concurrency=4 \
    --pool=prefork \
    -n worker1@%h &

# Celery 워커 시작 (디스패처 큐)
celery -A app.core.celery_app:celery_app worker \
    --loglevel=info \
    --queues=dispatcher \
    --concurrency=1 \
    --pool=solo \
    -n dispatcher@%h &

echo "✅ Celery Workers started"
echo "📊 Workers are listening on queues: api_calls, dispatcher"
echo "Press Ctrl+C to stop all workers"

# 종료 시그널 대기
wait