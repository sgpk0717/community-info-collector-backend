#!/usr/bin/env python3
"""
프로덕션 서버 테스트 - 단계별 기능 검증
"""

import requests
import json
import time
from datetime import datetime

# 테스트 설정
API_BASE_URL = "https://community-info-collector-backend.onrender.com"
TEST_USER = "phase_test_prod"
TEST_KEYWORD = "애플 비전프로"

print("🚀 Community Info Collector 프로덕션 테스트")
print("=" * 60)
print(f"서버: {API_BASE_URL}")
print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 1. 분석 요청 생성
print("\n📝 새로운 분석 요청 생성")
print(f"키워드: '{TEST_KEYWORD}'")

try:
    search_data = {
        "query": TEST_KEYWORD,
        "sources": ["reddit"],
        "user_nickname": TEST_USER,
        "length": "detailed",
        "schedule_yn": "N"
    }
    
    print("요청 전송 중...")
    resp = requests.post(f"{API_BASE_URL}/api/v1/search", json=search_data)
    
    if resp.status_code == 200:
        result = resp.json()
        session_id = result.get("session_id")
        print(f"✅ 요청 성공! 세션 ID: {session_id}")
        
        # 분석 완료 대기
        print("\n⏳ 분석 진행 중... (최대 2분 대기)")
        for i in range(24):  # 5초씩 24번 = 2분
            time.sleep(5)
            print(".", end="", flush=True)
            
            # 보고서 목록 확인
            reports_resp = requests.get(f"{API_BASE_URL}/api/v1/reports/{TEST_USER}")
            if reports_resp.status_code == 200:
                response_data = reports_resp.json()
                
                # 응답이 dict이고 reports 키가 있는 경우
                if isinstance(response_data, dict) and 'reports' in response_data:
                    reports = response_data['reports']
                else:
                    reports = response_data
                
                # reports가 리스트인지 확인
                if not isinstance(reports, list):
                    continue
                
                # 현재 키워드로 생성된 보고서 찾기
                matching_report = None
                for report in reports:
                    if isinstance(report, dict) and report.get('query_text') == TEST_KEYWORD:
                        matching_report = report
                        break
                
                if matching_report:
                    print("\n✅ 보고서 생성 완료!")
                    
                    # 보고서 기본 정보
                    print(f"\n📊 보고서 기본 정보:")
                    print(f"   - ID: {matching_report.get('id')}")
                    print(f"   - 생성일: {matching_report.get('created_at')}")
                    print(f"   - 수집된 게시물: {matching_report.get('posts_collected')}개")
                    
                    # 상세 보고서 조회
                    report_id = matching_report.get('id')
                    if report_id:
                        detail_resp = requests.get(f"{API_BASE_URL}/api/v1/reports/detail/{report_id}")
                        
                        if detail_resp.status_code == 200:
                            detail = detail_resp.json()
                            
                            # Phase 1 검증: 키워드 확장
                            print("\n🔍 Phase 1 - 키워드 확장 검증:")
                            keywords_used = detail.get('keywords_used', [])
                            print(f"   확장된 키워드 수: {len(keywords_used)}개")
                            
                            if len(keywords_used) > 5:
                                print("   ✅ Phase 1 성공: 5개 이상의 키워드로 확장됨!")
                                # 상위 10개 키워드 표시
                                for idx, kw in enumerate(keywords_used[:10]):
                                    print(f"      {idx+1}. {kw.get('keyword', 'N/A')} ({kw.get('posts_found', 0)}개 게시물)")
                                if len(keywords_used) > 10:
                                    print(f"      ... 외 {len(keywords_used) - 10}개")
                            else:
                                print("   ❌ Phase 1 실패: 키워드가 5개 이하로 제한됨")
                            
                            # 보고서 내용 분석
                            full_report = detail.get('full_report', '')
                            summary = detail.get('summary', '')
                            
                            # Phase 2 검증: 댓글 수집
                            print("\n💬 Phase 2 - 댓글 수집 검증:")
                            comment_mentions = (
                                full_report.count('댓글') + 
                                full_report.lower().count('comment') +
                                summary.count('댓글') +
                                summary.lower().count('comment')
                            )
                            
                            if comment_mentions > 0:
                                print(f"   ✅ Phase 2 성공: 댓글 관련 언급 {comment_mentions}회 발견")
                            else:
                                print("   ⚠️  Phase 2 미확인: 보고서에 댓글 언급 없음")
                            
                            # Phase 3 검증: 관련성 필터링
                            print("\n🎯 Phase 3 - 관련성 필터링 검증:")
                            relevance_mentions = (
                                full_report.count('관련성') + 
                                full_report.lower().count('relevance') +
                                full_report.count('관련') +
                                full_report.count('품질')
                            )
                            
                            if relevance_mentions > 0:
                                print(f"   ✅ Phase 3 성공: 관련성/품질 언급 {relevance_mentions}회 발견")
                            else:
                                print("   ⚠️  Phase 3 미확인: 보고서에 관련성 분석 흔적 없음")
                            
                            # 보고서 샘플 출력
                            print("\n📝 보고서 요약 (첫 300자):")
                            print(f"   {summary[:300]}...")
                            
                            # 각주 정보 확인
                            if '[1]' in full_report or '[2]' in full_report:
                                print("\n🔗 각주 시스템: ✅ 활성화됨")
                            else:
                                print("\n🔗 각주 시스템: ⚠️  미확인")
                            
                        else:
                            print(f"\n❌ 상세 보고서 조회 실패: {detail_resp.status_code}")
                    
                    break
        
        if not matching_report:
            print("\n⚠️  제한 시간 내에 보고서가 생성되지 않았습니다.")
            
    else:
        print(f"❌ 검색 요청 실패: {resp.status_code}")
        print(f"응답: {resp.text[:500]}...")
        
except Exception as e:
    print(f"❌ 오류 발생: {e}")

print("\n" + "=" * 60)
print("🏁 테스트 완료!")