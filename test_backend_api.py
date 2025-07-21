#!/usr/bin/env python3
"""
백엔드 API 테스트 스크립트
Community Info Collector Backend API 테스트
"""

import requests
import json
from datetime import datetime

# API 기본 URL
API_BASE_URL = "https://community-info-collector-backend.onrender.com"
# API_BASE_URL = "http://localhost:8000"  # 로컬 테스트용

# 색상 코드
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}ℹ {text}{RESET}")

def test_health_check():
    """헬스체크 테스트"""
    print_header("1. 헬스체크 테스트")
    
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=10)
        
        if response.status_code == 200:
            print_success(f"헬스체크 성공: {response.status_code}")
            print(f"응답: {response.json()}")
        else:
            print_error(f"헬스체크 실패: {response.status_code}")
            print(f"응답: {response.text}")
            
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print_error("서버 연결 실패 - 서버가 실행 중인지 확인하세요")
        return False
    except Exception as e:
        print_error(f"오류 발생: {str(e)}")
        return False

def test_user_registration():
    """사용자 등록 테스트"""
    print_header("2. 사용자 등록 테스트")
    
    test_nickname = f"test_user_{int(datetime.now().timestamp())}"
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/users/register",
            json={"user_nickname": test_nickname},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print_success(f"사용자 등록 성공: {test_nickname}")
            print(f"응답: {response.json()}")
            return True, test_nickname
        else:
            print_error(f"사용자 등록 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False, None
            
    except Exception as e:
        print_error(f"오류 발생: {str(e)}")
        return False, None

def test_user_login(nickname):
    """사용자 로그인 테스트"""
    print_header("3. 사용자 로그인 테스트")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/users/login",
            json={"user_nickname": nickname},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            print_success(f"로그인 성공: {nickname}")
            print(f"응답: {response.json()}")
            return True
        else:
            print_error(f"로그인 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"오류 발생: {str(e)}")
        return False

def test_search_request(nickname):
    """검색 요청 테스트 (간단한 버전)"""
    print_header("4. 검색 요청 테스트")
    
    search_data = {
        "query": "테슬라 주가",
        "sources": ["reddit"],
        "user_nickname": nickname,
        "length": "simple"
    }
    
    print_info(f"검색 요청 데이터: {json.dumps(search_data, ensure_ascii=False, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/search",
            json=search_data,
            headers={"Content-Type": "application/json"},
            timeout=60  # 검색은 시간이 걸릴 수 있음
        )
        
        if response.status_code == 200:
            print_success("검색 요청 성공")
            result = response.json()
            print(f"\n세션 ID: {result.get('session_id', 'N/A')}")
            summary = result.get('summary', 'N/A')
            if summary and summary != 'N/A':
                print(f"요약: {summary[:200]}...")
            else:
                print("요약: 아직 생성되지 않음")
            return True, result.get('session_id')
        else:
            print_error(f"검색 요청 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False, None
            
    except requests.exceptions.Timeout:
        print_error("요청 시간 초과 (60초)")
        return False, None
    except Exception as e:
        print_error(f"오류 발생: {str(e)}")
        return False, None

def test_get_reports(nickname):
    """보고서 목록 조회 테스트"""
    print_header("5. 보고서 목록 조회 테스트")
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/reports/{nickname}",
            timeout=10
        )
        
        if response.status_code == 200:
            print_success("보고서 목록 조회 성공")
            reports = response.json().get('reports', [])
            print(f"총 보고서 수: {len(reports)}")
            
            if reports:
                print("\n최근 보고서 3개:")
                for report in reports[:3]:
                    print(f"  - {report.get('query_text', 'N/A')} ({report.get('created_at', 'N/A')})")
            
            return True
        else:
            print_error(f"보고서 조회 실패: {response.status_code}")
            print(f"응답: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"오류 발생: {str(e)}")
        return False

def main():
    """메인 테스트 실행"""
    print_header("Community Info Collector 백엔드 API 테스트")
    print(f"API 서버: {API_BASE_URL}")
    print(f"테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 헬스체크
    if not test_health_check():
        print_error("\n서버가 응답하지 않습니다. 테스트를 중단합니다.")
        return
    
    # 2. 사용자 등록
    success, test_nickname = test_user_registration()
    if not success:
        print_info("\n기존 사용자로 테스트를 계속합니다.")
        test_nickname = "test_user"
    
    # 3. 로그인 테스트
    if not test_user_login(test_nickname):
        print_error("\n로그인 실패. 일부 테스트를 건너뜁니다.")
    
    # 4. 검색 요청 테스트
    print_info("\n검색 요청을 시작합니다. 시간이 걸릴 수 있습니다...")
    search_success, session_id = test_search_request(test_nickname)
    
    # 5. 보고서 목록 조회
    test_get_reports(test_nickname)
    
    # 결과 요약
    print_header("테스트 완료")
    print(f"테스트 종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()