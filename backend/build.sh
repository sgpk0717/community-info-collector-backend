#!/bin/bash
set -e

echo "🚀 Render 배포 시작..."

# pip 업그레이드
python -m pip install --upgrade pip setuptools wheel

# 의존성 설치 (캐시 사용 안함)
pip install --no-cache-dir --upgrade -r requirements.txt

echo "✅ 빌드 완료!"