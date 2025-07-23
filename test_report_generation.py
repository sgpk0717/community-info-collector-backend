import asyncio
from datetime import datetime
import json
from app.services.llm_service import LLMService
from app.services.reddit_service import RedditService
from app.schemas.enums import TimeFilter

async def test_report_with_footnotes():
    """보고서 생성 시 각주 변환이 제대로 되는지 테스트"""
    
    # 서비스 초기화
    llm_service = LLMService()
    reddit_service = RedditService()
    
    # 테스트 키워드와 시간 필터
    keyword = "구글 실적"
    time_filter = TimeFilter.ONE_DAY  # 24시간
    
    print(f"🔍 테스트 시작: '{keyword}' 키워드로 {time_filter.value} 기간 검색\n")
    
    # Reddit 검색
    try:
        posts = await reddit_service.search_posts(
            query=keyword,
            time_filter=time_filter,
            limit=10
        )
        
        print(f"📊 수집된 게시물: {len(posts)}개")
        
        # 게시물 시간 확인
        for i, post in enumerate(posts[:3]):
            created_time = datetime.fromtimestamp(post['created_utc'])
            hours_ago = (datetime.now() - created_time).total_seconds() / 3600
            print(f"\n게시물 {i+1}:")
            print(f"  제목: {post['title'][:50]}...")
            print(f"  작성 시간: {created_time} ({hours_ago:.1f}시간 전)")
            print(f"  ID: {post['id']}")
        
        # 보고서 생성
        print("\n\n📝 보고서 생성 중...")
        report_data = await llm_service.generate_report(
            posts=posts,
            query=keyword,
            length='moderate'
        )
        
        # 결과 확인
        print("\n✅ 보고서 생성 완료!")
        print(f"\n요약 (처음 200자):\n{report_data['summary'][:200]}...")
        
        # 각주 확인
        if '[ref:' in report_data['full_report']:
            print("\n⚠️  문제 발견: 보고서에 [ref:POST_XXX] 형식이 남아있음!")
            # [ref:XXX] 패턴 찾기
            import re
            refs = re.findall(r'\[ref:[^\]]+\]', report_data['full_report'])
            print(f"발견된 미변환 참조: {refs[:5]}")
        else:
            print("\n✅ 각주 변환 정상: [ref:XXX] 형식이 모두 [1], [2] 등으로 변환됨")
            # [1], [2] 패턴 찾기
            import re
            footnotes = re.findall(r'\[\d+\]', report_data['full_report'])
            print(f"발견된 각주: {set(footnotes)}")
        
        # footnote_mapping 확인
        if 'footnote_mapping' in report_data:
            print(f"\n📌 각주 매핑 정보: {len(report_data['footnote_mapping'])}개")
            for fm in report_data['footnote_mapping'][:3]:
                print(f"  [{fm['footnote_number']}] {fm['title'][:50]}...")
        
        # 보고서 끝부분 확인 (참조 목록)
        report_lines = report_data['full_report'].split('\n')
        if any('참조 목록' in line for line in report_lines):
            print("\n✅ '참조 목록' 섹션이 보고서에 포함됨")
        else:
            print("\n⚠️  '참조 목록' 섹션이 보고서에 없음")
            
    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_report_with_footnotes())