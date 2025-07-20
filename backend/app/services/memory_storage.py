from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class MemoryStorage:
    """메모리 기반 간단한 저장소 (테스트용)"""
    
    def __init__(self):
        self.reports: Dict[str, Dict] = {}
        self.users: Dict[str, Dict] = {}
    
    def save_report(self, user_nickname: str, query: str, summary: str, full_report: str, 
                   posts_collected: int = 0, session_id: str = None) -> str:
        """보고서 저장"""
        report_id = str(uuid.uuid4())
        
        report = {
            "id": report_id,
            "user_nickname": user_nickname,
            "query_text": query,
            "summary": summary,
            "full_report": full_report,
            "posts_collected": posts_collected,
            "session_id": session_id,
            "created_at": datetime.now().isoformat()
        }
        
        self.reports[report_id] = report
        
        logger.info(f"📝 보고서 저장 완료: {report_id}")
        return report_id
    
    def get_user_reports(self, user_nickname: str) -> List[Dict]:
        """사용자 보고서 목록 조회"""
        user_reports = []
        
        for report in self.reports.values():
            if report["user_nickname"] == user_nickname:
                user_reports.append(report)
        
        # 생성 시간 역순으로 정렬
        user_reports.sort(key=lambda x: x["created_at"], reverse=True)
        
        logger.info(f"📋 사용자 보고서 조회: {user_nickname} - {len(user_reports)}개")
        return user_reports
    
    def get_report_by_id(self, report_id: str) -> Optional[Dict]:
        """보고서 상세 조회"""
        return self.reports.get(report_id)
    
    def create_user(self, user_nickname: str, email: str = None) -> Dict:
        """사용자 생성"""
        user = {
            "id": str(uuid.uuid4()),
            "user_nickname": user_nickname,
            "email": email,
            "created_at": datetime.now().isoformat()
        }
        
        self.users[user_nickname] = user
        
        logger.info(f"👤 사용자 생성: {user_nickname}")
        return user
    
    def get_user(self, user_nickname: str) -> Optional[Dict]:
        """사용자 조회"""
        return self.users.get(user_nickname)

# 전역 인스턴스
memory_storage = MemoryStorage()