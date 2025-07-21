from typing import List, Dict, Any, Optional
from app.services.llm_service import LLMService
import logging
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class RelevanceFilteringService:
    """관련성 기반 콘텐츠 필터링 서비스
    
    수집된 게시물과 댓글 중에서 키워드와 실제로 관련성이 높은 내용만 선별하여
    보고서 품질을 향상시키는 LLM 기반 필터링 시스템
    """
    
    def __init__(self, thread_pool: Optional[ThreadPoolExecutor] = None, api_semaphore: Optional[asyncio.Semaphore] = None):
        self.llm_service = LLMService(api_semaphore=api_semaphore)
        self.thread_pool = thread_pool
        self.api_semaphore = api_semaphore
        
        # 관련성 점수 임계값
        self.RELEVANCE_THRESHOLD = 6.0  # 10점 만점 중 6점 이상만 통과
        self.MIN_HIGH_QUALITY_POSTS = 10  # 최소 10개의 고품질 게시물 보장
        self.MAX_CONTENT_ITEMS = 50  # 최대 50개 아이템 처리 (성능 고려)
    
    async def filter_relevant_content(
        self, 
        content_items: List[Dict[str, Any]], 
        query: str, 
        expanded_keywords: List[str] = None
    ) -> List[Dict[str, Any]]:
        """관련성 기반 콘텐츠 필터링
        
        Args:
            content_items: 게시물과 댓글이 포함된 콘텐츠 목록
            query: 원본 검색 키워드
            expanded_keywords: 확장된 키워드 목록
        
        Returns:
            관련성이 높은 콘텐츠만 선별된 목록
        """
        if not content_items:
            logger.warning("📭 필터링할 콘텐츠가 없습니다")
            return []
        
        logger.info(f"🔍 관련성 필터링 시작 - 대상: {len(content_items)}개 콘텐츠")
        logger.info(f"   키워드: '{query}'")
        if expanded_keywords:
            logger.info(f"   확장 키워드: {len(expanded_keywords)}개")
        
        # 성능을 위해 콘텐츠 수 제한
        if len(content_items) > self.MAX_CONTENT_ITEMS:
            logger.info(f"⚡ 성능 최적화를 위해 상위 {self.MAX_CONTENT_ITEMS}개 콘텐츠만 필터링")
            # 점수 기준으로 상위 콘텐츠 선별
            content_items = sorted(content_items, key=lambda x: x.get('score', 0), reverse=True)[:self.MAX_CONTENT_ITEMS]
        
        # 콘텐츠를 배치로 나누어 처리 (LLM API 효율성을 위해)
        batch_size = 10  # 한 번에 10개씩 처리
        batches = [content_items[i:i + batch_size] for i in range(0, len(content_items), batch_size)]
        
        all_filtered_content = []
        
        for batch_idx, batch in enumerate(batches):
            try:
                logger.info(f"🔍 배치 {batch_idx + 1}/{len(batches)} 처리 중 ({len(batch)}개 콘텐츠)")
                
                # 배치별 관련성 점수 계산
                scored_content = await self._score_content_relevance(batch, query, expanded_keywords)
                
                # 임계값 이상의 콘텐츠만 선별
                filtered_batch = [
                    item for item in scored_content 
                    if item.get('relevance_score', 0) >= self.RELEVANCE_THRESHOLD
                ]
                
                all_filtered_content.extend(filtered_batch)
                logger.info(f"✅ 배치 {batch_idx + 1} 완료: {len(filtered_batch)}/{len(batch)}개 통과")
                
            except Exception as e:
                logger.error(f"❌ 배치 {batch_idx + 1} 처리 중 오류: {str(e)}")
                # 오류 발생 시 원본 콘텐츠를 그대로 포함 (안정성 우선)
                all_filtered_content.extend(batch)
                continue
        
        # 관련성 점수 기준으로 정렬
        all_filtered_content.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # 최소 고품질 게시물 수 보장
        final_content = self._ensure_minimum_quality_content(all_filtered_content, content_items)
        
        logger.info(f"🎯 관련성 필터링 완료")
        logger.info(f"   원본: {len(content_items)}개 → 필터링 후: {len(final_content)}개")
        logger.info(f"   평균 관련성 점수: {self._calculate_average_score(final_content):.1f}/10")
        
        return final_content
    
    async def _score_content_relevance(
        self, 
        content_batch: List[Dict[str, Any]], 
        query: str, 
        expanded_keywords: List[str] = None
    ) -> List[Dict[str, Any]]:
        """콘텐츠 배치의 관련성 점수 계산"""
        
        # 키워드 목록 준비
        all_keywords = [query]
        if expanded_keywords:
            all_keywords.extend(expanded_keywords[:10])  # 상위 10개 키워드만 사용
        
        # 콘텐츠 정보를 LLM용 텍스트로 변환
        content_descriptions = []
        for idx, item in enumerate(content_batch):
            item_type = item.get('type', 'unknown')
            title = item.get('title', '제목 없음') if item_type == 'post' else '댓글'
            content = item.get('content', item.get('selftext', '내용 없음'))[:300]  # 300자 제한
            score = item.get('score', 0)
            
            description = f"""[{idx + 1}] {item_type.upper()}: {title}
내용: {content}
점수: {score}
---"""
            content_descriptions.append(description)
        
        prompt = f"""다음은 "{query}" 키워드로 수집된 콘텐츠들입니다.

관련 키워드: {', '.join(all_keywords)}

수집된 콘텐츠:
{chr(10).join(content_descriptions)}

각 콘텐츠의 관련성을 0-10점으로 평가해주세요:

평가 기준:
- 9-10점: 키워드와 직접적으로 매우 관련성이 높음 (핵심 내용)
- 7-8점: 키워드와 관련성이 높음 (중요한 내용)  
- 5-6점: 키워드와 어느 정도 관련성 있음 (참고 내용)
- 3-4점: 키워드와 간접적으로만 관련됨 (부차적 내용)
- 0-2점: 키워드와 관련성이 거의 없음 (무관한 내용)

특별 고려사항:
- 구체적인 사례, 경험담, 데이터가 포함된 콘텐츠는 가점
- 추측성, 루머성 내용은 감점
- 감정적 반응만 있고 실질적 정보가 없으면 감점

JSON 형식으로 응답해주세요:
[
    {{"content_index": 1, "relevance_score": 8.5, "reason": "구체적인 사례와 데이터 포함"}},
    {{"content_index": 2, "relevance_score": 6.0, "reason": "키워드와 관련있으나 일반적인 내용"}},
    ...
]"""

        try:
            response = await self.llm_service._call_llm(prompt, temperature=0.3)
            
            # JSON 응답 파싱
            scores_data = self._parse_relevance_scores(response)
            
            # 점수를 원본 콘텐츠에 적용
            scored_content = []
            for item in content_batch:
                # 기본값: 중간 점수 (필터링 실패 시 안전장치)
                relevance_score = 5.0
                reason = "점수 계산 실패"
                
                # 해당 콘텐츠의 점수 찾기
                content_idx = content_batch.index(item) + 1
                for score_item in scores_data:
                    if score_item.get('content_index') == content_idx:
                        relevance_score = float(score_item.get('relevance_score', 5.0))
                        reason = score_item.get('reason', '이유 없음')
                        break
                
                # 점수 정보 추가
                enhanced_item = item.copy()
                enhanced_item['relevance_score'] = relevance_score
                enhanced_item['relevance_reason'] = reason
                
                scored_content.append(enhanced_item)
            
            return scored_content
            
        except Exception as e:
            logger.error(f"❌ 관련성 점수 계산 실패: {str(e)}")
            # 오류 시 기본 점수로 반환
            return [
                {**item, 'relevance_score': 5.0, 'relevance_reason': 'LLM 평가 실패'}
                for item in content_batch
            ]
    
    def _parse_relevance_scores(self, llm_response: str) -> List[Dict[str, Any]]:
        """LLM 응답에서 관련성 점수 파싱"""
        try:
            # JSON 블록 추출
            response_clean = llm_response.strip()
            if '```json' in response_clean:
                response_clean = response_clean.split('```json')[1].split('```')[0].strip()
            elif '```' in response_clean:
                response_clean = response_clean.split('```')[1].strip()
            
            scores_data = json.loads(response_clean)
            
            # 데이터 유효성 검증
            if not isinstance(scores_data, list):
                raise ValueError("응답이 리스트 형태가 아님")
            
            # 각 항목 검증 및 정리
            validated_scores = []
            for item in scores_data:
                if isinstance(item, dict) and 'content_index' in item and 'relevance_score' in item:
                    # 점수 범위 제한 (0-10)
                    score = max(0.0, min(10.0, float(item['relevance_score'])))
                    validated_scores.append({
                        'content_index': int(item['content_index']),
                        'relevance_score': score,
                        'reason': item.get('reason', '이유 없음')
                    })
            
            return validated_scores
            
        except Exception as e:
            logger.warning(f"⚠️ LLM 응답 파싱 실패: {str(e)}")
            logger.warning(f"   응답 내용: {llm_response[:200]}...")
            return []
    
    def _ensure_minimum_quality_content(
        self, 
        filtered_content: List[Dict[str, Any]], 
        original_content: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """최소 고품질 콘텐츠 수 보장"""
        
        if len(filtered_content) >= self.MIN_HIGH_QUALITY_POSTS:
            return filtered_content
        
        logger.info(f"📈 최소 품질 콘텐츠 수 미달 ({len(filtered_content)}/{self.MIN_HIGH_QUALITY_POSTS})")
        logger.info("   추가 콘텐츠를 포함합니다")
        
        # 이미 포함된 콘텐츠 ID 목록
        included_ids = {item.get('id') for item in filtered_content}
        
        # 원본에서 아직 포함되지 않은 콘텐츠 중 점수가 높은 것들 추가
        additional_content = [
            item for item in original_content 
            if item.get('id') not in included_ids
        ]
        
        # 점수 기준으로 정렬하여 추가
        additional_content.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # 필요한 만큼 추가
        needed_count = self.MIN_HIGH_QUALITY_POSTS - len(filtered_content)
        selected_additional = additional_content[:needed_count]
        
        # 추가된 콘텐츠에 기본 관련성 점수 부여
        for item in selected_additional:
            if 'relevance_score' not in item:
                item['relevance_score'] = 5.5  # 임계값보다 약간 높은 기본 점수
                item['relevance_reason'] = '최소 콘텐츠 수 보장을 위해 추가'
        
        final_content = filtered_content + selected_additional
        logger.info(f"✅ 총 {len(final_content)}개 콘텐츠로 조정 완료")
        
        return final_content
    
    def _calculate_average_score(self, content_list: List[Dict[str, Any]]) -> float:
        """평균 관련성 점수 계산"""
        if not content_list:
            return 0.0
        
        scores = [item.get('relevance_score', 0) for item in content_list]
        return sum(scores) / len(scores)
    
    async def get_filtering_summary(self, filtered_content: List[Dict[str, Any]]) -> Dict[str, Any]:
        """필터링 결과 요약 정보 생성"""
        
        if not filtered_content:
            return {
                'total_count': 0,
                'high_quality_count': 0,
                'average_score': 0.0,
                'score_distribution': {}
            }
        
        total_count = len(filtered_content)
        high_quality_count = len([item for item in filtered_content if item.get('relevance_score', 0) >= 8.0])
        average_score = self._calculate_average_score(filtered_content)
        
        # 점수 분포 계산
        score_ranges = {
            '9-10점 (최고품질)': 0,
            '7-8점 (고품질)': 0,
            '5-6점 (보통품질)': 0,
            '3-4점 (낮은품질)': 0,
            '0-2점 (매우낮음)': 0
        }
        
        for item in filtered_content:
            score = item.get('relevance_score', 0)
            if score >= 9:
                score_ranges['9-10점 (최고품질)'] += 1
            elif score >= 7:
                score_ranges['7-8점 (고품질)'] += 1
            elif score >= 5:
                score_ranges['5-6점 (보통품질)'] += 1
            elif score >= 3:
                score_ranges['3-4점 (낮은품질)'] += 1
            else:
                score_ranges['0-2점 (매우낮음)'] += 1
        
        return {
            'total_count': total_count,
            'high_quality_count': high_quality_count,
            'average_score': average_score,
            'score_distribution': score_ranges
        }