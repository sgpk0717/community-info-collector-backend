#!/usr/bin/env python3
"""
기존 보고서 확인 테스트
"""

import requests
import json

# 테스트 설정
API_BASE_URL = "https://community-info-collector-backend.onrender.com"
TEST_USERS = ["test_phases_user", "test_user", "testuser", "quick_test_user"]

print("📊 기존 보고서 확인 테스트")
print("=" * 60)

for user in TEST_USERS:
    print(f"\n👤 사용자: {user}")
    
    try:
        # 보고서 목록 조회
        resp = requests.get(f"{API_BASE_URL}/api/v1/reports/{user}")
        
        if resp.status_code == 200:
            data = resp.json()
            
            # 응답 형식 확인
            if isinstance(data, dict) and 'reports' in data:
                reports = data['reports']
                total = data.get('total', len(reports))
            else:
                reports = data if isinstance(data, list) else []
                total = len(reports)
            
            if reports:
                print(f"   ✅ 총 {total}개 보고서 발견!")
                
                # 최근 3개 보고서만 표시
                for idx, report in enumerate(reports[:3]):
                    print(f"\n   [{idx+1}] 보고서:")
                    print(f"      - ID: {report.get('id')}")
                    print(f"      - 키워드: {report.get('query_text')}")
                    print(f"      - 생성일: {report.get('created_at')}")
                    print(f"      - 수집 게시물: {report.get('posts_collected')}개")
                    
                    # 상세 보고서 조회
                    report_id = report.get('id')
                    if report_id:
                        detail_resp = requests.get(f"{API_BASE_URL}/api/v1/reports/detail/{report_id}")
                        
                        if detail_resp.status_code == 200:
                            detail = detail_resp.json()
                            
                            # keywords_used 확인
                            keywords_used = detail.get('keywords_used', [])
                            if keywords_used:
                                print(f"      - 사용된 키워드: {len(keywords_used)}개")
                                if len(keywords_used) > 5:
                                    print("        ✅ Phase 1: 키워드 확장 성공!")
                                else:
                                    print("        ❌ Phase 1: 키워드 제한됨")
                            
                            # 보고서 내용 간단 확인
                            full_report = detail.get('full_report', '')
                            if full_report:
                                # Phase 2: 댓글
                                if '댓글' in full_report or 'comment' in full_report.lower():
                                    print("        ✅ Phase 2: 댓글 수집 흔적 발견")
                                
                                # Phase 3: 관련성
                                if '관련성' in full_report or '품질' in full_report:
                                    print("        ✅ Phase 3: 관련성 필터링 흔적 발견")
                        else:
                            print(f"      ⚠️  상세 조회 실패: {detail_resp.status_code}")
                
                if total > 3:
                    print(f"\n   ... 외 {total - 3}개 보고서")
                    
            else:
                print("   ⚠️  보고서 없음")
                
        else:
            print(f"   ❌ 조회 실패: {resp.status_code}")
            
    except Exception as e:
        print(f"   ❌ 오류: {e}")

print("\n" + "=" * 60)
print("✅ 테스트 완료!")