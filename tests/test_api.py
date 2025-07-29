#!/usr/bin/env python3
import requests
import json
import time

# 테스트 설정
API_BASE_URL = "http://localhost:8000"
TEST_USER = "testuser123"

def test_login():
    """로그인 테스트"""
    print("1. 로그인 테스트...")
    url = f"{API_BASE_URL}/api/v1/users/login"
    data = {"user_nickname": TEST_USER}
    
    try:
        response = requests.post(url, json=data)
        print(f"   상태: {response.status_code}")
        print(f"   응답: {response.text[:200]}")
        return response.status_code == 200
    except Exception as e:
        print(f"   오류: {e}")
        return False

def test_search():
    """검색 요청 테스트"""
    print("\n2. 검색 요청 테스트...")
    url = f"{API_BASE_URL}/api/v1/search"
    data = {
        "query": "테스트 키워드",
        "sources": ["reddit"],
        "user_nickname": TEST_USER,
        "length": "moderate",
        "schedule_yn": "N"
    }
    
    print(f"   URL: {url}")
    print(f"   데이터: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(url, json=data)
        print(f"   상태: {response.status_code}")
        print(f"   응답: {response.text[:200]}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   세션 ID: {result.get('session_id', 'N/A')}")
        return response.status_code == 200
    except Exception as e:
        print(f"   오류: {e}")
        return False

def test_cors_preflight():
    """CORS preflight 테스트"""
    print("\n3. CORS preflight 테스트...")
    url = f"{API_BASE_URL}/api/v1/search"
    
    headers = {
        "Origin": "http://localhost:8081",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"
    }
    
    try:
        response = requests.options(url, headers=headers)
        print(f"   상태: {response.status_code}")
        print(f"   CORS 헤더:")
        for key, value in response.headers.items():
            if key.lower().startswith('access-control'):
                print(f"     {key}: {value}")
        return response.status_code == 200
    except Exception as e:
        print(f"   오류: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Community Info Collector API 테스트")
    print("=" * 50)
    
    # 서버 연결 확인
    print("서버 연결 확인...")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print(f"✅ 서버 연결 성공: {response.json()}")
    except Exception as e:
        print(f"❌ 서버 연결 실패: {e}")
        print("서버가 실행 중인지 확인하세요.")
        exit(1)
    
    print("\n" + "=" * 50)
    
    # 테스트 실행
    tests = [
        ("로그인", test_login),
        ("검색 요청", test_search),
        ("CORS", test_cors_preflight)
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
        time.sleep(1)  # 요청 간 간격
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    print("=" * 50)
    for name, result in results:
        status = "✅ 성공" if result else "❌ 실패"
        print(f"{name}: {status}")