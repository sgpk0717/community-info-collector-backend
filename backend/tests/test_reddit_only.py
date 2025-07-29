#!/usr/bin/env python3
"""
Reddit 전용 멀티플랫폼 서비스 테스트
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from app.services.multi_platform_service import MultiPlatformService

async def test_reddit_only():
    """Reddit만으로 멀티플랫폼 서비스 테스트"""
    print("=== Reddit 전용 멀티플랫폼 서비스 테스트 ===")
    
    try:
        multi_service = MultiPlatformService()
        
        # 지원 플랫폼 확인
        supported = multi_service.get_supported_platforms()
        print(f"지원 플랫폼: {supported}")
        
        # Reddit만으로 검색
        print("Tesla 키워드로 Reddit 검색 중...")
        results = await multi_service.search_all_platforms(
            query="Tesla",
            sources=["reddit"],  # Reddit만
            reddit_limit=10
        )
        
        print(f"검색 결과: {len(results)}개")
        
        if results:
            print("첫 번째 결과:")
            first = results[0]
            print(f"- 제목: {first.get('title', '')[:100]}...")
            print(f"- 점수: {first.get('score', 0)}")
            print(f"- 플랫폼: {first.get('platform', 'unknown')}")
            print(f"- URL: {first.get('url', '')}")
        
        return True
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_reddit_only())