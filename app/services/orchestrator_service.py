from typing import List, Dict, Any, Optional, Tuple
from app.services.llm_service import LLMService
from app.services.reddit_service import RedditService
from app.services.relevance_filtering_service import RelevanceFilteringService
from app.services.topic_clustering_service import TopicClusteringService
import logging
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.schemas.search import SearchRequest, ReportLength

logger = logging.getLogger(__name__)

class OrchestratorService:
    """
    전체 분석 프로세스를 관리하는 오케스트레이터 서비스
    - 각 단계의 품질 검증
    - 섹션별 중복 제거
    - 일관된 품질 보장
    """
    
    def __init__(self, thread_pool: Optional[ThreadPoolExecutor] = None, api_semaphore: Optional[asyncio.Semaphore] = None):
        self.llm_service = LLMService(api_semaphore=api_semaphore)
        self.reddit_service = RedditService(thread_pool=thread_pool)
        self.relevance_service = RelevanceFilteringService(thread_pool=thread_pool, api_semaphore=api_semaphore)
        self.clustering_service = TopicClusteringService(thread_pool=thread_pool, api_semaphore=api_semaphore)
        self.thread_pool = thread_pool
        self.api_semaphore = api_semaphore
    
    async def orchestrate_analysis(
        self, 
        request: SearchRequest,
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        전체 분석 프로세스를 오케스트레이션
        """
        try:
            logger.info(f"🎼 오케스트레이션 시작 - 키워드: '{request.query}'")
            
            # 1단계: 키워드 확장
            if progress_callback:
                await progress_callback("키워드 분석 중", 10)
            
            expanded_keywords = await self.llm_service.expand_keywords(request.query)
            logger.info(f"✅ 키워드 확장 완료: {len(expanded_keywords)}개")
            
            # 2단계: 데이터 수집 (게시물 + 댓글)
            if progress_callback:
                await progress_callback("데이터 수집 중", 20)
            
            collection_result = await self._collect_data_with_quality_check(
                expanded_keywords, 
                progress_callback,
                request
            )
            
            # 3단계: 관련성 필터링
            if progress_callback:
                await progress_callback("관련성 분석 중", 40)
            
            filtered_content = await self._filter_with_quality_check(
                collection_result['content'],
                request.query,
                expanded_keywords
            )
            
            # 4단계: 주제별 클러스터링
            if progress_callback:
                await progress_callback("주제 분류 중", 55)
            
            clustering_result = await self._cluster_with_quality_check(
                filtered_content,
                request.query
            )
            
            # 5단계: 통합 보고서 생성
            if progress_callback:
                await progress_callback("보고서 작성 중", 70)
            
            report = await self._generate_quality_report(
                clustering_result,
                request.query,
                request.length,
                expanded_keywords
            )
            
            # 6단계: 품질 검증 및 개선
            if progress_callback:
                await progress_callback("품질 검증 중", 85)
            
            final_report = await self._quality_assurance(
                report, 
                clustering_result=clustering_result,
                query=request.query,
                keywords=expanded_keywords
            )
            
            if progress_callback:
                await progress_callback("분석 완료", 100)
            
            logger.info("🎉 오케스트레이션 완료!")
            
            return {
                'report': final_report,
                'metadata': {
                    'expanded_keywords': expanded_keywords,
                    'total_collected': collection_result['total'],
                    'filtered_count': len(filtered_content),
                    'cluster_count': len(clustering_result['clusters']),
                    'quality_score': final_report.get('quality_score', 0),
                    'keyword_stats': collection_result.get('keyword_stats', {})  # 키워드별 통계 추가
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 오케스트레이션 실패: {str(e)}")
            raise
    
    async def _collect_data_with_quality_check(
        self, 
        keywords: List[str], 
        progress_callback: Optional[Any] = None,
        request: Optional[SearchRequest] = None
    ) -> Dict[str, Any]:
        """데이터 수집 및 품질 체크"""
        all_content = []
        keyword_stats = {}  # 키워드별 통계 정보
        
        # 키워드별로 수집
        for idx, keyword in enumerate(keywords[:10]):  # 최대 10개 키워드
            if progress_callback:
                progress = 20 + (idx / len(keywords[:10])) * 15
                await progress_callback(f"'{keyword}' 수집 중", int(progress))
            
            # collect_posts_with_comments는 리스트를 반환함
            # time_filter 받아서 전달
            time_filter = 'all'
            if request and request.time_filter:
                # TimeFilter enum을 Reddit API 형식으로 변환
                time_filter_map = {
                    '1h': 'hour',
                    '3h': 'hour',
                    '6h': 'day',
                    '12h': 'day',
                    '1d': 'day',
                    '3d': 'week',
                    '1w': 'week',
                    '1m': 'month'
                }
                time_filter = time_filter_map.get(request.time_filter.value, 'all')
            
            content_items = await self.reddit_service.collect_posts_with_comments(
                keywords=[keyword],  # keywords 파라미터로 변경
                posts_limit=15,  # posts_limit 파라미터명으로 변경
                time_filter=time_filter
            )
            
            # 키워드별 통계 정보 수집
            keyword_posts = [item for item in content_items if item['type'] == 'post']
            keyword_stats[keyword] = {
                'posts_found': len(keyword_posts),
                'sample_titles': [post['title'] for post in keyword_posts[:3]]  # 상위 3개 제목
            }
            
            # 수집된 콘텐츠에 메타데이터 추가
            for item in content_items:
                item['keyword_source'] = keyword
                all_content.append(item)
        
        # 중복 제거
        unique_content = self._remove_duplicates(all_content)
        
        logger.info(f"📊 수집 결과: 전체 {len(all_content)}개 → 중복 제거 후 {len(unique_content)}개")
        
        return {
            'content': unique_content,
            'total': len(all_content),
            'unique': len(unique_content),
            'keyword_stats': keyword_stats  # 키워드별 통계 추가
        }
    
    async def _filter_with_quality_check(
        self,
        content: List[Dict[str, Any]],
        query: str,
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """관련성 필터링 및 품질 검증"""
        # 관련성 필터링
        filtered = await self.relevance_service.filter_relevant_content(
            content_items=content,
            query=query,
            expanded_keywords=keywords
        )
        
        # 품질 기준 확인
        high_quality = [item for item in filtered if item.get('relevance_score', 0) >= 7.5]
        medium_quality = [item for item in filtered if 6 <= item.get('relevance_score', 0) < 7.5]
        
        logger.info(f"🎯 품질 분포: 고품질 {len(high_quality)}개, 중품질 {len(medium_quality)}개")
        
        # 최소 품질 기준 보장
        if len(high_quality) < 5:
            logger.warning("⚠️ 고품질 콘텐츠 부족, 중품질 콘텐츠 포함")
            filtered = high_quality + medium_quality[:10-len(high_quality)]
        else:
            filtered = high_quality
        
        return filtered
    
    async def _cluster_with_quality_check(
        self,
        content: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """주제 클러스터링 및 품질 검증"""
        # 클러스터링 수행
        clustering_result = await self.clustering_service.cluster_content(
            content_items=content,
            query=query
        )
        
        # 클러스터 품질 검증
        quality_clusters = []
        for cluster in clustering_result['clusters']:
            # 너무 작은 클러스터는 제외
            if len(cluster['items']) >= 2:
                quality_clusters.append(cluster)
            else:
                logger.info(f"🔍 작은 클러스터 제외: {cluster['topic']['name']} ({len(cluster['items'])}개)")
        
        # 클러스터 재정렬 (크기순)
        quality_clusters.sort(key=lambda x: len(x['items']), reverse=True)
        
        return {
            'clusters': quality_clusters,
            'statistics': clustering_result['statistics']
        }
    
    async def _generate_quality_report(
        self,
        clustering_result: Dict[str, Any],
        query: str,
        length: ReportLength,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """통합 품질 보고서 생성 - 각주 시스템 포함"""
        
        # 모든 컨텐츠 수집 (게시물 + 댓글)
        all_content = []
        for cluster in clustering_result['clusters']:
            for item in cluster['items']:
                all_content.append(item)
        
        # 중복 제거 및 정렬
        unique_content = {item.get('id'): item for item in all_content if item.get('id')}.values()
        sorted_content = sorted(unique_content, key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # LLM 서비스를 통한 보고서 생성 (각주 포함)
        try:
            report_result = await self.llm_service.generate_report(
                posts=list(sorted_content),
                query=query,
                length=length,
                cluster_info=clustering_result
            )
            
            # 보고서 파싱
            report_sections = self._parse_report_sections(report_result['full_report'])
            
            return {
                'full_report': report_result['full_report'],
                'sections': report_sections,
                'quality_score': await self._calculate_quality_score(report_sections),
                'footnote_mapping': report_result.get('footnote_mapping', [])
            }
            
        except Exception as e:
            logger.error(f"보고서 생성 실패: {str(e)}")
            raise
    
    async def _quality_assurance(self, report: Dict[str, Any], 
                               clustering_result: Dict[str, Any] = None,
                               query: str = None,
                               keywords: List[str] = None) -> Dict[str, Any]:
        """최종 품질 보증 및 개선"""
        
        # 1. 중복 내용 제거
        cleaned_sections = await self._remove_section_duplicates(report['sections'])
        
        # 2. 일관성 검증
        consistency_score = await self._check_consistency(cleaned_sections)
        
        # 3. 필수 요소 확인
        completeness = self._check_completeness(cleaned_sections)
        
        # 4. 개선이 필요한 경우 재생성
        if consistency_score < 0.7 or not completeness['is_complete']:
            logger.info("📝 품질 개선을 위한 보고서 재생성")
            improved_report = await self._improve_report(
                report, 
                completeness['missing'],
                clustering_result=clustering_result,
                query=query,
                keywords=keywords
            )
            # 개선된 보고서에서 summary와 full_report 확인
            return {
                'summary': improved_report.get('summary', self._extract_summary(improved_report.get('full_report', ''))),
                'full_report': improved_report.get('full_report', ''),
                'quality_metrics': {
                    'consistency_score': consistency_score,
                    'completeness': completeness,
                    'quality_score': improved_report.get('quality_score', 0)
                },
                'footnote_mapping': report.get('footnote_mapping', [])
            }
        
        # 5. 최종 포맷팅
        final_report = self._format_final_report(cleaned_sections)
        
        return {
            'summary': self._extract_summary(final_report),
            'full_report': final_report,
            'quality_metrics': {
                'consistency_score': consistency_score,
                'completeness': completeness,
                'quality_score': report.get('quality_score', 0)
            },
            'footnote_mapping': report.get('footnote_mapping', [])
        }
    
    async def _create_structured_prompt(
        self,
        clustering_result: Dict[str, Any],
        query: str,
        length: ReportLength,
        keywords: List[str]
    ) -> str:
        """구조화된 프롬프트 생성"""
        
        clusters = clustering_result['clusters']
        
        # 클러스터 정보 정리
        cluster_summaries = []
        for idx, cluster in enumerate(clusters, 1):
            topic = cluster['topic']
            items = cluster['items']
            
            # 각 클러스터의 핵심 콘텐츠 추출
            top_items = sorted(items, key=lambda x: x.get('relevance_score', 0), reverse=True)[:3]
            
            cluster_summary = f"""
주제 {idx}: {topic['name']}
설명: {topic['description']}
관련 콘텐츠 수: {len(items)}개
핵심 내용:
"""
            for item in top_items:
                if item['type'] == 'post':
                    cluster_summary += f"- {item['title'][:80]}... (점수: {item.get('score', 0)})\n"
                else:
                    cluster_summary += f"- 댓글: {item.get('content', '')[:80]}... (추천: {item.get('score', 0)})\n"
            
            cluster_summaries.append(cluster_summary)
        
        # 길이별 가이드
        length_guides = {
            ReportLength.simple: "각 섹션 1-2 단락, 전체 500-700자",
            ReportLength.moderate: "각 섹션 2-3 단락, 전체 1000-1500자",
            ReportLength.detailed: "각 섹션 3-5 단락, 전체 2000-3000자"
        }
        
        prompt = f"""당신은 전문 커뮤니티 분석가입니다. '{query}' 키워드로 수집된 데이터를 분석하여 고품질 보고서를 작성해주세요.

검색 키워드: {', '.join(keywords[:5])}
수집된 고품질 콘텐츠: {sum(len(c['items']) for c in clusters)}개

주제별 분류 결과:
{''.join(cluster_summaries)}

다음 구조로 {length_guides[length]} 분량의 한국어 보고서를 작성해주세요:

## 1. 핵심 요약
- 전체 여론과 트렌드를 2-3문장으로 요약
- 가장 중요한 발견사항 1-2가지 강조

## 2. 주요 주제 분석
- 위에서 분류된 각 주제별로 섹션 구성
- 각 주제의 핵심 논점과 여론 정리
- 각 주제마다 최소 2-3개의 원문 인용 필수
- 인용 형식: "원문 내용" (작성자: username, 추천: N)

## 3. 감성 분석
- 전반적인 감성 분포 (긍정/부정/중립)
- 주제별 감성 차이 분석
- 특히 부정적 의견의 주요 원인

## 4. 주목할 만한 인사이트
- 예상치 못한 발견사항
- 소수의견이지만 중요한 관점
- 향후 주목해야 할 신호

## 5. 결론 및 시사점
- 전체 분석 결과 종합
- 실행 가능한 인사이트 제시

중요 지침:
1. 각 섹션 간 중복을 피하고 유기적으로 연결
2. 구체적인 수치와 사례로 주장 뒷받침
3. 객관적이고 균형잡힌 시각 유지
4. 전문적이면서도 이해하기 쉬운 문체 사용"""
        
        return prompt
    
    def _remove_duplicates(self, content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """중복 콘텐츠 제거"""
        seen_ids = set()
        unique_content = []
        
        for item in content:
            item_id = item.get('id')
            if item_id and item_id not in seen_ids:
                seen_ids.add(item_id)
                unique_content.append(item)
        
        return unique_content
    
    def _parse_report_sections(self, report_text: str) -> Dict[str, str]:
        """보고서를 섹션별로 파싱"""
        sections = {
            'summary': '',
            'topic_analysis': '',
            'sentiment_analysis': '',
            'insights': '',
            'conclusion': ''
        }
        
        # 섹션 매핑
        section_markers = {
            '## 1. 핵심 요약': 'summary',
            '## 2. 주요 주제 분석': 'topic_analysis',
            '## 3. 감성 분석': 'sentiment_analysis',
            '## 4. 주목할 만한 인사이트': 'insights',
            '## 5. 결론 및 시사점': 'conclusion'
        }
        
        current_section = None
        lines = report_text.split('\n')
        
        for line in lines:
            # 섹션 시작 확인
            for marker, section_name in section_markers.items():
                if line.strip().startswith(marker):
                    current_section = section_name
                    break
            else:
                # 현재 섹션에 내용 추가
                if current_section:
                    sections[current_section] += line + '\n'
        
        return sections
    
    async def _calculate_quality_score(self, sections: Dict[str, str]) -> float:
        """보고서 품질 점수 계산"""
        score = 0.0
        
        # 각 섹션 존재 여부 (50%)
        for section, content in sections.items():
            if content.strip():
                score += 0.1
        
        # 섹션별 최소 길이 충족 (30%)
        min_lengths = {
            'summary': 100,
            'topic_analysis': 300,
            'sentiment_analysis': 200,
            'insights': 150,
            'conclusion': 150
        }
        
        for section, min_length in min_lengths.items():
            if len(sections.get(section, '')) >= min_length:
                score += 0.06
        
        # 구체적 수치/인용 포함 여부 (20%)
        all_content = ' '.join(sections.values())
        if any(char.isdigit() for char in all_content):
            score += 0.1
        if '"' in all_content or '「' in all_content:
            score += 0.1
        
        return min(score, 1.0)
    
    async def _remove_section_duplicates(self, sections: Dict[str, str]) -> Dict[str, str]:
        """섹션 간 중복 내용 제거"""
        cleaned_sections = {}
        used_sentences = set()
        
        for section_name, content in sections.items():
            sentences = content.split('.')
            cleaned_sentences = []
            
            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and sentence not in used_sentences:
                    used_sentences.add(sentence)
                    cleaned_sentences.append(sentence)
            
            cleaned_sections[section_name] = '. '.join(cleaned_sentences) + '.'
        
        return cleaned_sections
    
    async def _check_consistency(self, sections: Dict[str, str]) -> float:
        """섹션 간 일관성 검증"""
        # 간단한 일관성 체크 (실제로는 더 복잡한 로직 필요)
        consistency_score = 1.0
        
        # 요약과 결론의 일치도 확인
        summary = sections.get('summary', '').lower()
        conclusion = sections.get('conclusion', '').lower()
        
        # 공통 키워드 확인
        summary_words = set(summary.split())
        conclusion_words = set(conclusion.split())
        
        if summary_words and conclusion_words:
            overlap = len(summary_words & conclusion_words)
            consistency_score = min(overlap / min(len(summary_words), len(conclusion_words)) * 2, 1.0)
        
        return consistency_score
    
    def _check_completeness(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """보고서 완성도 확인"""
        required_sections = ['summary', 'topic_analysis', 'sentiment_analysis', 'insights', 'conclusion']
        missing_sections = []
        
        for section in required_sections:
            if not sections.get(section, '').strip():
                missing_sections.append(section)
        
        return {
            'is_complete': len(missing_sections) == 0,
            'missing': missing_sections,
            'completeness_ratio': (len(required_sections) - len(missing_sections)) / len(required_sections)
        }
    
    async def _improve_report(self, report: Dict[str, Any], missing_sections: List[str], 
                           clustering_result: Dict[str, Any] = None, query: str = None, 
                           keywords: List[str] = None) -> Dict[str, Any]:
        """보고서 개선 - 원본 데이터를 활용한 종합적 개선"""
        
        # 기존 섹션들의 내용 보존 (임시 비활성화 - 빈 내용 문제 해결)
        existing_sections = []
        # TODO: 추후 기존 내용이 실제로 있을 때만 보존하도록 개선
        # for section, content in report.get('sections', {}).items():
        #     if content and content.strip() and section not in missing_sections:
        #         existing_sections.append(f"### {section}\n{content}")
        
        # 클러스터 정보 재구성
        cluster_info = ""
        if clustering_result and 'clusters' in clustering_result:
            for idx, cluster in enumerate(clustering_result['clusters'], 1):
                cluster_info += f"\n클러스터 {idx} - {cluster['topic']['name']}:\n"
                cluster_info += f"  설명: {cluster['topic']['description']}\n"
                cluster_info += f"  콘텐츠 수: {len(cluster['items'])}개\n"
                
                # 상위 콘텐츠 예시
                top_items = sorted(cluster['items'], 
                                 key=lambda x: x.get('relevance_score', 0), 
                                 reverse=True)[:2]
                for item in top_items:
                    if item['type'] == 'post':
                        cluster_info += f"  - {item['title'][:60]}...\n"
                    else:
                        cluster_info += f"  - 댓글: {item.get('content', '')[:60]}...\n"
        
        improvement_prompt = f"""당신은 10년 경력의 전문 커뮤니티 분석가입니다. 
여러 분석가들이 작성한 개별 분석들을 종합하여, 전체적인 관점에서만 볼 수 있는 통찰과 함께 
포괄적이고 심층적인 최종 보고서를 작성해주세요.

분석 주제: {query or ''}
관련 키워드: {', '.join(keywords[:5]) if keywords else ''}

=== 원본 데이터 정보 ===
{cluster_info}

=== 기존에 작성된 개별 분석 내용들 (모두 포함하여 확장) ===
{chr(10).join(existing_sections)}

=== 보완이 필요한 섹션: {', '.join(missing_sections)} ===

다음 지침에 따라 종합 보고서를 작성해주세요:

1. **기존 분석 확장 및 심화**
   - 개별 분석가들이 작성한 내용을 모두 포함하되, 더 깊이 있게 확장
   - 각 주제별로 3-5개의 구체적인 원문을 반드시 인용
   - 인용 형식: "원문 내용" (출처: 작성자명, 추천수)
   
2. **종합적 시각에서의 새로운 통찰**
   - 개별 분석에서는 보이지 않았던 전체적인 패턴과 트렌드 파악
   - 서로 다른 주제/클러스터 간의 연관성과 상호작용 분석
   - 표면적으로 드러나지 않은 숨은 의미와 함의 도출
   
3. **구체적인 증거와 사례**
   - 모든 주장은 실제 게시물/댓글의 원문 인용으로 뒷받침
   - 통계적 수치와 비율을 구체적으로 제시
   - "많은 사람들이"가 아닌 "전체 응답자의 65%가" 같은 정확한 표현
   
4. **상세하고 풍부한 내용**
   - 각 섹션을 최소 3-4개 단락으로 구성
   - 핵심 요약은 500자 이상
   - 주요 주제 분석은 각 주제당 300-500자
   - 전체 보고서는 3000-5000자 수준
   
5. **다층적 분석**
   - 표면적 의견 → 근본 원인 → 잠재적 영향 순으로 분석
   - 단기적 반응과 장기적 함의를 구분하여 제시
   - 주류 의견과 소수 의견의 가치를 모두 평가

최종 보고서 구조:

## 1. 종합 요약 및 핵심 발견사항
- 전체 데이터를 관통하는 핵심 메시지 3-5개
- 가장 중요한 발견사항과 그 의미
- 예상치 못한 통찰이나 역설적 발견

## 2. 주제별 심층 분석
- 각 주제마다 배경, 현황, 구체적 사례(원문 인용 필수), 의미 분석
- 주제 간 연결고리와 상호 영향 관계
- 각 주제별로 대표적인 원문 3-5개 인용

## 3. 정서 및 여론 동향 분석
- 정량적 감성 분포와 정성적 감정 분석
- 감정 변화의 원인과 맥락
- 특정 이슈에 대한 감정적 반응의 원문 예시

## 4. 숨은 패턴과 통찰
- 개별 분석에서 놓친 전체적 패턴
- 약한 신호(weak signal)이지만 중요한 징후
- 커뮤니티의 집단 무의식이나 암묵적 합의

## 5. 전략적 함의와 제언
- 분석 결과가 시사하는 바
- 향후 예상되는 전개 방향
- 구체적이고 실행 가능한 제언

모든 섹션에서 구체적인 원문을 인용하고, 
단순 나열이 아닌 서사적 흐름으로 작성해주세요."""
        
        try:
            improved_response = await self.llm_service._call_llm(improvement_prompt, temperature=0.5)
            improved_sections = self._parse_report_sections(improved_response)
            
            # 기존 섹션과 병합
            for section, content in improved_sections.items():
                if section in missing_sections and content.strip():
                    report['sections'][section] = content
            
            report['full_report'] = self._format_final_report(report['sections'])
            
        except Exception as e:
            logger.error(f"보고서 개선 실패: {str(e)}")
        
        # summary와 quality_metrics가 있는지 확인하고 없으면 추가
        if 'summary' not in report:
            report['summary'] = self._extract_summary(report['full_report'])
        if 'quality_score' not in report:
            report['quality_score'] = await self._calculate_quality_score(report['sections'])
        
        return report
    
    def _format_final_report(self, sections: Dict[str, str]) -> str:
        """최종 보고서 포맷팅"""
        formatted_parts = []
        
        section_titles = {
            'summary': '## 1. 핵심 요약',
            'topic_analysis': '## 2. 주요 주제 분석',
            'sentiment_analysis': '## 3. 감성 분석',
            'insights': '## 4. 주목할 만한 인사이트',
            'conclusion': '## 5. 결론 및 시사점'
        }
        
        for section_key, title in section_titles.items():
            content = sections.get(section_key, '').strip()
            if content:
                formatted_parts.append(f"{title}\n\n{content}")
        
        return '\n\n'.join(formatted_parts)
    
    def _extract_summary(self, report: str) -> str:
        """보고서에서 요약 추출"""
        lines = report.split('\n')
        summary_lines = []
        in_summary = False
        
        for line in lines:
            if '## 1. 핵심 요약' in line:
                in_summary = True
                continue
            elif line.startswith('## 2.'):
                break
            elif in_summary and line.strip():
                summary_lines.append(line.strip())
        
        return ' '.join(summary_lines[:3])  # 최대 3줄