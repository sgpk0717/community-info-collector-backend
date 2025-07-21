#!/usr/bin/env python3
"""
간단한 기능 테스트 - 서버가 이미 실행 중일 때 사용
"""

import requests
import json
import time

# 테스트 설정
API_BASE_URL = "https://community-info-collector-backend.onrender.com"
TEST_USER = "test_phases_user_prod"
TEST_KEYWORD = "테슬라의 미래"

print("🚀 Community Info Collector 빠른 테스트")
print("=" * 50)

# 1. 사용자 등록/로그인
print("\n1️⃣ 사용자 등록/로그인 테스트")
try:
    # 로그인 시도
    login_data = {"user_nickname": TEST_USER}
    resp = requests.post(f"{API_BASE_URL}/api/v1/users/login", json=login_data)
    
    if resp.status_code == 404:
        # 사용자가 없으면 등록
        print("   사용자가 없어서 등록합니다...")
        register_data = {"user_nickname": TEST_USER}
        resp = requests.post(f"{API_BASE_URL}/api/v1/users/register", json=register_data)
        if resp.status_code == 200:
            print("   ✅ 사용자 등록 성공!")
        else:
            print(f"   ❌ 사용자 등록 실패: {resp.status_code}")
    elif resp.status_code == 200:
        print("   ✅ 로그인 성공!")
    else:
        print(f"   ❌ 로그인 실패: {resp.status_code}")
except Exception as e:
    print(f"   ❌ 오류: {e}")

# 2. 검색 요청 테스트
print("\n2️⃣ 검색 및 분석 요청 테스트")
print(f"   키워드: '{TEST_KEYWORD}'")

try:
    search_data = {
        "query": TEST_KEYWORD,
        "sources": ["reddit"],
        "user_nickname": TEST_USER,
        "length": "moderate",
        "schedule_yn": "N"
    }
    
    print("   검색 요청 전송 중...")
    resp = requests.post(f"{API_BASE_URL}/api/v1/search", json=search_data)
    
    if resp.status_code == 200:
        result = resp.json()
        session_id = result.get("session_id")
        print(f"   ✅ 검색 요청 성공! 세션 ID: {session_id}")
        
        # 잠시 대기
        print("\n   ⏳ 분석이 진행 중입니다. 30초 후 보고서를 확인합니다...")
        time.sleep(30)
        
        # 3. 보고서 조회
        print("\n3️⃣ 보고서 조회 테스트")
        resp = requests.get(f"{API_BASE_URL}/api/v1/reports/{TEST_USER}")
        
        if resp.status_code == 200:
            reports = resp.json()
            if reports:
                print(f"   ✅ 보고서 {len(reports)}개 발견!")
                
                # 가장 최근 보고서 확인
                latest = reports[0]
                print(f"\n   📄 최근 보고서:")
                print(f"      - 키워드: {latest.get('query_text')}")
                print(f"      - 생성일: {latest.get('created_at')}")
                print(f"      - 수집된 게시물: {latest.get('posts_collected')}개")
                print(f"      - 보고서 ID: {latest.get('id')}")
                
                # 상세 보고서 조회
                report_id = latest.get('id')
                detail_resp = requests.get(f"{API_BASE_URL}/api/v1/reports/detail/{report_id}")
                
                if detail_resp.status_code == 200:
                    detail = detail_resp.json()
                    
                    # Phase 1 검증: 키워드 확장
                    keywords_used = detail.get('keywords_used', [])
                    print(f"\n   🔍 Phase 1 - 키워드 확장:")
                    print(f"      확장된 키워드 수: {len(keywords_used)}개")
                    if len(keywords_used) > 5:
                        print("      ✅ 5개 이상 확장됨!")
                    else:
                        print("      ❌ 5개 이하로 제한됨")
                else:
                    print(f"\n   ❌ 상세 보고서 조회 실패: {detail_resp.status_code}")
                    print(f"   응답: {detail_resp.text[:200]}...")
                    return
                    
                    # 보고서 내용 일부 표시
                    summary = detail.get('summary', '')
                    if summary:
                        print(f"\n   📝 보고서 요약 (첫 200자):")
                        print(f"      {summary[:200]}...")
                        
                    # 보고서 내용에서 Phase 2, 3 흔적 찾기
                    full_report = detail.get('full_report', '')
                    
                    # Phase 2: 댓글 수집 여부
                    if '댓글' in full_report or 'comment' in full_report.lower():
                        print("\n   💬 Phase 2 - 댓글 수집: ✅ 댓글 관련 내용 발견")
                    else:
                        print("\n   💬 Phase 2 - 댓글 수집: ⚠️  댓글 관련 내용 없음")
                    
                    # Phase 3: 관련성 필터링 여부
                    if '관련성' in full_report or 'relevance' in full_report.lower():
                        print("   🎯 Phase 3 - 관련성 필터링: ✅ 관련성 분석 흔적 발견")
                    else:
                        print("   🎯 Phase 3 - 관련성 필터링: ⚠️  관련성 분석 흔적 없음")
                        
            else:
                print("   ⚠️  아직 보고서가 생성되지 않았습니다")
        else:
            print(f"   ❌ 보고서 조회 실패: {resp.status_code}")
            
    else:
        print(f"   ❌ 검색 요청 실패: {resp.status_code}")
        print(f"   응답: {resp.text}")
        
except Exception as e:
    print(f"   ❌ 오류 발생: {e}")

print("\n" + "=" * 50)
print("테스트 완료!")