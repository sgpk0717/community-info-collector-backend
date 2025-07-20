import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from app.services.multi_agent_service import MultiAgentService
from app.services.footnote_service import FootnoteService
from app.services.llm_service import LLMService
from app.core.dependencies import get_supabase_client

logger = logging.getLogger(__name__)

class SynthesisService:
    """
    종합 분석 서비스
    
    모든 분석 컴포넌트를 통합하여 최종 보고서 생성:
    1. Multi-Agent 분석 실행
    2. 각주 시스템 적용
    3. 최종 보고서 종합 및 품질 검증
    4. 메타데이터 관리
    """
    
    def __init__(self):
        logger.info("🎨 SynthesisService 초기화")
        
        self.multi_agent_service = MultiAgentService()
        self.footnote_service = FootnoteService()
        self.llm_service = LLMService()
        self.client = get_supabase_client()
        
        logger.info("✅ 종합 분석 서비스 초기화 완료")
    
    async def generate_comprehensive_report(self, session_id: str, query: str, 
                                          posts_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """포괄적인 보고서 생성"""
        logger.info(f"🎯 종합 보고서 생성 시작 - Session: {session_id}, Query: {query}")
        
        start_time = datetime.now()
        
        try:
            # 1. 기본 데이터 수집 (posts_data가 없으면 DB에서 조회)
            if not posts_data:
                posts_data = await self._fetch_posts_data(session_id)
            
            logger.info(f"📊 분석 대상 게시물: {len(posts_data)}개")
            
            # 2. Multi-Agent 분석 실행
            logger.info("🤖 Multi-Agent 분석 실행 중...")
            agent_results = await self.multi_agent_service.analyze_with_agents(session_id, query)
            
            # 3. 각주 시스템 적용
            logger.info("📎 각주 시스템 적용 중...")
            footnote_results = await self.footnote_service.process_report_with_footnotes(
                session_id, 
                agent_results['final_report'], 
                posts_data
            )
            
            # 4. 최종 보고서 품질 검증 및 보완
            logger.info("🔍 보고서 품질 검증 중...")
            quality_check = await self._validate_report_quality(
                footnote_results['processed_report'],
                agent_results,
                footnote_results
            )
            
            # 5. 메타데이터 생성
            metadata = self._generate_report_metadata(
                session_id, query, posts_data, agent_results, footnote_results, quality_check
            )
            
            # 6. 최종 결과 구성
            execution_time = (datetime.now() - start_time).total_seconds()
            
            final_result = {
                'session_id': session_id,
                'query': query,
                'execution_time': execution_time,
                'final_report': footnote_results['processed_report'],
                'agent_analysis': agent_results,
                'footnote_system': footnote_results,
                'quality_metrics': quality_check,
                'metadata': metadata,
                'timestamp': datetime.now().isoformat()
            }
            
            # 7. 결과 저장
            await self._save_comprehensive_results(session_id, final_result)
            
            logger.info(f"🎉 종합 보고서 생성 완료! 소요시간: {execution_time:.2f}초")
            
            return final_result
            
        except Exception as e:
            logger.error(f"❌ 종합 보고서 생성 실패: {str(e)}")
            raise
    
    async def _fetch_posts_data(self, session_id: str) -> List[Dict[str, Any]]:
        """세션 ID로 게시물 데이터 조회"""
        logger.info("📥 게시물 데이터 조회 중...")
        
        try:
            result = self.client.table('source_contents')\
                .select('*')\
                .eq('metadata->>session_id', session_id)\
                .execute()
            
            if result.data:
                # source_contents 형태를 posts 형태로 변환
                posts_data = []
                for item in result.data:
                    post = {
                        'id': item['source_id'],
                        'title': item['raw_text'][:100] + '...' if len(item['raw_text']) > 100 else item['raw_text'],
                        'selftext': item['raw_text'],
                        'url': item['source_url'],
                        'score': item.get('score', 0),
                        'num_comments': item.get('comments', 0),
                        'created_utc': item.get('created_at', ''),
                        'subreddit': item.get('metadata', {}).get('subreddit', 'community'),
                        'author': item.get('metadata', {}).get('author', 'anonymous')
                    }
                    posts_data.append(post)
                
                logger.info(f"✅ {len(posts_data)}개 게시물 조회 완료")
                return posts_data
            
            logger.warning("⚠️ 게시물 데이터가 없습니다")
            return []
            
        except Exception as e:
            logger.error(f"게시물 데이터 조회 실패: {str(e)}")
            return []
    
    async def _validate_report_quality(self, report: str, agent_results: Dict[str, Any], 
                                     footnote_results: Dict[str, Any]) -> Dict[str, Any]:
        """보고서 품질 검증"""
        logger.info("🔍 보고서 품질 검증 수행 중...")
        
        quality_metrics = {
            'report_length': len(report),
            'footnote_count': footnote_results['footnote_count'],
            'topics_covered': len(agent_results.get('detailed_results', {}).get('topics', [])),
            'agent_confidence': self._calculate_average_confidence(agent_results),
            'completeness_score': 0.0,
            'issues': []
        }
        
        # 1. 보고서 길이 검증
        if quality_metrics['report_length'] < 500:
            quality_metrics['issues'].append("보고서가 너무 짧습니다")
        elif quality_metrics['report_length'] > 10000:
            quality_metrics['issues'].append("보고서가 너무 깁니다")
        
        # 2. 각주 비율 검증
        footnote_ratio = quality_metrics['footnote_count'] / max(quality_metrics['report_length'] / 1000, 1)
        if footnote_ratio < 0.5:
            quality_metrics['issues'].append("각주가 부족합니다")
        
        # 3. 구조적 완성도 검증
        required_sections = ['요약', '분석', '결론']
        missing_sections = [section for section in required_sections if section not in report]
        if missing_sections:
            quality_metrics['issues'].append(f"필수 섹션 누락: {', '.join(missing_sections)}")
        
        # 4. 전체 완성도 점수 계산
        completeness_factors = [
            quality_metrics['report_length'] > 500,  # 적절한 길이
            quality_metrics['footnote_count'] > 0,   # 각주 존재
            quality_metrics['topics_covered'] > 0,   # 주제 분석
            len(quality_metrics['issues']) == 0      # 이슈 없음
        ]
        
        quality_metrics['completeness_score'] = sum(completeness_factors) / len(completeness_factors)
        
        # 5. 품질 보완 권장사항
        if quality_metrics['completeness_score'] < 0.8:
            logger.warning(f"⚠️ 보고서 품질 점수 낮음: {quality_metrics['completeness_score']:.2f}")
            quality_metrics['recommendations'] = await self._generate_quality_recommendations(quality_metrics)
        
        logger.info(f"✅ 품질 검증 완료 - 점수: {quality_metrics['completeness_score']:.2f}")
        
        return quality_metrics
    
    def _calculate_average_confidence(self, agent_results: Dict[str, Any]) -> float:
        """에이전트들의 평균 신뢰도 계산"""
        detailed_results = agent_results.get('detailed_results', {})
        
        confidences = []
        for key, value in detailed_results.items():
            if isinstance(value, dict) and hasattr(value, 'confidence_score'):
                confidences.append(value.confidence_score)
        
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    async def _generate_quality_recommendations(self, quality_metrics: Dict[str, Any]) -> List[str]:
        """품질 개선 권장사항 생성"""
        recommendations = []
        
        if quality_metrics['report_length'] < 500:
            recommendations.append("보고서 내용을 더 상세히 작성하세요")
        
        if quality_metrics['footnote_count'] == 0:
            recommendations.append("중요한 주장에 대한 근거 자료 각주를 추가하세요")
        
        if quality_metrics['topics_covered'] < 3:
            recommendations.append("더 다양한 관점에서 주제를 분석하세요")
        
        if quality_metrics['issues']:
            recommendations.append("식별된 이슈들을 해결하세요")
        
        return recommendations
    
    def _generate_report_metadata(self, session_id: str, query: str, posts_data: List[Dict[str, Any]], 
                                agent_results: Dict[str, Any], footnote_results: Dict[str, Any], 
                                quality_check: Dict[str, Any]) -> Dict[str, Any]:
        """보고서 메타데이터 생성"""
        return {
            'session_id': session_id,
            'query': query,
            'analysis_timestamp': datetime.now().isoformat(),
            'data_sources': {
                'posts_count': len(posts_data),
                'topics_identified': len(agent_results.get('detailed_results', {}).get('topics', [])),
                'footnotes_added': footnote_results['footnote_count']
            },
            'processing_stats': {
                'agent_execution_time': agent_results.get('execution_time', 0),
                'topics_count': agent_results.get('topics_count', 0),
                'quality_score': quality_check['completeness_score']
            },
            'version': '2.0',
            'methodology': 'Multi-Agent Analysis with Footnote System'
        }
    
    async def _save_comprehensive_results(self, session_id: str, results: Dict[str, Any]):
        """종합 결과를 데이터베이스에 저장"""
        logger.info("💾 종합 결과 저장 중...")
        
        try:
            # analysis_sections 테이블에 종합 결과 저장
            comprehensive_data = {
                'session_id': session_id,
                'analysis_type': 'comprehensive_report',
                'analysis_data': {
                    'final_report': results['final_report'],
                    'metadata': results['metadata'],
                    'quality_metrics': results['quality_metrics'],
                    'execution_time': results['execution_time'],
                    'timestamp': results['timestamp']
                }
            }
            
            result = self.client.table('analysis_sections').insert(comprehensive_data).execute()
            
            if result.data:
                logger.info("✅ 종합 결과 저장 완료")
            else:
                logger.warning("⚠️ 종합 결과 저장 실패")
                
        except Exception as e:
            logger.error(f"❌ 종합 결과 저장 중 오류: {str(e)}")
    
    async def get_comprehensive_report(self, session_id: str) -> Optional[Dict[str, Any]]:
        """저장된 종합 보고서 조회"""
        try:
            result = self.client.table('analysis_sections')\
                .select('analysis_data')\
                .eq('session_id', session_id)\
                .eq('analysis_type', 'comprehensive_report')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]['analysis_data']
            return None
            
        except Exception as e:
            logger.error(f"종합 보고서 조회 실패: {str(e)}")
            return None
    
    async def enhance_existing_report(self, session_id: str, additional_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """기존 보고서에 추가 분석 결과 통합"""
        logger.info(f"🔄 기존 보고서 향상 - Session: {session_id}")
        
        try:
            # 기존 보고서 조회
            existing_report = await self.get_comprehensive_report(session_id)
            if not existing_report:
                logger.error("기존 보고서를 찾을 수 없습니다")
                return {}
            
            # 추가 분석 결과 통합
            enhanced_report = existing_report.copy()
            
            # 메타데이터 업데이트
            enhanced_report['metadata']['last_updated'] = datetime.now().isoformat()
            enhanced_report['metadata']['enhancements_applied'] = enhanced_report['metadata'].get('enhancements_applied', 0) + 1
            
            # 추가 분석 결과 추가
            enhanced_report['additional_analysis'] = additional_analysis
            
            # 새로운 품질 검증
            quality_check = await self._validate_report_quality(
                enhanced_report['final_report'],
                additional_analysis,
                {'footnote_count': 0}  # 기본값
            )
            enhanced_report['quality_metrics'] = quality_check
            
            # 저장
            await self._save_comprehensive_results(session_id, enhanced_report)
            
            logger.info("✅ 보고서 향상 완료")
            return enhanced_report
            
        except Exception as e:
            logger.error(f"보고서 향상 실패: {str(e)}")
            return {}
    
    async def export_report_for_frontend(self, session_id: str) -> Dict[str, Any]:
        """프론트엔드 출력용 보고서 포맷"""
        logger.info("🖥️ 프론트엔드용 보고서 생성 중...")
        
        try:
            comprehensive_report = await self.get_comprehensive_report(session_id)
            if not comprehensive_report:
                return {}
            
            # 각주 매핑 정보 조회
            footnote_mapping = await self.footnote_service.get_footnote_mapping(session_id)
            
            # 클릭 가능한 각주 생성
            clickable_report = self.footnote_service.create_clickable_footnotes(
                comprehensive_report['final_report'],
                footnote_mapping
            )
            
            # 프론트엔드 전용 포맷
            frontend_export = {
                'session_id': session_id,
                'report_content': clickable_report,
                'footnote_mapping': footnote_mapping,
                'metadata': comprehensive_report['metadata'],
                'quality_score': comprehensive_report['quality_metrics']['completeness_score'],
                'export_timestamp': datetime.now().isoformat(),
                'interactive_elements': {
                    'footnotes_clickable': len(footnote_mapping) > 0,
                    'topics_expandable': comprehensive_report['metadata']['data_sources']['topics_identified'] > 0
                }
            }
            
            logger.info("✅ 프론트엔드용 보고서 생성 완료")
            return frontend_export
            
        except Exception as e:
            logger.error(f"프론트엔드 보고서 생성 실패: {str(e)}")
            return {}