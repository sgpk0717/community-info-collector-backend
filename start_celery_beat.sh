#!/bin/bash

# Celery Beat 스케줄러 시작 스크립트

echo "🕐 Starting Celery Beat Scheduler..."

# 환경 변수 로드
source venv/bin/activate
export $(cat .env | xargs)

# Celery Beat 시작
celery -A app.core.celery_app:celery_app beat \
    --loglevel=info

echo "✅ Celery Beat started"