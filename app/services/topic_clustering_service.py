from typing import List, Dict, Any, Optional, Tuple
from app.services.llm_service import LLMService
import logging
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

logger = logging.getLogger(__name__)

class TopicClusteringService:
    """동적 주제 클러스터링 서비스
    
    필터링된 콘텐츠를 의미있는 주제별로 자동 그룹화하여
    체계적이고 구조화된 보고서 생성을 지원합니다.
    """
    
    def __init__(self, thread_pool: Optional[ThreadPoolExecutor] = None, api_semaphore: Optional[asyncio.Semaphore] = None):
        self.llm_service = LLMService(api_semaphore=api_semaphore)
        self.thread_pool = thread_pool
        self.api_semaphore = api_semaphore
        
        # 클러스터링 설정
        self.MIN_CLUSTER_SIZE = 3  # 클러스터로 인정되는 최소 콘텐츠 수
        self.MAX_CLUSTERS = 7  # 최대 클러스터 수 (너무 많으면 복잡해짐)
        self.MAX_ITEMS_PER_BATCH = 20  # LLM 처리를 위한 배치 크기
    
    async def cluster_content(
        self, 
        content_items: List[Dict[str, Any]], 
        query: str
    ) -> Dict[str, Any]:
        """콘텐츠를 주제별로 클러스터링
        
        Args:
            content_items: 필터링된 고품질 콘텐츠 목록
            query: 원본 검색 키워드
        
        Returns:
            클러스터링 결과 (클러스터 목록, 통계, 메타데이터)
        """
        if not content_items:
            logger.warning("📭 클러스터링할 콘텐츠가 없습니다")
            return {
                'clusters': [],
                'unclustered': [],
                'statistics': {}
            }
        
        logger.info(f"🎯 주제 클러스터링 시작 - 대상: {len(content_items)}개 콘텐츠")
        logger.info(f"   키워드: '{query}'")
        
        # 1단계: 주제 추출
        topics = await self._extract_topics(content_items, query)
        logger.info(f"📋 추출된 주제: {len(topics)}개")
        for idx, topic in enumerate(topics[:5]):  # 상위 5개만 로그
            logger.info(f"   {idx+1}. {topic['name']} - {topic['description']}")
        
        # 2단계: 콘텐츠를 주제별로 분류
        clusters = await self._assign_content_to_topics(content_items, topics)
        
        # 3단계: 작은 클러스터 병합 및 정리
        final_clusters = self._optimize_clusters(clusters)
        
        # 4단계: 클러스터 통계 생성
        statistics = self._generate_cluster_statistics(final_clusters, content_items)
        
        logger.info(f"✅ 클러스터링 완료:")
        logger.info(f"   최종 클러스터: {len(final_clusters)}개")
        logger.info(f"   클러스터된 콘텐츠: {statistics['total_clustered']}개")
        logger.info(f"   미분류 콘텐츠: {statistics['total_unclustered']}개")
        
        return {
            'clusters': final_clusters,
            'unclustered': [item for item in content_items if not self._is_item_clustered(item, final_clusters)],
            'statistics': statistics
        }
    
    async def _extract_topics(self, content_items: List[Dict[str, Any]], query: str) -> List[Dict[str, str]]:
        """콘텐츠에서 주요 주제 추출"""
        
        # 샘플 콘텐츠 준비 (성능을 위해 일부만 사용)
        sample_size = min(len(content_items), 30)
        sample_items = sorted(content_items, key=lambda x: x.get('relevance_score', 0), reverse=True)[:sample_size]
        
        # 콘텐츠 텍스트 준비
        content_texts = []
        for idx, item in enumerate(sample_items):
            title = item.get('title', '') if item.get('type') == 'post' else ''
            content = item.get('content', item.get('selftext', ''))[:200]
            relevance = item.get('relevance_score', 0)
            
            text = f"[{idx+1}] {title}\n{content}\n관련성: {relevance}/10"
            content_texts.append(text)
        
        prompt = f"""다음은 "{query}" 키워드로 수집된 고품질 콘텐츠들입니다.

{chr(10).join(content_texts)}

이 콘텐츠들을 분석하여 주요 토픽/주제를 추출해주세요.

요구사항:
1. 5-7개의 명확하고 구별되는 주제를 추출
2. 각 주제는 여러 콘텐츠에서 공통적으로 나타나는 것이어야 함
3. 너무 광범위하거나 너무 세부적이지 않은 적절한 수준
4. 각 주제에 대한 간단한 설명 포함

JSON 형식으로 응답:
[
    {{
        "name": "주제명 (2-4 단어)",
        "description": "이 주제에 대한 간단한 설명 (1문장)",
        "keywords": ["관련", "키워드", "3-5개"]
    }},
    ...
]"""

        try:
            response = await self.llm_service._call_llm(prompt, temperature=0.3)
            topics = self._parse_topics_response(response)
            
            # 기본 주제가 없으면 추가
            if len(topics) < 3:
                topics.extend([
                    {"name": "일반 논의", "description": "특정 주제로 분류되지 않는 일반적인 논의", "keywords": ["general", "discussion"]},
                    {"name": "기타 의견", "description": "다양한 개인적 의견과 경험", "keywords": ["opinion", "experience"]}
                ])
            
            return topics[:self.MAX_CLUSTERS]
            
        except Exception as e:
            logger.error(f"❌ 주제 추출 실패: {str(e)}")
            # 오류 발생 시 예외를 전파
            raise Exception(f"LLM 주제 추출 실패: {str(e)}")
    
    async def _assign_content_to_topics(
        self, 
        content_items: List[Dict[str, Any]], 
        topics: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """각 콘텐츠를 적절한 주제에 할당"""
        
        clusters = []
        for topic in topics:
            clusters.append({
                'topic': topic,
                'items': [],
                'average_relevance': 0.0,
                'key_insights': []
            })
        
        # 배치로 나누어 처리
        batch_size = self.MAX_ITEMS_PER_BATCH
        for i in range(0, len(content_items), batch_size):
            batch = content_items[i:i + batch_size]
            
            # 각 배치에 대해 주제 할당
            assignments = await self._assign_batch_to_topics(batch, topics)
            
            # 할당 결과를 클러스터에 추가
            for item_idx, topic_idx in enumerate(assignments):
                if 0 <= topic_idx < len(clusters):
                    clusters[topic_idx]['items'].append(batch[item_idx])
        
        # 각 클러스터의 통계 계산
        for cluster in clusters:
            if cluster['items']:
                relevance_scores = [item.get('relevance_score', 0) for item in cluster['items']]
                cluster['average_relevance'] = sum(relevance_scores) / len(relevance_scores)
                
                # 핵심 인사이트 추출 (상위 3개 고득점 콘텐츠)
                top_items = sorted(cluster['items'], key=lambda x: x.get('score', 0), reverse=True)[:3]
                cluster['key_insights'] = [
                    {
                        'title': item.get('title', '제목 없음'),
                        'score': item.get('score', 0),
                        'type': item.get('type', 'unknown')
                    }
                    for item in top_items
                ]
        
        return clusters
    
    async def _assign_batch_to_topics(
        self, 
        batch: List[Dict[str, Any]], 
        topics: List[Dict[str, str]]
    ) -> List[int]:
        """배치 콘텐츠를 주제에 할당"""
        
        # 콘텐츠와 주제 정보 준비
        content_descriptions = []
        for idx, item in enumerate(batch):
            title = item.get('title', '') if item.get('type') == 'post' else '댓글'
            content = item.get('content', item.get('selftext', ''))[:150]
            content_descriptions.append(f"[{idx}] {title}\n{content}")
        
        topic_descriptions = []
        for idx, topic in enumerate(topics):
            topic_descriptions.append(f"[{idx}] {topic['name']}: {topic['description']}")
        
        prompt = f"""다음 콘텐츠들을 가장 적합한 주제에 할당해주세요.

주제 목록:
{chr(10).join(topic_descriptions)}

콘텐츠:
{chr(10).join(content_descriptions)}

각 콘텐츠에 대해 가장 적합한 주제의 번호를 할당하세요.
만약 어떤 주제에도 맞지 않으면 -1을 할당하세요.

JSON 배열로 응답 (콘텐츠 순서대로):
[0, 2, 1, -1, 0, ...]"""

        try:
            response = await self.llm_service._call_llm(prompt, temperature=0.2)
            assignments = self._parse_assignments_response(response, len(batch))
            return assignments
            
        except Exception as e:
            logger.error(f"❌ 주제 할당 실패: {str(e)}")
            # 오류 발생 시 예외를 전파
            raise Exception(f"LLM 주제 할당 실패 (배치): {str(e)}")
    
    def _optimize_clusters(self, clusters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """작은 클러스터 병합 및 최적화"""
        
        # 크기가 충분한 클러스터와 작은 클러스터 분리
        large_clusters = []
        small_clusters = []
        
        for cluster in clusters:
            if len(cluster['items']) >= self.MIN_CLUSTER_SIZE:
                large_clusters.append(cluster)
            elif cluster['items']:  # 비어있지 않은 작은 클러스터
                small_clusters.append(cluster)
        
        # 작은 클러스터들을 병합하거나 가장 유사한 큰 클러스터에 병합
        if small_clusters:
            # 모든 작은 클러스터의 아이템을 모음
            orphan_items = []
            for cluster in small_clusters:
                orphan_items.extend(cluster['items'])
            
            if orphan_items:
                # "기타" 클러스터 생성
                misc_cluster = {
                    'topic': {
                        'name': '기타 관련 내용',
                        'description': '다양한 관련 주제들',
                        'keywords': []
                    },
                    'items': orphan_items,
                    'average_relevance': sum(item.get('relevance_score', 0) for item in orphan_items) / len(orphan_items),
                    'key_insights': []
                }
                
                # 핵심 인사이트 추출
                top_items = sorted(orphan_items, key=lambda x: x.get('score', 0), reverse=True)[:3]
                misc_cluster['key_insights'] = [
                    {
                        'title': item.get('title', '제목 없음'),
                        'score': item.get('score', 0),
                        'type': item.get('type', 'unknown')
                    }
                    for item in top_items
                ]
                
                large_clusters.append(misc_cluster)
        
        # 클러스터를 크기 순으로 정렬
        final_clusters = sorted(large_clusters, key=lambda x: len(x['items']), reverse=True)
        
        return final_clusters
    
    def _generate_cluster_statistics(
        self, 
        clusters: List[Dict[str, Any]], 
        all_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """클러스터링 결과 통계 생성"""
        
        total_clustered = sum(len(cluster['items']) for cluster in clusters)
        total_items = len(all_items)
        
        cluster_sizes = [len(cluster['items']) for cluster in clusters]
        
        statistics = {
            'total_items': total_items,
            'total_clustered': total_clustered,
            'total_unclustered': total_items - total_clustered,
            'num_clusters': len(clusters),
            'average_cluster_size': total_clustered / len(clusters) if clusters else 0,
            'largest_cluster_size': max(cluster_sizes) if cluster_sizes else 0,
            'smallest_cluster_size': min(cluster_sizes) if cluster_sizes else 0,
            'cluster_distribution': {}
        }
        
        # 각 클러스터의 분포
        for cluster in clusters:
            topic_name = cluster['topic']['name']
            statistics['cluster_distribution'][topic_name] = {
                'count': len(cluster['items']),
                'percentage': (len(cluster['items']) / total_items * 100) if total_items > 0 else 0,
                'average_relevance': cluster['average_relevance']
            }
        
        return statistics
    
    def _is_item_clustered(self, item: Dict[str, Any], clusters: List[Dict[str, Any]]) -> bool:
        """아이템이 클러스터에 포함되었는지 확인"""
        item_id = item.get('id')
        for cluster in clusters:
            for cluster_item in cluster['items']:
                if cluster_item.get('id') == item_id:
                    return True
        return False
    
    def _parse_topics_response(self, response: str) -> List[Dict[str, str]]:
        """LLM 응답에서 주제 목록 파싱"""
        try:
            # JSON 블록 추출
            response_clean = response.strip()
            if '```json' in response_clean:
                response_clean = response_clean.split('```json')[1].split('```')[0].strip()
            elif '```' in response_clean:
                response_clean = response_clean.split('```')[1].strip()
            
            topics = json.loads(response_clean)
            
            if not isinstance(topics, list):
                raise ValueError("응답이 리스트 형태가 아님")
            
            # 각 주제 검증
            validated_topics = []
            for topic in topics:
                if isinstance(topic, dict) and 'name' in topic and 'description' in topic:
                    validated_topics.append({
                        'name': topic['name'],
                        'description': topic['description'],
                        'keywords': topic.get('keywords', [])
                    })
            
            return validated_topics
            
        except Exception as e:
            logger.warning(f"⚠️ 주제 파싱 실패: {str(e)}")
            return []
    
    def _parse_assignments_response(self, response: str, expected_length: int) -> List[int]:
        """LLM 응답에서 주제 할당 결과 파싱"""
        try:
            # JSON 배열 추출
            response_clean = response.strip()
            if '[' in response_clean:
                start_idx = response_clean.find('[')
                end_idx = response_clean.rfind(']') + 1
                response_clean = response_clean[start_idx:end_idx]
            
            assignments = json.loads(response_clean)
            
            if not isinstance(assignments, list):
                raise ValueError("응답이 리스트 형태가 아님")
            
            # 길이 맞추기
            if len(assignments) < expected_length:
                # 부족한 부분은 0(첫 번째 주제)으로 채우기
                assignments.extend([0] * (expected_length - len(assignments)))
            elif len(assignments) > expected_length:
                # 초과 부분 제거
                assignments = assignments[:expected_length]
            
            # 유효성 검증 (음수가 아닌 정수)
            validated = []
            for val in assignments:
                if isinstance(val, int) and val >= -1:
                    validated.append(val)
                else:
                    validated.append(0)  # 잘못된 값은 첫 번째 주제로
            
            return validated
            
        except Exception as e:
            logger.warning(f"⚠️ 할당 결과 파싱 실패: {str(e)}")
            # 폴백: 모두 첫 번째 주제에 할당
            return [0] * expected_length
    
    def get_cluster_summary(self, clusters: List[Dict[str, Any]]) -> str:
        """클러스터링 결과를 읽기 쉬운 요약으로 변환"""
        
        if not clusters:
            return "클러스터링된 주제가 없습니다."
        
        summary_lines = ["📊 주제별 분류 결과:\n"]
        
        for idx, cluster in enumerate(clusters, 1):
            topic = cluster['topic']
            item_count = len(cluster['items'])
            avg_relevance = cluster['average_relevance']
            
            summary_lines.append(f"{idx}. {topic['name']} ({item_count}개 콘텐츠)")
            summary_lines.append(f"   - {topic['description']}")
            summary_lines.append(f"   - 평균 관련성: {avg_relevance:.1f}/10")
            
            if cluster['key_insights']:
                summary_lines.append("   - 주요 내용:")
                for insight in cluster['key_insights'][:2]:
                    summary_lines.append(f"     • {insight['title'][:50]}...")
            
            summary_lines.append("")
        
        return "\n".join(summary_lines)