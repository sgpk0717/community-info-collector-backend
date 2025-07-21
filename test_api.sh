#!/bin/bash

# Community Info Collector API 테스트 스크립트

API_BASE_URL="https://community-info-collector-backend.onrender.com"
# API_BASE_URL="http://localhost:8000"  # 로컬 테스트용

echo "======================================"
echo "Community Info Collector API 테스트"
echo "======================================"
echo ""

# 1. 헬스체크
echo "1. 헬스체크 테스트"
echo "-------------------"
curl -X GET "$API_BASE_URL/" \
  -H "Content-Type: application/json" | python3 -m json.tool
echo ""
echo ""

# 2. 사용자 등록
echo "2. 사용자 등록 테스트"
echo "-------------------"
NICKNAME="test_user_$(date +%s)"
echo "닉네임: $NICKNAME"
curl -X POST "$API_BASE_URL/api/v1/users/register" \
  -H "Content-Type: application/json" \
  -d "{\"user_nickname\": \"$NICKNAME\"}" | python3 -m json.tool
echo ""
echo ""

# 3. 로그인
echo "3. 로그인 테스트"
echo "-------------------"
curl -X POST "$API_BASE_URL/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d "{\"user_nickname\": \"$NICKNAME\"}" | python3 -m json.tool
echo ""
echo ""

# 4. 간단한 검색 요청
echo "4. 검색 요청 테스트 (테슬라 주가)"
echo "-------------------"
echo "주의: 이 요청은 시간이 걸릴 수 있습니다..."
curl -X POST "$API_BASE_URL/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "테슬라 주가",
    "sources": ["reddit"],
    "user_nickname": "'$NICKNAME'",
    "length": "simple"
  }' | python3 -m json.tool
echo ""
echo ""

# 5. 보고서 목록 조회
echo "5. 보고서 목록 조회"
echo "-------------------"
curl -X GET "$API_BASE_URL/api/v1/reports/$NICKNAME" \
  -H "Content-Type: application/json" | python3 -m json.tool
echo ""
echo ""

echo "======================================"
echo "테스트 완료!"
echo "======================================