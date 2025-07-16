import asyncio
import httpx
import json
import websockets

async def test_search_api():
    """테슬라의 미래 키워드로 API 테스트"""
    
    # API 엔드포인트
    base_url = "http://localhost:8000"
    
    # 테스트 데이터
    test_data = {
        "query": "테슬라의 미래",
        "sources": ["reddit"],
        "user_nickname": "testuser",
        "length": "moderate",
        "schedule_yn": "N"
    }
    
    async with httpx.AsyncClient() as client:
        # 1. 검색 요청 보내기
        print("1. 검색 요청을 보냅니다...")
        print(f"키워드: {test_data['query']}")
        
        response = await client.post(
            f"{base_url}/api/v1/search",
            json=test_data,
            timeout=30.0
        )
        
        if response.status_code != 200:
            print(f"에러 발생: {response.status_code}")
            print(response.text)
            return
        
        result = response.json()
        print(f"응답 받음: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        session_id = result.get("session_id")
        
        if not session_id:
            print("세션 ID를 받지 못했습니다.")
            return
        
        # 2. WebSocket으로 진행 상황 모니터링
        print(f"\n2. WebSocket으로 진행 상황 모니터링 (세션 ID: {session_id})")
        
        ws_url = f"ws://localhost:8000/api/v1/ws/progress/{session_id}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=60.0)
                        progress = json.loads(message)
                        
                        print(f"진행 상황: {progress['progress']}% - {progress['message']}")
                        
                        if progress.get("stage") == "completed":
                            print("\n분석이 완료되었습니다!")
                            break
                        elif progress.get("stage") == "error":
                            print(f"\n에러 발생: {progress['message']}")
                            break
                            
                    except asyncio.TimeoutError:
                        print("타임아웃 - 진행 상황 업데이트가 없습니다.")
                        break
                    except websockets.exceptions.ConnectionClosed:
                        print("WebSocket 연결이 종료되었습니다.")
                        break
                        
        except Exception as e:
            print(f"WebSocket 연결 실패: {str(e)}")
        
        # 3. 보고서 목록 조회
        print(f"\n3. 사용자의 보고서 목록을 조회합니다...")
        
        reports_response = await client.get(
            f"{base_url}/api/v1/reports/{test_data['user_nickname']}"
        )
        
        if reports_response.status_code == 200:
            reports = reports_response.json()
            print(f"총 {reports['total']}개의 보고서가 있습니다.")
            
            if reports['reports']:
                latest_report = reports['reports'][0]
                print(f"\n최신 보고서:")
                print(f"- 쿼리: {latest_report['query_text']}")
                print(f"- 수집된 게시물: {latest_report['posts_collected']}개")
                print(f"- 생성 시간: {latest_report['created_at']}")
                
                if latest_report.get('summary'):
                    print(f"\n요약:")
                    print(latest_report['summary'])

if __name__ == "__main__":
    asyncio.run(test_search_api())