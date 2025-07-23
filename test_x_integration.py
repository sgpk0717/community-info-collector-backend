#!/usr/bin/env python3
"""
X API 통합 테스트 스크립트
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# 백엔드 모듈 import를 위한 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 환경변수 로드
load_dotenv()

from app.services.x_usage_service import XUsageService
from app.services.x_service import XService
from app.services.multi_platform_service import MultiPlatformService

async def test_x_usage_service():
    """X API 사용량 서비스 테스트"""
    print("=== X API 사용량 서비스 테스트 ===")
    
    try:
        usage_service = XUsageService()
        
        # 현재 사용량 확인
        current_usage = await usage_service.get_current_month_usage()
        print(f"현재 월 사용량: {current_usage}")
        
        # 사용 가능 여부 확인
        can_use = await usage_service.can_use_api(tweets_needed=5)
        print(f"API 사용 가능: {can_use}")
        
        return True
    except Exception as e:
        print(f"❌ 사용량 서비스 테스트 실패: {e}")
        return False

async def test_x_service():
    """X API 서비스 테스트"""
    print("\n=== X API 서비스 테스트 ===")
    
    try:
        x_service = XService()
        
        # 간단한 검색 테스트
        print("Tesla 키워드로 트윗 검색 중...")
        tweets = await x_service.search_tweets("Tesla", max_results=10)
        
        print(f"검색 결과: {len(tweets)}개 트윗")
        
        if tweets:
            print("첫 번째 트윗:")
            first_tweet = tweets[0]
            print(f"- ID: {first_tweet['id']}")
            print(f"- 내용: {first_tweet['text'][:100]}...")
            print(f"- 점수: {first_tweet['score']}")
            print(f"- URL: {first_tweet['url']}")
        
        return True
    except Exception as e:
        print(f"❌ X 서비스 테스트 실패: {e}")
        return False

async def test_multi_platform_service():
    """멀티 플랫폼 서비스 테스트"""
    print("\n=== 멀티 플랫폼 서비스 테스트 ===")
    
    try:
        multi_service = MultiPlatformService()
        
        # 지원 플랫폼 확인
        supported = multi_service.get_supported_platforms()
        print(f"지원 플랫폼: {supported}")
        
        # 간단한 멀티 플랫폼 검색
        print("AI 키워드로 멀티 플랫폼 검색 중...")
        results = await multi_service.search_all_platforms(
            query="AI",
            sources=["reddit", "x"],
            reddit_limit=5,
            x_limit=10  # X API 최소 요구사항
        )
        
        print(f"전체 검색 결과: {len(results)}개")
        
        # 플랫폼별 통계
        reddit_count = len([r for r in results if r.get('platform') == 'reddit'])
        x_count = len([r for r in results if r.get('platform') == 'x'])
        
        print(f"- Reddit: {reddit_count}개")
        print(f"- X: {x_count}개")
        
        return True
    except Exception as e:
        print(f"❌ 멀티 플랫폼 서비스 테스트 실패: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("🚀 X API 통합 테스트 시작\n")
    
    # 환경변수 확인
    required_vars = ['X_BEARER_TOKEN', 'X_API_KEY', 'X_API_SECRET', 'X_ACCESS_TOKEN', 'X_ACCESS_TOKEN_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ 누락된 환경변수: {missing_vars}")
        print("   .env 파일에 X API 자격 증명을 추가하세요.")
        return
    
    print("✅ 환경변수 확인 완료")
    
    # 테스트 실행
    tests = [
        ("X API 사용량 서비스", test_x_usage_service),
        ("X API 서비스", test_x_service),
        ("멀티 플랫폼 서비스", test_multi_platform_service)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 예외 발생: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n" + "="*50)
    print("테스트 결과 요약:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"- {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n총 {passed}/{len(results)}개 테스트 통과")
    
    if passed == len(results):
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 로그를 확인하세요.")

if __name__ == "__main__":
    asyncio.run(main())