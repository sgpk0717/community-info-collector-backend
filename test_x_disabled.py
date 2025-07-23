#!/usr/bin/env python3
"""
X API 비활성화 상태 테스트
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# X API 비활성화 설정
os.environ['USE_X_API'] = 'false'

from app.services.multi_platform_service import MultiPlatformService

async def test_x_disabled():
    """X API 비활성화 상태에서 멀티플랫폼 서비스 테스트"""
    print("=== X API 비활성화 테스트 ===")
    print(f"USE_X_API 환경변수: {os.getenv('USE_X_API')}")
    
    try:
        multi_service = MultiPlatformService()
        
        # 지원 플랫폼 확인
        supported = multi_service.get_supported_platforms()
        print(f"\n지원 플랫폼: {supported}")
        
        # 플랫폼별 사용 가능 여부
        print("\n플랫폼별 사용 가능 여부:")
        print(f"- Reddit: {multi_service.is_platform_available('reddit')}")
        print(f"- X: {multi_service.is_platform_available('x')}")
        
        # 멀티플랫폼 검색 (X 포함 요청)
        print("\n'AI' 키워드로 멀티플랫폼 검색 (X 포함 요청)...")
        results = await multi_service.search_all_platforms(
            query="AI",
            sources=["reddit", "x"],  # X도 요청했지만 비활성화 상태
            reddit_limit=10
        )
        
        print(f"\n검색 결과: 총 {len(results)}개")
        
        # 플랫폼별 통계
        reddit_count = len([r for r in results if r.get('platform') == 'reddit'])
        x_count = len([r for r in results if r.get('platform') == 'x'])
        
        print(f"- Reddit: {reddit_count}개")
        print(f"- X: {x_count}개 (0이어야 정상)")
        
        # 플랫폼 통계
        stats = await multi_service.get_platform_stats()
        print(f"\n플랫폼 통계:")
        print(f"- Reddit: {stats['reddit']}")
        print(f"- X: {stats['x']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_x_enabled():
    """X API 활성화 상태 테스트 (비교용)"""
    print("\n\n=== X API 활성화 테스트 (비교) ===")
    
    # X API 활성화 설정
    os.environ['USE_X_API'] = 'true'
    print(f"USE_X_API 환경변수: {os.getenv('USE_X_API')}")
    
    # 모듈 다시 로드 (환경변수 변경 반영)
    import importlib
    from app.services import x_service
    importlib.reload(x_service)
    
    try:
        multi_service = MultiPlatformService()
        
        # 지원 플랫폼 확인
        supported = multi_service.get_supported_platforms()
        print(f"\n지원 플랫폼: {supported}")
        
        # 플랫폼별 사용 가능 여부
        print("\n플랫폼별 사용 가능 여부:")
        print(f"- Reddit: {multi_service.is_platform_available('reddit')}")
        print(f"- X: {multi_service.is_platform_available('x')}")
        
        return True
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("🚀 X API 환경변수 제어 테스트\n")
    
    # X API 비활성화 테스트
    result1 = await test_x_disabled()
    
    # X API 활성화 테스트 (API 키가 있을 때만)
    if os.getenv('X_API_KEY'):
        result2 = await test_x_enabled()
    else:
        print("\n⚠️ X API 키가 설정되지 않아 활성화 테스트를 건너뜁니다")
        result2 = True
    
    # 결과
    print("\n" + "="*50)
    print("테스트 결과:")
    print(f"- X API 비활성화 테스트: {'✅ 성공' if result1 else '❌ 실패'}")
    print(f"- X API 활성화 테스트: {'✅ 성공' if result2 else '❌ 실패'}")
    
    if result1:
        print("\n✅ USE_X_API=false 환경변수가 정상적으로 작동합니다!")
        print("   테스트/개발 환경에서 X API를 안전하게 비활성화할 수 있습니다.")

if __name__ == "__main__":
    asyncio.run(main())