import requests
import json
import time

# API 베이스 URL
API_BASE_URL = "http://127.0.0.1:8000"

# 테스트 요청 데이터
test_request = {
    "query": "Tesla stock",
    "sources": ["reddit"],
    "user_nickname": "test_user_footnote",
    "length": "moderate",
    "time_filter": "1d",  # 24시간
    "schedule_yn": "N"
}

print("🚀 보고서 생성 API 테스트 시작...")
print(f"요청 데이터: {json.dumps(test_request, indent=2, ensure_ascii=False)}")

try:
    # API 호출
    response = requests.post(
        f"{API_BASE_URL}/api/v1/search",
        json=test_request,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ API 호출 성공!")
        print(f"Session ID: {data.get('session_id')}")
        print(f"Query ID: {data.get('query_id')}")
        
        # 잠시 대기 (보고서 생성 시간)
        print("\n⏳ 보고서 생성 대기 중... (30초)")
        time.sleep(30)
        
        # 보고서 목록 조회
        reports_response = requests.get(
            f"{API_BASE_URL}/api/v1/reports/{test_request['user_nickname']}"
        )
        
        if reports_response.status_code == 200:
            reports_data = reports_response.json()
            reports = reports_data.get('reports', [])
            
            if reports:
                latest_report = reports[0]
                print(f"\n📄 최신 보고서 확인:")
                print(f"제목: {latest_report['query_text']}")
                print(f"생성 시간: {latest_report['created_at']}")
                
                # 전체 보고서 내용 확인
                full_report = latest_report.get('full_report', '')
                
                # [ref:XXX] 패턴 확인
                if '[ref:' in full_report:
                    print("\n⚠️  문제 발견: [ref:POST_XXX] 형식이 보고서에 남아있음!")
                    import re
                    refs = re.findall(r'\[ref:[^\]]+\]', full_report)
                    print(f"발견된 미변환 참조: {refs[:5]}")
                else:
                    print("\n✅ 각주 변환 정상: 모든 참조가 [1], [2] 형식으로 변환됨")
                    import re
                    footnotes = re.findall(r'\[\d+\]', full_report)
                    print(f"발견된 각주: {set(footnotes)}")
                
                # 보고서 끝 부분 확인
                report_lines = full_report.split('\n')[-20:]
                if any('참조 목록' in line for line in report_lines):
                    print("\n✅ '참조 목록' 섹션이 보고서 끝에 있음")
                    # 참조 목록 부분 출력
                    ref_start = False
                    for line in report_lines:
                        if '참조 목록' in line:
                            ref_start = True
                        if ref_start:
                            print(f"  {line}")
                else:
                    print("\n⚠️  '참조 목록' 섹션이 보고서에 없음")
                
                # report_links 확인
                report_id = latest_report['id']
                links_response = requests.get(
                    f"{API_BASE_URL}/api/v1/reports/{report_id}/links"
                )
                
                if links_response.status_code == 200:
                    links_data = links_response.json()
                    links = links_data.get('links', [])
                    print(f"\n🔗 report_links 테이블 데이터: {len(links)}개")
                    for link in links[:3]:
                        print(f"  [{link['footnote_number']}] {link['title'][:50]}...")
                        
    else:
        print(f"\n❌ API 호출 실패: {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"\n❌ 에러 발생: {e}")
    import traceback
    traceback.print_exc()