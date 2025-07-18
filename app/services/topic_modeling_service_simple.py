import logging
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
import re
from app.services.llm_service import LLMService
from app.core.dependencies import get_supabase_client
import json

logger = logging.getLogger(__name__)

class SimpleTopicModelingService:
    """간단한 키워드 기반 주제 모델링 서비스"""
    
    def __init__(self):
        logger.info("🧠 SimpleTopicModelingService 초기화")
        self.llm_service = LLMService()
        self.client = get_supabase_client()
        
        # 한국어 불용어 리스트
        self.stop_words = {
            '그', '저', '것', '수', '등', '및', '또', '더', '매우', '와', '은', '는', '이', '가',
            '을', '를', '에', '의', '로', '으로', '하다', '있다', '되다', '없다', '이다'
        }
    
    async def analyze_topics(self, session_id: str) -> List[Dict[str, Any]]:
        """수집된 텍스트에서 주제를 추출하고 분석"""
        logger.info(f"📊 간단한 주제 분석 시작 - Session ID: {session_id}")
        
        try:
            # 1. 수집된 데이터 조회
            logger.info("📥 수집된 데이터 조회 중...")
            result = self.client.table('source_contents')\
                .select("*")\
                .eq('metadata->>session_id', session_id)\
                .execute()
            
            if not result.data:
                logger.warning("❌ 분석할 데이터가 없습니다")
                return []
            
            documents = result.data
            logger.info(f"✅ {len(documents)}개의 문서 조회 완료")
            
            # 2. 텍스트 전처리 및 키워드 추출
            all_keywords = []
            doc_keywords_map = defaultdict(list)
            
            for doc in documents:
                text = doc['raw_text']
                if text and len(text.strip()) > 10:
                    keywords = self._extract_keywords(text)
                    all_keywords.extend(keywords)
                    doc_keywords_map[doc['content_id']] = keywords
            
            # 3. 빈도 기반 주요 주제 추출
            keyword_freq = Counter(all_keywords)
            top_keywords = keyword_freq.most_common(20)  # 상위 20개 키워드
            
            logger.info(f"🔍 주요 키워드: {[k for k, v in top_keywords[:10]]}")
            
            # 4. 키워드 그룹핑으로 주제 생성
            topics = await self._group_keywords_into_topics(top_keywords, documents)
            
            # 5. 각 문서를 주제에 할당
            for doc in documents:
                doc_id = doc['content_id']
                doc_keywords = set(doc_keywords_map[doc_id])
                
                # 가장 많이 매칭되는 주제 찾기
                best_topic = 0
                max_matches = 0
                
                for i, topic in enumerate(topics):
                    topic_keywords = set(topic['keywords'])
                    matches = len(doc_keywords & topic_keywords)
                    if matches > max_matches:
                        max_matches = matches
                        best_topic = i
                
                # DB 업데이트
                self.client.table('source_contents')\
                    .update({'topic_id': best_topic})\
                    .eq('content_id', doc_id)\
                    .execute()
            
            # 6. 각 주제별 문서 수 계산 및 대표 문서 선택
            for i, topic in enumerate(topics):
                topic_docs = [doc for doc in documents 
                             if doc.get('topic_id') == i or 
                             any(kw in doc['raw_text'] for kw in topic['keywords'][:3])]
                
                topic['document_count'] = len(topic_docs)
                topic['representative_docs'] = [doc['raw_text'][:200] + '...' 
                                              for doc in topic_docs[:3]]
                topic['doc_ids'] = [doc['content_id'] for doc in topic_docs]
                
                logger.info(f"📌 주제 {i}: {topic['topic_label']} ({len(topic_docs)}개 문서)")
            
            # 문서가 없는 주제 제거
            topics = [t for t in topics if t['document_count'] > 0]
            
            # 문서 수 기준으로 정렬
            topics.sort(key=lambda x: x['document_count'], reverse=True)
            
            logger.info(f"🎉 주제 분석 완료! 총 {len(topics)}개 주제")
            return topics
            
        except Exception as e:
            logger.error(f"❌ 주제 분석 실패: {str(e)}")
            # 에러 발생 시 단일 주제로 처리
            return await self._create_single_topic(documents if 'documents' in locals() else [])
    
    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        # 간단한 키워드 추출 (명사 위주)
        # 한글, 영문, 숫자만 추출
        words = re.findall(r'[가-힣]+|[a-zA-Z]+', text.lower())
        
        # 2글자 이상, 불용어 제외
        keywords = [w for w in words 
                   if len(w) >= 2 and w not in self.stop_words]
        
        # 빈도수 기반으로 상위 키워드 추출
        word_freq = Counter(keywords)
        return [word for word, freq in word_freq.most_common(10)]
    
    async def _group_keywords_into_topics(self, top_keywords: List[tuple], 
                                        documents: List[Dict]) -> List[Dict[str, Any]]:
        """키워드를 주제로 그룹핑"""
        # LLM을 사용하여 키워드를 주제로 그룹핑
        keywords_text = ', '.join([f"{kw}({freq})" for kw, freq in top_keywords])
        
        prompt = f"""다음은 텍스트에서 추출된 주요 키워드와 빈도수입니다:

{keywords_text}

이 키워드들을 3-5개의 의미있는 주제로 그룹핑해주세요. 각 주제별로:
1. 주제명 (10-20자)
2. 관련 키워드 5-8개

JSON 형식으로 응답하세요:
[
  {{
    "topic_label": "주제명",
    "keywords": ["키워드1", "키워드2", ...]
  }},
  ...
]"""
        
        try:
            response = await self.llm_service._call_openai(prompt, temperature=0.3)
            topics_data = json.loads(response)
            
            # topic_id 추가
            topics = []
            for i, topic in enumerate(topics_data):
                topics.append({
                    'topic_id': i,
                    'topic_label': topic['topic_label'],
                    'keywords': topic['keywords'][:8],  # 최대 8개
                    'document_count': 0,
                    'representative_docs': [],
                    'doc_ids': []
                })
            
            return topics
            
        except Exception as e:
            logger.error(f"LLM 주제 그룹핑 실패: {str(e)}")
            # 폴백: 단순 그룹핑
            return self._simple_topic_grouping(top_keywords)
    
    def _simple_topic_grouping(self, top_keywords: List[tuple]) -> List[Dict[str, Any]]:
        """단순 키워드 그룹핑 (폴백)"""
        # 상위 키워드를 3개 그룹으로 나누기
        topics = []
        keywords_per_topic = len(top_keywords) // 3 + 1
        
        for i in range(3):
            start_idx = i * keywords_per_topic
            end_idx = start_idx + keywords_per_topic
            topic_keywords = [kw for kw, freq in top_keywords[start_idx:end_idx]]
            
            if topic_keywords:
                topics.append({
                    'topic_id': i,
                    'topic_label': f"{topic_keywords[0]} 관련 논의",
                    'keywords': topic_keywords,
                    'document_count': 0,
                    'representative_docs': [],
                    'doc_ids': []
                })
        
        return topics
    
    async def _create_single_topic(self, documents: List[Dict]) -> List[Dict[str, Any]]:
        """문서가 적을 때 단일 주제로 처리"""
        logger.info("📦 단일 주제로 처리")
        
        if not documents:
            return []
        
        texts = [doc['raw_text'] for doc in documents if doc.get('raw_text')]
        doc_ids = [doc['content_id'] for doc in documents if doc.get('raw_text')]
        
        # 모든 문서를 주제 0으로 할당
        for doc_id in doc_ids:
            self.client.table('source_contents')\
                .update({'topic_id': 0})\
                .eq('content_id', doc_id)\
                .execute()
        
        return [{
            'topic_id': 0,
            'topic_label': '전체 내용 종합',
            'document_count': len(texts),
            'keywords': ['종합', '전체', '분석'],
            'representative_docs': texts[:3],
            'doc_ids': doc_ids
        }]