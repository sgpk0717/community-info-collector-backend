import logging
from typing import List, Dict, Any, Optional, Tuple
import re
import json
from datetime import datetime
from app.core.dependencies import get_supabase_client
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class FootnoteService:
    """
    각주 시스템 관리 서비스
    
    주요 기능:
    1. 보고서 내 [ref:POST_ID] 형태 참조를 자동으로 [1], [2] 등 번호로 변환
    2. 각주 번호와 원본 게시물 URL 매핑 관리
    3. 보고서 하단에 참조 목록 자동 생성
    4. 글로벌 각주 관리로 중복 참조 방지
    """
    
    def __init__(self):
        logger.info("📎 FootnoteService 초기화")
        self.client = get_supabase_client()
        self.llm_service = LLMService()
        
    async def process_report_with_footnotes(self, session_id: str, report_content: str, 
                                          posts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """보고서에 각주 시스템 적용"""
        logger.info(f"📎 보고서 각주 처리 시작 - Session: {session_id}")
        
        try:
            # 1. 보고서에 각주 참조 자동 삽입
            enhanced_report = await self._add_footnotes_to_report(report_content, posts_data)
            
            # 2. 각주 매핑 정보 추출
            footnote_mapping = self._extract_footnote_mapping(enhanced_report, posts_data)
            
            # 3. [ref:POST_ID] 형태를 [1], [2] 번호로 변환
            processed_report = self._convert_refs_to_numbers(enhanced_report, footnote_mapping)
            
            # 4. 참조 목록 추가
            final_report = self._add_references_section(processed_report, footnote_mapping)
            
            # 5. 각주 정보를 데이터베이스에 저장
            await self._save_footnote_mapping(session_id, footnote_mapping)
            
            logger.info(f"✅ 각주 처리 완료 - {len(footnote_mapping)}개 각주 생성")
            
            return {
                'processed_report': final_report,
                'footnote_mapping': footnote_mapping,
                'footnote_count': len(footnote_mapping)
            }
            
        except Exception as e:
            logger.error(f"❌ 각주 처리 실패: {str(e)}")
            # 에러 발생 시 원본 보고서 반환
            return {
                'processed_report': report_content,
                'footnote_mapping': [],
                'footnote_count': 0
            }
    
    async def _add_footnotes_to_report(self, report_content: str, posts_data: List[Dict[str, Any]]) -> str:
        """보고서에 각주 참조 자동 삽입"""
        logger.info("📝 보고서에 각주 참조 삽입 중...")
        
        # 게시물 정보를 요약하여 LLM에 전달
        posts_summary = []
        for post in posts_data[:10]:  # 최대 10개만 사용
            post_summary = {
                'id': post.get('id', 'unknown'),
                'title': post.get('title', '')[:100],
                'content': post.get('selftext', '')[:200],
                'score': post.get('score', 0),
                'url': post.get('url', '')
            }
            posts_summary.append(post_summary)
        
        # LLM을 사용하여 적절한 위치에 각주 삽입
        prompt = f"""다음 보고서를 분석하고, 특정 게시물이나 의견을 참조할 때 각주를 삽입해주세요.

보고서:
{report_content}

사용 가능한 게시물들:
{json.dumps(posts_summary, ensure_ascii=False, indent=2)}

규칙:
1. 구체적인 통계나 사실을 언급할 때 [ref:POST_ID] 형태로 각주를 삽입
2. 특정 사용자의 의견을 인용할 때 각주 삽입
3. 중요한 정보의 출처를 명시할 때 각주 삽입
4. 각주는 문장이나 단락 끝에 삽입
5. 하나의 문장에 여러 각주가 있을 수 있음: [ref:POST_ID1][ref:POST_ID2]

예시:
- "테슬라 주가가 30% 상승했다는 보고가 있습니다[ref:t3_abc123]."
- "한 사용자는 FSD 기술이 완벽하다고 평가했습니다[ref:t3_def456]."

게시물 ID를 정확히 매칭하여 각주를 삽입한 보고서를 작성해주세요."""
        
        try:
            enhanced_report = await self.llm_service._call_openai(prompt, temperature=0.3)
            logger.info("✅ 각주 삽입 완료")
            return enhanced_report
            
        except Exception as e:
            logger.error(f"각주 삽입 실패: {str(e)}")
            # 실패 시 원본 반환
            return report_content
    
    def _extract_footnote_mapping(self, report: str, posts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """보고서에서 각주 매핑 정보 추출"""
        logger.info("🔍 각주 매핑 정보 추출 중...")
        
        footnote_mapping = []
        posts_by_id = {post['id']: post for post in posts_data}
        
        # [ref:POST_ID] 패턴 찾기
        ref_pattern = r'\[ref:([^\]]+)\]'
        refs = re.findall(ref_pattern, report)
        
        if not refs:
            logger.info("📄 참조가 발견되지 않음")
            return footnote_mapping
        
        # 고유한 참조들을 순서대로 번호 할당
        unique_refs = []
        for ref in refs:
            if ref not in [item['post_id'] for item in footnote_mapping]:
                unique_refs.append(ref)
        
        for i, post_id in enumerate(unique_refs, 1):
            if post_id in posts_by_id:
                post = posts_by_id[post_id]
                footnote_mapping.append({
                    'footnote_number': i,
                    'post_id': post_id,
                    'url': post.get('url', ''),
                    'title': post.get('title', ''),
                    'score': post.get('score', 0),
                    'comments': post.get('num_comments', 0),
                    'created_utc': post.get('created_utc', ''),
                    'subreddit': post.get('subreddit', ''),
                    'author': post.get('author', ''),
                    'position_in_report': i
                })
            else:
                logger.warning(f"⚠️ 참조된 POST_ID를 찾을 수 없음: {post_id}")
        
        logger.info(f"✅ 각주 매핑 완료: {len(footnote_mapping)}개")
        return footnote_mapping
    
    def _convert_refs_to_numbers(self, report: str, footnote_mapping: List[Dict[str, Any]]) -> str:
        """[ref:POST_ID] 형태를 [1], [2] 번호로 변환"""
        logger.info("🔄 참조 번호 변환 중...")
        
        # POST_ID -> 번호 매핑 생성
        id_to_number = {
            item['post_id']: item['footnote_number']
            for item in footnote_mapping
        }
        
        # 변환 함수
        def replace_ref(match):
            post_id = match.group(1)
            if post_id in id_to_number:
                return f"[{id_to_number[post_id]}]"
            return match.group(0)  # 매핑이 없으면 원본 유지
        
        processed_report = re.sub(r'\[ref:([^\]]+)\]', replace_ref, report)
        logger.info("✅ 참조 번호 변환 완료")
        
        return processed_report
    
    def _add_references_section(self, report: str, footnote_mapping: List[Dict[str, Any]]) -> str:
        """보고서 하단에 참조 목록 추가"""
        if not footnote_mapping:
            return report
        
        logger.info("📋 참조 목록 추가 중...")
        
        references_section = "\n\n## 📚 참조 목록\n\n"
        
        for item in footnote_mapping:
            # 참조 정보 포맷팅
            ref_line = f"[{item['footnote_number']}] **{item['title']}**"
            
            # 서브레딧 정보 추가
            if item['subreddit']:
                ref_line += f" - r/{item['subreddit']}"
            
            # 점수 및 댓글 수 추가
            ref_line += f" (↑{item['score']}, 💬{item['comments']})"
            
            # URL 추가
            if item['url']:
                ref_line += f"\n   🔗 {item['url']}"
            
            references_section += ref_line + "\n\n"
        
        final_report = report + references_section
        logger.info("✅ 참조 목록 추가 완료")
        
        return final_report
    
    async def _save_footnote_mapping(self, session_id: str, footnote_mapping: List[Dict[str, Any]]):
        """각주 매핑 정보를 데이터베이스에 저장"""
        logger.info("💾 각주 매핑 정보 저장 중...")
        
        try:
            # analysis_sections 테이블에 각주 정보 저장
            footnote_data = {
                'session_id': session_id,
                'analysis_type': 'footnote_mapping',
                'analysis_data': {
                    'footnote_mapping': footnote_mapping,
                    'footnote_count': len(footnote_mapping),
                    'created_at': datetime.now().isoformat()
                }
            }
            
            result = self.client.table('analysis_sections').insert(footnote_data).execute()
            
            if result.data:
                logger.info(f"✅ 각주 매핑 정보 저장 완료")
            else:
                logger.warning("⚠️ 각주 매핑 정보 저장 실패")
                
        except Exception as e:
            logger.error(f"❌ 각주 매핑 저장 중 오류: {str(e)}")
    
    async def get_footnote_mapping(self, session_id: str) -> List[Dict[str, Any]]:
        """세션 ID로 각주 매핑 정보 조회"""
        try:
            result = self.client.table('analysis_sections')\
                .select('analysis_data')\
                .eq('session_id', session_id)\
                .eq('analysis_type', 'footnote_mapping')\
                .execute()
            
            if result.data:
                return result.data[0]['analysis_data']['footnote_mapping']
            return []
            
        except Exception as e:
            logger.error(f"각주 매핑 조회 실패: {str(e)}")
            return []
    
    def create_clickable_footnotes(self, report: str, footnote_mapping: List[Dict[str, Any]]) -> str:
        """프론트엔드에서 클릭 가능한 각주 생성을 위한 특수 마크업 추가"""
        logger.info("🔗 클릭 가능한 각주 마크업 생성 중...")
        
        # 각주 번호를 클릭 가능한 링크로 변환
        def make_clickable(match):
            footnote_num = match.group(1)
            # 특수 마크업 추가 (프론트엔드에서 처리)
            return f'<footnote data-id="{footnote_num}">[{footnote_num}]</footnote>'
        
        # [숫자] 패턴을 클릭 가능한 형태로 변환
        clickable_report = re.sub(r'\[(\d+)\]', make_clickable, report)
        
        logger.info("✅ 클릭 가능한 각주 마크업 생성 완료")
        return clickable_report
    
    async def validate_footnotes(self, report: str, posts_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """각주 유효성 검증"""
        logger.info("🔍 각주 유효성 검증 중...")
        
        # 보고서에서 모든 각주 찾기
        footnote_refs = re.findall(r'\[ref:([^\]]+)\]', report)
        numbered_refs = re.findall(r'\[(\d+)\]', report)
        
        # 게시물 ID 목록
        available_post_ids = [post['id'] for post in posts_data]
        
        # 검증 결과
        validation_result = {
            'total_footnote_refs': len(footnote_refs),
            'total_numbered_refs': len(numbered_refs),
            'valid_refs': [],
            'invalid_refs': [],
            'missing_posts': []
        }
        
        # 각주 참조 유효성 검증
        for ref in footnote_refs:
            if ref in available_post_ids:
                validation_result['valid_refs'].append(ref)
            else:
                validation_result['invalid_refs'].append(ref)
        
        # 누락된 게시물 체크
        for post_id in available_post_ids:
            if post_id not in footnote_refs:
                validation_result['missing_posts'].append(post_id)
        
        logger.info(f"✅ 각주 유효성 검증 완료 - 유효: {len(validation_result['valid_refs'])}개, 무효: {len(validation_result['invalid_refs'])}개")
        
        return validation_result