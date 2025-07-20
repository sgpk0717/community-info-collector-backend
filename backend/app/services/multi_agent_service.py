import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime
from app.services.llm_service import LLMService
from app.core.dependencies import get_supabase_client
from app.services.topic_modeling_service_simple import SimpleTopicModelingService
import asyncio

logger = logging.getLogger(__name__)

class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    SUMMARIZER = "summarizer"
    SENTIMENT_ANALYZER = "sentiment_analyzer"
    TREND_ANALYZER = "trend_analyzer"
    SYNTHESIS_AGENT = "synthesis_agent"

@dataclass
class AgentMessage:
    role: AgentRole
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]

@dataclass
class AgentResponse:
    agent_role: AgentRole
    analysis_result: str
    confidence_score: float
    supporting_data: Dict[str, Any]
    execution_time: float

class MultiAgentService:
    """
    LangChain 기반 멀티 에이전트 분석 시스템
    
    에이전트 구성:
    - Orchestrator: 전체 분석 프로세스를 조율하고 관리
    - Summarizer: 각 주제별 핵심 요약 생성
    - Sentiment Analyzer: 감정 분석 및 여론 분석
    - Trend Analyzer: 트렌드 및 패턴 분석
    - Synthesis Agent: 각 에이전트 결과를 종합하여 최종 보고서 생성
    """
    
    def __init__(self):
        logger.info("🤖 MultiAgentService 초기화")
        
        self.llm_service = LLMService()
        self.client = get_supabase_client()
        self.topic_service = SimpleTopicModelingService()
        
        # 에이전트별 특화 프롬프트 템플릿
        self.agent_prompts = {
            AgentRole.ORCHESTRATOR: self._get_orchestrator_prompt(),
            AgentRole.SUMMARIZER: self._get_summarizer_prompt(),
            AgentRole.SENTIMENT_ANALYZER: self._get_sentiment_analyzer_prompt(),
            AgentRole.TREND_ANALYZER: self._get_trend_analyzer_prompt(),
            AgentRole.SYNTHESIS_AGENT: self._get_synthesis_agent_prompt()
        }
        
        logger.info("✅ 멀티 에이전트 시스템 초기화 완료")
    
    async def analyze_with_agents(self, session_id: str, query: str) -> Dict[str, Any]:
        """멀티 에이전트를 활용한 종합 분석"""
        logger.info(f"🎯 멀티 에이전트 분석 시작 - Session: {session_id}, Query: {query}")
        
        start_time = datetime.now()
        
        try:
            # 1. Orchestrator가 분석 계획 수립
            orchestration_plan = await self._execute_orchestrator(session_id, query)
            logger.info(f"📋 Orchestrator 분석 계획: {orchestration_plan['plan_summary']}")
            
            # 2. 주제 모델링 실행
            topics = await self.topic_service.analyze_topics(session_id)
            logger.info(f"📊 주제 모델링 완료 - {len(topics)}개 주제 발견")
            
            # 3. 각 에이전트 병렬 실행
            logger.info("🔄 전문 에이전트들 병렬 실행 시작...")
            agent_tasks = [
                self._execute_summarizer(session_id, topics),
                self._execute_sentiment_analyzer(session_id, topics),
                self._execute_trend_analyzer(session_id, topics, query)
            ]
            
            agent_results = await asyncio.gather(*agent_tasks)
            
            # 4. 결과 구조화
            analysis_results = {
                'orchestration_plan': orchestration_plan,
                'topics': topics,
                'summarizer_result': agent_results[0],
                'sentiment_result': agent_results[1],
                'trend_result': agent_results[2]
            }
            
            # 5. Synthesis Agent가 최종 보고서 생성
            logger.info("🎨 Synthesis Agent 최종 보고서 생성 중...")
            final_report = await self._execute_synthesis_agent(analysis_results, query)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 6. 결과 저장
            await self._save_agent_analysis(session_id, {
                'query': query,
                'execution_time': execution_time,
                'agent_results': analysis_results,
                'final_report': final_report
            })
            
            logger.info(f"🎉 멀티 에이전트 분석 완료! 소요시간: {execution_time:.2f}초")
            
            return {
                'session_id': session_id,
                'query': query,
                'execution_time': execution_time,
                'topics_count': len(topics),
                'final_report': final_report,
                'detailed_results': analysis_results
            }
            
        except Exception as e:
            logger.error(f"❌ 멀티 에이전트 분석 실패: {str(e)}")
            raise
    
    async def _execute_orchestrator(self, session_id: str, query: str) -> Dict[str, Any]:
        """Orchestrator 에이전트 실행"""
        logger.info("🎯 Orchestrator 에이전트 실행")
        
        # 기본 문서 정보 수집
        result = self.client.table('source_contents')\
            .select("content_id, raw_text, metadata")\
            .eq('metadata->>session_id', session_id)\
            .execute()
        
        documents = result.data
        doc_count = len(documents)
        
        # 분석 계획 생성
        prompt = self.agent_prompts[AgentRole.ORCHESTRATOR].format(
            query=query,
            doc_count=doc_count,
            sample_content=documents[0]['raw_text'][:200] if documents else "내용 없음"
        )
        
        response = await self.llm_service._call_openai(prompt, temperature=0.3)
        
        try:
            plan_data = json.loads(response)
            logger.info(f"✅ Orchestrator 계획 수립 완료")
            return plan_data
        except json.JSONDecodeError:
            logger.warning("⚠️ Orchestrator 응답 파싱 실패, 기본 계획 사용")
            return {
                "plan_summary": "기본 분석 계획 수행",
                "analysis_steps": ["주제 분석", "요약", "감정 분석", "트렌드 분석", "종합 보고서"],
                "estimated_time": 30,
                "confidence": 0.8
            }
    
    async def _execute_summarizer(self, session_id: str, topics: List[Dict[str, Any]]) -> AgentResponse:
        """Summarizer 에이전트 실행 (최적화된 버전)"""
        logger.info("📝 Summarizer 에이전트 실행")
        
        start_time = datetime.now()
        
        # 모든 주제를 한 번에 처리 (API 호출 최적화)
        all_topics_content = []
        for topic in topics:
            topic_content = f"주제: {topic['topic_label']} (문서 {topic['document_count']}개)\n"
            topic_content += f"키워드: {', '.join(topic['keywords'])}\n"
            topic_content += f"내용: {' '.join(topic['representative_docs'][:2])}\n"  # 처음 2개만 사용
            all_topics_content.append(topic_content)
        
        combined_prompt = f"""당신은 전문 요약 분석가입니다. 다음 주제들을 각각 요약해주세요:

{chr(10).join(all_topics_content)}

각 주제별로 3-4문장으로 핵심 요약을 작성하고, 다음 JSON 형식으로 응답해주세요:

[
  {{
    "topic_id": 0,
    "topic_label": "주제명",
    "summary": "요약 내용",
    "document_count": 문서수
  }},
  ...
]"""
        
        response = await self.llm_service._call_openai(combined_prompt, temperature=0.5)
        
        try:
            topic_summaries = json.loads(response)
        except json.JSONDecodeError:
            # JSON 파싱 실패 시 폴백
            topic_summaries = [{
                'topic_id': i,
                'topic_label': topic['topic_label'],
                'summary': f"{topic['topic_label']} 관련 내용 분석",
                'document_count': topic['document_count']
            } for i, topic in enumerate(topics)]
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Summarizer 완료 - {len(topic_summaries)}개 주제 요약")
        
        return AgentResponse(
            agent_role=AgentRole.SUMMARIZER,
            analysis_result=json.dumps(topic_summaries, ensure_ascii=False),
            confidence_score=0.9,
            supporting_data={'topics_processed': len(topics)},
            execution_time=execution_time
        )
    
    async def _execute_sentiment_analyzer(self, session_id: str, topics: List[Dict[str, Any]]) -> AgentResponse:
        """Sentiment Analyzer 에이전트 실행"""
        logger.info("😊 Sentiment Analyzer 에이전트 실행")
        
        start_time = datetime.now()
        
        # 전체 문서 감정 분석
        all_docs = []
        for topic in topics:
            all_docs.extend(topic['representative_docs'])
        
        combined_content = "\n\n".join(all_docs)
        
        prompt = self.agent_prompts[AgentRole.SENTIMENT_ANALYZER].format(
            content=combined_content,
            total_docs=len(all_docs)
        )
        
        response = await self.llm_service._call_openai(prompt, temperature=0.4)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Sentiment Analyzer 완료 - 감정 분석 완료")
        
        return AgentResponse(
            agent_role=AgentRole.SENTIMENT_ANALYZER,
            analysis_result=response,
            confidence_score=0.85,
            supporting_data={'documents_analyzed': len(all_docs)},
            execution_time=execution_time
        )
    
    async def _execute_trend_analyzer(self, session_id: str, topics: List[Dict[str, Any]], query: str) -> AgentResponse:
        """Trend Analyzer 에이전트 실행"""
        logger.info("📈 Trend Analyzer 에이전트 실행")
        
        start_time = datetime.now()
        
        # 트렌드 분석을 위한 키워드 및 패턴 추출
        trend_data = {
            'query': query,
            'topics': [{
                'label': topic['topic_label'],
                'doc_count': topic['document_count'],
                'keywords': topic['keywords']
            } for topic in topics]
        }
        
        prompt = self.agent_prompts[AgentRole.TREND_ANALYZER].format(
            query=query,
            trend_data=json.dumps(trend_data, ensure_ascii=False),
            topic_count=len(topics)
        )
        
        response = await self.llm_service._call_openai(prompt, temperature=0.6)
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"✅ Trend Analyzer 완료 - 트렌드 분석 완료")
        
        return AgentResponse(
            agent_role=AgentRole.TREND_ANALYZER,
            analysis_result=response,
            confidence_score=0.8,
            supporting_data={'topics_analyzed': len(topics)},
            execution_time=execution_time
        )
    
    async def _execute_synthesis_agent(self, analysis_results: Dict[str, Any], query: str) -> str:
        """Synthesis Agent가 모든 에이전트 결과를 종합하여 최종 보고서 생성"""
        logger.info("🎨 Synthesis Agent 최종 보고서 생성")
        
        # 각 에이전트 결과 구조화
        synthesis_data = {
            'query': query,
            'orchestration_plan': analysis_results['orchestration_plan'],
            'topics_summary': f"{len(analysis_results['topics'])}개 주제 발견",
            'summarizer_result': analysis_results['summarizer_result'].analysis_result,
            'sentiment_result': analysis_results['sentiment_result'].analysis_result,
            'trend_result': analysis_results['trend_result'].analysis_result
        }
        
        prompt = self.agent_prompts[AgentRole.SYNTHESIS_AGENT].format(
            query=query,
            synthesis_data=json.dumps(synthesis_data, ensure_ascii=False, indent=2)
        )
        
        final_report = await self.llm_service._call_openai(prompt, temperature=0.7)
        
        logger.info("✅ Synthesis Agent 최종 보고서 생성 완료")
        
        return final_report
    
    async def _save_agent_analysis(self, session_id: str, analysis_data: Dict[str, Any]):
        """에이전트 분석 결과를 별도 테이블에 저장"""
        try:
            # analysis_sections 테이블에 저장
            sections_data = {
                'session_id': session_id,
                'analysis_type': 'multi_agent',
                'analysis_data': analysis_data,
                'created_at': datetime.now().isoformat()
            }
            
            result = self.client.table('analysis_sections').insert(sections_data).execute()
            
            if result.data:
                logger.info(f"✅ 에이전트 분석 결과 저장 완료 - ID: {result.data[0]['id']}")
            else:
                logger.warning("⚠️ 에이전트 분석 결과 저장 실패")
                
        except Exception as e:
            logger.error(f"❌ 에이전트 분석 결과 저장 중 오류: {str(e)}")
    
    # 에이전트별 프롬프트 템플릿
    def _get_orchestrator_prompt(self) -> str:
        return """당신은 분석 프로세스를 조율하는 Orchestrator Agent입니다.

주어진 정보:
- 분석 키워드: {query}
- 수집된 문서 수: {doc_count}개
- 샘플 내용: {sample_content}

다음 JSON 형식으로 분석 계획을 수립하세요:
{{
    "plan_summary": "분석 계획 요약 (1-2문장)",
    "analysis_steps": ["단계1", "단계2", "단계3", "단계4", "단계5"],
    "estimated_time": 예상_소요시간_초,
    "confidence": 0.0~1.0_사이_신뢰도,
    "special_considerations": "특별히 고려할 사항들"
}}

분석 계획을 체계적으로 수립해주세요."""

    def _get_summarizer_prompt(self) -> str:
        return """당신은 전문 요약 분석가입니다.

주제 정보:
- 주제명: {topic_label}
- 문서 수: {doc_count}개
- 핵심 키워드: {keywords}

내용:
{topic_content}

위 내용을 다음 기준으로 요약해주세요:
1. 핵심 메시지를 3-5문장으로 요약
2. 주요 논점들을 정리
3. 특별히 주목할 만한 의견이나 사실 강조
4. 객관적이고 균형잡힌 시각 유지

한국어로 명확하고 간결하게 작성해주세요."""

    def _get_sentiment_analyzer_prompt(self) -> str:
        return """당신은 감정 분석 전문가입니다.

분석 대상:
- 총 문서 수: {total_docs}개

내용:
{content}

다음 형식으로 감정 분석을 수행하세요:

## 전반적 감정 분석
- 긍정적 의견: X% (구체적 근거)
- 부정적 의견: X% (구체적 근거)
- 중립적 의견: X% (구체적 근거)

## 주요 감정 요인
1. 가장 긍정적인 요소: 
2. 가장 부정적인 요소:
3. 논란이 되는 요소:

## 감정 동향
- 현재 커뮤니티의 전체적인 분위기
- 특별한 감정 패턴이나 변화

객관적인 데이터를 바탕으로 분석해주세요."""

    def _get_trend_analyzer_prompt(self) -> str:
        return """당신은 트렌드 분석 전문가입니다.

분석 키워드: {query}
주제 수: {topic_count}개

데이터:
{trend_data}

다음 관점에서 트렌드를 분석해주세요:

## 주요 트렌드
1. 가장 주목받는 주제와 그 이유
2. 새롭게 떠오르는 관심사
3. 감소하는 관심사

## 패턴 분석
- 키워드 연관성 패턴
- 주제별 관심도 분포
- 특이한 패턴이나 이상 신호

## 미래 전망
- 향후 3-6개월 예상 트렌드
- 주목해야 할 변화 요인
- 리스크 요소

데이터 기반의 객관적 분석을 제공해주세요."""

    def _get_synthesis_agent_prompt(self) -> str:
        return """당신은 종합 분석 전문가입니다. 여러 전문 에이전트의 분석 결과를 종합하여 최종 보고서를 작성합니다.

분석 키워드: {query}

각 에이전트 분석 결과:
{synthesis_data}

다음 구조로 종합 보고서를 작성해주세요:

# {query} 종합 분석 보고서

## 📊 핵심 요약
[전체 분석의 핵심 내용을 3-4문장으로 요약]

## 🎯 주요 발견사항
1. [주제 분석 결과의 핵심]
2. [감정 분석 결과의 핵심]
3. [트렌드 분석 결과의 핵심]

## 📈 상세 분석
### 커뮤니티 반응 분석
[감정 분석 결과를 바탕으로]

### 트렌드 및 패턴
[트렌드 분석 결과를 바탕으로]

### 주제별 심층 분석
[요약 분석 결과를 바탕으로]

## 🔮 결론 및 전망
[종합적인 결론과 향후 전망]

## ⚠️ 주의사항
[분석 결과 해석 시 고려사항]

모든 에이전트의 분석을 균형있게 반영하여 포괄적인 보고서를 작성해주세요."""