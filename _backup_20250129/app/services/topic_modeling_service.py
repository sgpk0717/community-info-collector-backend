import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from app.services.llm_service import LLMService
from app.core.dependencies import get_supabase_client
import json

logger = logging.getLogger(__name__)

class TopicModelingService:
    def __init__(self):
        logger.info("🧠 TopicModelingService 초기화 시작")
        
        # 한국어 지원 sentence transformer 모델 사용
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("✅ 임베딩 모델 로드 완료: paraphrase-multilingual-MiniLM-L12-v2")
        
        # BERTopic 초기화 (한국어 불용어 제거 없이)
        self.topic_model = BERTopic(
            embedding_model=self.embedding_model,
            min_topic_size=3,  # 최소 주제 크기
            nr_topics="auto",  # 자동으로 주제 수 결정
            calculate_probabilities=True,
            verbose=True
        )
        logger.info("✅ BERTopic 모델 초기화 완료")
        
        self.llm_service = LLMService()
        self.client = get_supabase_client()
    
    async def analyze_topics(self, session_id: str) -> List[Dict[str, Any]]:
        """수집된 텍스트에서 주제를 추출하고 분석"""
        logger.info(f"📊 주제 분석 시작 - Session ID: {session_id}")
        
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
            
            # 2. 텍스트 준비
            texts = []
            doc_ids = []
            for doc in documents:
                text = doc['raw_text']
                if text and len(text.strip()) > 10:  # 최소 길이 확인
                    texts.append(text)
                    doc_ids.append(doc['content_id'])
            
            logger.info(f"📝 분석 가능한 텍스트: {len(texts)}개")
            
            if len(texts) < 5:
                logger.warning("⚠️ 분석하기에 텍스트가 너무 적습니다 (최소 5개 필요)")
                return await self._create_single_topic(documents)
            
            # 3. 임베딩 생성 (재사용을 위해 저장)
            logger.info("🔄 텍스트 임베딩 생성 중...")
            embeddings = self._create_embeddings(texts)
            
            # 4. BERTopic으로 주제 모델링
            logger.info("🎯 BERTopic 주제 모델링 시작...")
            topics, probs = self.topic_model.fit_transform(texts, embeddings)
            
            # 5. 주제 정보 추출
            topic_info = self.topic_model.get_topic_info()
            logger.info(f"✅ {len(topic_info) - 1}개의 주제 발견 (이상치 제외)")
            
            # 로그로 주제 정보 출력
            for idx, row in topic_info.iterrows():
                if row['Topic'] != -1:  # -1은 이상치
                    logger.info(f"  주제 {row['Topic']}: {row['Count']}개 문서 - {row['Name']}")
            
            # 6. 각 주제에 대한 상세 분석
            topic_packages = []
            
            for topic_id in set(topics):
                if topic_id == -1:  # 이상치 제외
                    continue
                
                # 해당 주제의 문서들
                topic_docs = [texts[i] for i, t in enumerate(topics) if t == topic_id]
                topic_doc_ids = [doc_ids[i] for i, t in enumerate(topics) if t == topic_id]
                
                # 주제의 핵심 키워드
                keywords = self.topic_model.get_topic(topic_id)
                keyword_list = [word for word, score in keywords[:10]]  # 상위 10개 키워드
                
                logger.info(f"🏷️ 주제 {topic_id} 분석 중... (문서 {len(topic_docs)}개)")
                logger.info(f"   키워드: {', '.join(keyword_list[:5])}")
                
                # LLM으로 주제 레이블 생성
                topic_label = await self._generate_topic_label(
                    topic_docs[:5],  # 대표 문서 5개
                    keyword_list
                )
                
                logger.info(f"   생성된 레이블: {topic_label}")
                
                # 해당 주제의 문서들을 DB에 업데이트
                for doc_id in topic_doc_ids:
                    self.client.table('source_contents')\
                        .update({'topic_id': topic_id})\
                        .eq('content_id', doc_id)\
                        .execute()
                
                topic_package = {
                    'topic_id': topic_id,
                    'topic_label': topic_label,
                    'document_count': len(topic_docs),
                    'keywords': keyword_list,
                    'representative_docs': topic_docs[:3],  # 대표 문서 3개
                    'doc_ids': topic_doc_ids
                }
                
                topic_packages.append(topic_package)
            
            # 주제를 문서 수 기준으로 정렬
            topic_packages.sort(key=lambda x: x['document_count'], reverse=True)
            
            logger.info(f"🎉 주제 분석 완료! 총 {len(topic_packages)}개 주제")
            return topic_packages
            
        except Exception as e:
            logger.error(f"❌ 주제 분석 실패: {str(e)}")
            # 에러 발생 시 단일 주제로 처리
            return await self._create_single_topic(documents)
    
    def _create_embeddings(self, texts: List[str]) -> np.ndarray:
        """텍스트를 임베딩 벡터로 변환"""
        logger.info(f"🔢 {len(texts)}개 텍스트 임베딩 중...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        logger.info(f"✅ 임베딩 생성 완료: shape={embeddings.shape}")
        return embeddings
    
    async def _generate_topic_label(self, sample_docs: List[str], keywords: List[str]) -> str:
        """LLM을 사용하여 가독성 높은 주제 레이블 생성"""
        prompt = f"""당신은 주어진 문서들과 핵심 키워드를 분석하여 전문적인 주제 레이블을 생성하는 리서치 분석가입니다.

문서 샘플:
{chr(10).join(f'- {doc[:200]}...' for doc in sample_docs)}

핵심 키워드:
{', '.join(keywords)}

위 내용을 바탕으로 가장 적절한 한국어 주제 레이블을 생성해주세요. 레이블은 10-20자 내외로 간결하고 명확해야 합니다.
주제 레이블만 응답하세요."""
        
        try:
            response = await self.llm_service._call_openai(prompt, temperature=0.3)
            label = response.strip().strip('"').strip("'")
            return label
        except Exception as e:
            logger.error(f"LLM 레이블 생성 실패: {str(e)}")
            # 폴백: 키워드 기반 레이블
            return f"{keywords[0]} 관련 논의"
    
    async def _create_single_topic(self, documents: List[Dict]) -> List[Dict[str, Any]]:
        """문서가 적을 때 단일 주제로 처리"""
        logger.info("📦 단일 주제로 처리")
        
        texts = [doc['raw_text'] for doc in documents if doc['raw_text']]
        doc_ids = [doc['content_id'] for doc in documents if doc['raw_text']]
        
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
            'keywords': ['종합', '전체'],
            'representative_docs': texts[:3],
            'doc_ids': doc_ids
        }]
    
    def save_topic_model(self, session_id: str):
        """학습된 토픽 모델 저장 (선택사항)"""
        try:
            model_path = f"models/topic_model_{session_id}"
            self.topic_model.save(model_path)
            logger.info(f"💾 토픽 모델 저장 완료: {model_path}")
        except Exception as e:
            logger.error(f"모델 저장 실패: {str(e)}")