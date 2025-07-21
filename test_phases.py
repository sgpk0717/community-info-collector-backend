#!/usr/bin/env python3
"""
Community Info Collector 단계별 기능 테스트 스크립트

Phase 1: 키워드 확장 (5개 → 무제한)
Phase 2: 댓글 수집 기능
Phase 3: 관련성 필터링 LLM 서비스
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import sys

# 테스트 설정
API_BASE_URL = "http://localhost:8000"
TEST_USER = "test_phases_user"
TEST_KEYWORD = "테슬라의 미래"

# 색상 코드 (터미널 출력용)
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ️  {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠️  {text}{Colors.ENDC}")

async def test_phase1_keyword_expansion():
    """Phase 1: 키워드 확장 테스트"""
    print_header("Phase 1: 키워드 확장 테스트")
    
    async with aiohttp.ClientSession() as session:
        # 분석 요청
        search_data = {
            "query": TEST_KEYWORD,
            "sources": ["reddit"],
            "user_nickname": TEST_USER,
            "length": "detailed",
            "schedule_yn": "N"
        }
        
        print_info(f"테스트 키워드: '{TEST_KEYWORD}'")
        print_info("분석 요청 전송 중...")
        
        async with session.post(f"{API_BASE_URL}/api/v1/search", json=search_data) as resp:
            if resp.status != 200:
                print_error(f"API 요청 실패: {resp.status}")
                return False
            
            result = await resp.json()
            session_id = result.get("session_id")
            print_success(f"세션 ID: {session_id}")
        
        # 진행 상태 모니터링 (WebSocket 대신 폴링)
        print_info("분석 진행 상태 확인 중...")
        
        # 최대 2분간 대기
        max_wait_time = 120
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait_time:
            await asyncio.sleep(5)  # 5초마다 확인
            
            # 보고서 목록 조회로 완료 여부 확인
            async with session.get(f"{API_BASE_URL}/api/v1/reports/{TEST_USER}") as resp:
                if resp.status == 200:
                    reports = await resp.json()
                    if reports and len(reports) > 0:
                        latest_report = reports[0]
                        if latest_report.get("query_text") == TEST_KEYWORD:
                            print_success("분석 완료!")
                            
                            # 상세 보고서 조회
                            report_id = latest_report["id"]
                            async with session.get(f"{API_BASE_URL}/api/v1/reports/detail/{report_id}") as detail_resp:
                                if detail_resp.status == 200:
                                    report_detail = await detail_resp.json()
                                    
                                    # keywords_used 정보 확인
                                    keywords_used = report_detail.get("keywords_used", [])
                                    
                                    print_info(f"\n확장된 키워드 수: {len(keywords_used)}")
                                    
                                    if len(keywords_used) > 5:
                                        print_success("✨ Phase 1 성공: 5개 이상의 키워드로 확장됨!")
                                        for idx, kw in enumerate(keywords_used[:10]):  # 상위 10개만 표시
                                            print(f"   {idx+1}. {kw['keyword']} → {kw.get('translated_keyword', 'N/A')} ({kw['posts_found']}개 게시물)")
                                        if len(keywords_used) > 10:
                                            print(f"   ... 외 {len(keywords_used) - 10}개 키워드")
                                    else:
                                        print_warning(f"키워드 확장이 제한적임: {len(keywords_used)}개만 사용됨")
                                    
                                    return True
            
            print(".", end="", flush=True)
        
        print_error("\n분석이 제한 시간 내에 완료되지 않았습니다")
        return False

async def test_phase2_comment_collection():
    """Phase 2: 댓글 수집 테스트"""
    print_header("Phase 2: 댓글 수집 테스트")
    
    # 서버 로그를 확인하여 댓글 수집 여부 체크
    print_info("최근 보고서의 로그를 확인하여 댓글 수집 여부를 검증합니다")
    
    async with aiohttp.ClientSession() as session:
        # 로그 조회 API 호출
        async with session.get(f"{API_BASE_URL}/api/v1/logs/recent?limit=100") as resp:
            if resp.status == 200:
                logs = await resp.json()
                
                # 댓글 수집 관련 로그 찾기
                comment_logs = [
                    log for log in logs 
                    if "댓글" in log.get("message", "") or "comment" in log.get("message", "").lower()
                ]
                
                if comment_logs:
                    print_success(f"✨ Phase 2 성공: 댓글 수집 로그 {len(comment_logs)}개 발견!")
                    for log in comment_logs[:5]:  # 상위 5개만 표시
                        print(f"   - {log['message']}")
                    return True
                else:
                    print_warning("댓글 수집 관련 로그를 찾을 수 없습니다")
            else:
                print_error(f"로그 조회 실패: {resp.status}")
    
    return False

async def test_phase3_relevance_filtering():
    """Phase 3: 관련성 필터링 테스트"""
    print_header("Phase 3: 관련성 필터링 테스트")
    
    print_info("최근 보고서의 로그를 확인하여 관련성 필터링 적용 여부를 검증합니다")
    
    async with aiohttp.ClientSession() as session:
        # 로그 조회 API 호출
        async with session.get(f"{API_BASE_URL}/api/v1/logs/recent?limit=200") as resp:
            if resp.status == 200:
                logs = await resp.json()
                
                # 관련성 필터링 로그 찾기
                relevance_logs = [
                    log for log in logs 
                    if "관련성" in log.get("message", "") or "relevance" in log.get("message", "").lower()
                ]
                
                if relevance_logs:
                    print_success(f"✨ Phase 3 성공: 관련성 필터링 로그 {len(relevance_logs)}개 발견!")
                    
                    # 필터링 결과 통계 찾기
                    for log in relevance_logs:
                        msg = log.get("message", "")
                        if "원본:" in msg and "필터링 후:" in msg:
                            print(f"   - {msg}")
                        elif "평균 관련성 점수:" in msg:
                            print(f"   - {msg}")
                        elif "고품질 콘텐츠:" in msg:
                            print(f"   - {msg}")
                    
                    return True
                else:
                    print_warning("관련성 필터링 관련 로그를 찾을 수 없습니다")
            else:
                print_error(f"로그 조회 실패: {resp.status}")
    
    return False

async def main():
    """메인 테스트 실행"""
    print_header("Community Info Collector 단계별 기능 테스트")
    print_info(f"API 서버: {API_BASE_URL}")
    print_info(f"테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 서버 상태 확인
    print("\n서버 상태 확인 중...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE_URL}/") as resp:
                if resp.status in [200, 404]:  # 루트 경로가 404를 반환해도 서버는 실행 중
                    print_success("서버가 정상적으로 실행 중입니다")
                else:
                    print_error(f"서버 상태 이상: {resp.status}")
                    return
        except Exception as e:
            print_error(f"서버 연결 실패: {e}")
            print_info("서버가 실행 중인지 확인해주세요: python -m uvicorn app.main:app")
            return
    
    # 각 단계별 테스트 실행
    results = {
        "Phase 1 (키워드 확장)": False,
        "Phase 2 (댓글 수집)": False,
        "Phase 3 (관련성 필터링)": False
    }
    
    try:
        # Phase 1 테스트
        results["Phase 1 (키워드 확장)"] = await test_phase1_keyword_expansion()
        await asyncio.sleep(2)
        
        # Phase 2 테스트
        results["Phase 2 (댓글 수집)"] = await test_phase2_comment_collection()
        await asyncio.sleep(2)
        
        # Phase 3 테스트
        results["Phase 3 (관련성 필터링)"] = await test_phase3_relevance_filtering()
        
    except Exception as e:
        print_error(f"테스트 중 오류 발생: {e}")
    
    # 최종 결과 출력
    print_header("테스트 결과 요약")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for phase, passed in results.items():
        if passed:
            print_success(f"{phase}: PASS")
        else:
            print_error(f"{phase}: FAIL")
    
    print(f"\n{Colors.BOLD}총 {total_tests}개 테스트 중 {passed_tests}개 성공{Colors.ENDC}")
    
    if passed_tests == total_tests:
        print_success("\n🎉 모든 테스트 통과! 단계별 기능이 정상적으로 작동합니다.")
    else:
        print_warning(f"\n⚠️ {total_tests - passed_tests}개 테스트 실패. 로그를 확인해주세요.")

if __name__ == "__main__":
    asyncio.run(main())