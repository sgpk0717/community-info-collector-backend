import asyncio
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import json

# .env 파일 로드
load_dotenv()

# Supabase 클라이언트 생성
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

async def create_sample_data():
    """샘플 데이터 생성"""
    
    # 1. 샘플 사용자 생성
    print("Creating sample users...")
    users = [
        {
            "nickname": "test_user",
            "approval_status": "Y",
            "created_at": datetime.now().isoformat(),
            "last_access": datetime.now().isoformat()
        },
        {
            "nickname": "demo_user",
            "approval_status": "Y",
            "created_at": (datetime.now() - timedelta(days=7)).isoformat(),
            "last_access": (datetime.now() - timedelta(hours=2)).isoformat()
        },
        {
            "nickname": "sample_user",
            "approval_status": "Y",
            "created_at": (datetime.now() - timedelta(days=30)).isoformat(),
            "last_access": (datetime.now() - timedelta(days=1)).isoformat()
        }
    ]
    
    for user in users:
        try:
            # 이미 존재하는지 확인
            existing = supabase.table('users').select("*").eq('nickname', user['nickname']).execute()
            if not existing.data:
                result = supabase.table('users').insert(user).execute()
                print(f"✅ Created user: {user['nickname']}")
            else:
                print(f"ℹ️  User already exists: {user['nickname']}")
        except Exception as e:
            print(f"❌ Error creating user {user['nickname']}: {e}")
    
    # 2. 샘플 보고서 생성
    print("\nCreating sample reports...")
    reports = [
        {
            "user_nickname": "test_user",
            "query_text": "테슬라의 미래",
            "summary": "테슬라의 미래에 대한 커뮤니티의 전반적인 의견은 긍정적이며, 특히 자율주행 기술과 에너지 사업 확장에 대한 기대가 높습니다.",
            "full_report": """## 테슬라의 미래 분석 보고서

### 핵심 요약
테슬라의 미래에 대한 Reddit 커뮤니티의 의견을 분석한 결과, 전반적으로 긍정적인 전망이 우세했습니다. 특히 자율주행(FSD) 기술의 발전과 에너지 저장 사업의 성장 가능성에 대한 기대가 높았습니다.

### 주요 토픽
1. **자율주행 기술 (FSD)**
   - 대부분의 사용자가 FSD의 지속적인 개선을 긍정적으로 평가
   - 완전 자율주행 실현 시기에 대해서는 의견이 분분

2. **에너지 사업**
   - 태양광 패널과 에너지 저장 시스템(ESS)의 성장 잠재력
   - 전기차 사업과의 시너지 효과 기대

3. **경쟁 환경**
   - 중국 전기차 업체들의 빠른 성장에 대한 우려
   - 전통 자동차 제조사들의 전기차 전환 가속화

### 커뮤니티 반응
- 긍정적: 70%
- 중립적: 20%
- 부정적: 10%

### 종합 분석
Reddit 커뮤니티는 테슬라의 장기적 성장 잠재력을 높게 평가하고 있습니다.""",
            "posts_collected": 46,
            "report_length": "moderate",
            "session_id": "session_001",
            "created_at": datetime.now().isoformat()
        },
        {
            "user_nickname": "demo_user",
            "query_text": "애플 비전프로",
            "summary": "애플 비전프로에 대한 커뮤니티 반응은 혁신적인 기술력을 인정하면서도 높은 가격과 실용성에 대한 우려가 공존합니다.",
            "full_report": """## 애플 비전프로 분석 보고서

### 핵심 요약
애플 비전프로에 대한 Reddit 커뮤니티의 반응을 분석한 결과, 기술적 혁신성은 인정받고 있으나 가격과 실용성 측면에서 논란이 있습니다.

### 주요 토픽
1. **가격 문제**
   - $3,499의 높은 가격에 대한 부담감
   - 가격 대비 가치에 대한 논쟁

2. **사용 경험**
   - 몰입감 있는 경험에 대한 긍정적 평가
   - 장시간 착용 시 불편함 호소

### 커뮤니티 반응
- 긍정적: 45%
- 중립적: 35%
- 부정적: 20%""",
            "posts_collected": 32,
            "report_length": "moderate",
            "session_id": "session_002",
            "created_at": (datetime.now() - timedelta(days=1)).isoformat()
        },
        {
            "user_nickname": "sample_user",
            "query_text": "ChatGPT 활용법",
            "summary": "ChatGPT 활용에 대한 커뮤니티는 프로그래밍, 콘텐츠 작성, 학습 도구 등 다양한 분야에서의 활용 사례를 공유하고 있습니다.",
            "full_report": """## ChatGPT 활용법 분석 보고서

### 핵심 요약
Reddit 커뮤니티에서는 ChatGPT를 다양한 분야에서 활용하는 방법들이 활발히 공유되고 있으며, 특히 프로그래밍과 콘텐츠 작성 분야에서 높은 만족도를 보이고 있습니다.

### 주요 활용 분야
1. **프로그래밍 지원**
   - 코드 디버깅 및 최적화
   - 새로운 프로그래밍 언어 학습

2. **콘텐츠 작성**
   - 블로그 포스트 작성
   - 이메일 및 보고서 작성

3. **학습 도구**
   - 복잡한 개념 설명
   - 언어 학습 보조""",
            "posts_collected": 58,
            "report_length": "simple",
            "session_id": "session_003",
            "created_at": (datetime.now() - timedelta(days=3)).isoformat()
        }
    ]
    
    for report in reports:
        try:
            result = supabase.table('reports').insert(report).execute()
            print(f"✅ Created report: {report['query_text']}")
        except Exception as e:
            print(f"❌ Error creating report: {e}")
    
    # 3. 샘플 스케줄 생성
    print("\nCreating sample schedules...")
    schedules = [
        {
            "user_nickname": "test_user",
            "keyword": "AI 트렌드",
            "interval_minutes": 1440,  # 매일 (24시간)
            "report_length": "moderate",
            "total_reports": 10,
            "completed_reports": 3,
            "status": "active",
            "next_run": (datetime.now() + timedelta(hours=1)).isoformat(),
            "last_run": (datetime.now() - timedelta(hours=23)).isoformat(),
            "notification_enabled": True,
            "is_executing": False,
            "created_at": (datetime.now() - timedelta(days=3)).isoformat()
        },
        {
            "user_nickname": "demo_user",
            "keyword": "메타버스 동향",
            "interval_minutes": 10080,  # 매주 (7일)
            "report_length": "detailed",
            "total_reports": 5,
            "completed_reports": 1,
            "status": "active",
            "next_run": (datetime.now() + timedelta(days=2)).isoformat(),
            "last_run": (datetime.now() - timedelta(days=5)).isoformat(),
            "notification_enabled": True,
            "is_executing": False,
            "created_at": (datetime.now() - timedelta(days=7)).isoformat()
        },
        {
            "user_nickname": "sample_user",
            "keyword": "블록체인 기술",
            "interval_minutes": 720,  # 12시간마다
            "report_length": "simple",
            "total_reports": 20,
            "completed_reports": 15,
            "status": "paused",
            "next_run": None,
            "last_run": (datetime.now() - timedelta(days=2)).isoformat(),
            "notification_enabled": False,
            "is_executing": False,
            "created_at": (datetime.now() - timedelta(days=10)).isoformat()
        }
    ]
    
    for schedule in schedules:
        try:
            result = supabase.table('schedules').insert(schedule).execute()
            print(f"✅ Created schedule: {schedule['keyword']} ({schedule['status']})")
        except Exception as e:
            print(f"❌ Error creating schedule: {e}")
    
    print("\n✨ Sample data creation completed!")
    
    # 데이터 통계 출력
    print("\n📊 Data Statistics:")
    print(f"- Users: {len(users)}")
    print(f"- Reports: {len(reports)}")
    print(f"- Schedules: {len(schedules)}")
    
    # 각 사용자별 요약
    print("\n👥 User Summary:")
    for user in users:
        user_reports = [r for r in reports if r['user_nickname'] == user['nickname']]
        user_schedules = [s for s in schedules if s['user_nickname'] == user['nickname']]
        print(f"- {user['nickname']}: {len(user_reports)} reports, {len(user_schedules)} schedules")

if __name__ == "__main__":
    asyncio.run(create_sample_data())