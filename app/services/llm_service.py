from typing import List, Dict, Any, Optional, Literal
from app.core.exceptions import OpenAIAPIException
from app.schemas.search import ReportLength
from app.services.llm_providers import BaseLLMProvider, OpenAIProvider, GeminiProvider
import logging
import json
import os
import asyncio

logger = logging.getLogger(__name__)

# Provider 타입 정의
LLMProviderType = Literal["openai", "gemini"]


class LLMService:
    """다중 LLM Provider를 지원하는 통합 LLM Service"""
    
    def __init__(self, provider_type: Optional[LLMProviderType] = None, api_semaphore: Optional[asyncio.Semaphore] = None):
        """
        LLMService 초기화
        
        Args:
            provider_type: 사용할 LLM provider ("openai" 또는 "gemini")
                          None인 경우 환경변수 LLM_PROVIDER에서 읽음 (기본값: "openai")
        """
        # Provider 타입 결정
        if provider_type is None:
            provider_type = os.getenv('LLM_PROVIDER', 'openai').lower()
        
        # Provider 초기화
        self.api_semaphore = api_semaphore
        self.provider = self._initialize_provider(provider_type)
        logger.info(f"LLMService 초기화 완료 - Provider: {self.provider.provider_name}, Model: {self.provider.default_model}")
    
    def _initialize_provider(self, provider_type: str) -> BaseLLMProvider:
        """Provider 타입에 따라 적절한 provider 인스턴스 생성"""
        if provider_type == "openai":
            return OpenAIProvider(api_semaphore=self.api_semaphore)
        elif provider_type == "gemini":
            return GeminiProvider()
        else:
            raise ValueError(f"지원하지 않는 provider 타입: {provider_type}")
    
    async def translate_to_english(self, query: str) -> str:
        """한글 키워드를 영어로 번역"""
        logger.info(f"🌐 번역 시작: '{query}'")
        try:
            prompt = f"""Translate the following Korean search query to English for Reddit search.
            
            Rules:
            1. If it's already in English, return as is
            2. Translate company/brand names to their official English names
            3. Keep the search intent clear and specific
            4. Use common English terms that Reddit users would use
            5. Only return the translated text, nothing else
            
            Examples:
            - "구글 실적발표 예측" → "Google earnings prediction"
            - "테슬라 자율주행 기술" → "Tesla autonomous driving technology"
            - "삼성 신제품 루머" → "Samsung new product rumors"
            
            Keyword: {query}
            Translation:
            """
            
            response = await self.provider.generate(
                prompt=prompt,
                system_prompt="You are a professional translator.",
                temperature=0.3,
                max_tokens=100
            )
            
            translated = response.content.strip()
            logger.info(f"✅ 번역 완료: '{query}' → '{translated}'")
            return translated
            
        except Exception as e:
            logger.error(f"❌ 번역 중 오류 발생: {str(e)}")
            logger.error(f"   Provider: {self.provider.provider_name}")
            logger.error(f"   Model: {self.provider.default_model}")
            logger.error(f"   Query: '{query}'")
            import traceback
            logger.error(f"   Stack trace:\n{traceback.format_exc()}")
            return query  # 실패 시 원본 반환
    
    async def expand_keywords(self, query: str) -> List[str]:
        """주어진 키워드를 확장하여 관련 검색어 생성 (영어)"""
        logger.info(f"🔍 키워드 확장 시작: '{query}'")
        try:
            # 먼저 영어로 번역
            english_query = await self.translate_to_english(query)
            logger.info(f"   번역된 쿼리: '{english_query}'")
            
            prompt = f"""Extract ALL effective search keywords for Reddit about: "{english_query}"
            
            SEARCH STRATEGY RULES:
            1. Generate SHORT, HIGH-IMPACT keywords (1-3 words preferred)
            2. Include multiple variations:
               - Main topic alone (e.g., "Google")
               - Topic + action words (e.g., "Google earnings", "GOOGL forecast")
               - Stock symbols if applicable (e.g., "GOOGL", "GOOG")
               - Common abbreviations and full names
               - Singular AND plural forms
               - Present AND future tense variations
            3. Focus on HIGH-INTENT search patterns:
               - Questions: "how", "what", "when" + topic
               - Comparisons: "vs", "versus", "or"
               - Opinions: "best", "worst", "review"
               - Predictions: "forecast", "prediction", "outlook"
            4. Include Reddit-specific terms:
               - DD (Due Diligence)
               - YOLO, calls, puts (for stock-related)
               - ELI5 (Explain Like I'm 5)
            5. Extract 10-20 keywords to maximize coverage
            
            Examples:
            - For "Tesla earnings prediction": ["Tesla", "TSLA", "Tesla earnings", "TSLA earnings", "Tesla Q4", "Tesla forecast", "TSLA prediction", "Tesla revenue", "Tesla results", "Tesla call", "TSLA DD", "Tesla outlook", "when Tesla earnings", "TSLA vs", "Tesla profit"]
            - For "Apple AI": ["Apple", "AAPL", "Apple AI", "Apple artificial intelligence", "Apple ML", "Apple GPT", "Apple Siri", "AAPL AI", "Apple vs Google AI", "Apple AI news", "when Apple AI", "Apple AI chip"]
            
            Generate comprehensive keywords for: "{english_query}"
            Return as JSON array:
            """
            
            response = await self.provider.generate(
                prompt=prompt,
                system_prompt="You are a keyword expansion expert.",
                temperature=0.7,
                max_tokens=200
            )
            
            content = response.content
            logger.info(f"   LLM 응답 수신 (길이: {len(content)})")
            
            # JSON 파싱 시도
            try:
                # 코드 블록 제거
                if '```json' in content:
                    content = content.replace('```json', '').replace('```', '').strip()
                
                keywords = json.loads(content)
                if isinstance(keywords, list):
                    result = keywords[:5]  # 최대 5개
                    logger.info(f"✅ 키워드 확장 완료: {len(result)}개 - {result}")
                    return result
            except json.JSONDecodeError:
                logger.warning(f"⚠️ JSON 파싱 실패, 원본: {content[:200]}...")
            
            # 파싱 실패 시 원본 키워드만 반환
            logger.warning(f"⚠️ 키워드 확장 실패, 빈 리스트 반환")
            return []
            
        except Exception as e:
            logger.error(f"❌ 키워드 확장 중 오류: {str(e)}")
            logger.error(f"   Provider: {self.provider.provider_name}")
            logger.error(f"   Model: {self.provider.default_model}")
            import traceback
            logger.error(f"   Stack trace:\n{traceback.format_exc()}")
            return []  # 실패해도 계속 진행
    
    async def generate_report(self, posts: List[Dict[str, Any]], query: str, length: ReportLength) -> Dict[str, Any]:
        """수집된 게시물을 바탕으로 분석 보고서 생성"""
        try:
            logger.info(f"📝 보고서 생성 시작 - 키워드: '{query}', 길이: {length.value}, 게시물 수: {len(posts)}")
            
            # 게시물 정보 포맷팅
            posts_text = self._format_posts_for_prompt(posts[:30])  # 최대 30개 게시물
            logger.info(f"📄 게시물 포맷팅 완료 - {min(len(posts), 30)}개 게시물 사용")
            
            # 보고서 길이에 따른 프롬프트 조정
            length_guide = {
                ReportLength.simple: "간단히 3-5 문장으로",
                ReportLength.moderate: "적당히 상세하게 2-3 단락으로", 
                ReportLength.detailed: "매우 상세하게 각 섹션별로"
            }
            
            prompt = f"""You are a professional community analyst. The following are social media posts collected with the keyword '{query}'.

{posts_text}

Based on this English data, create a comprehensive analysis report in KOREAN following these guidelines:

Length: {length_guide[length]}

Required sections (write all section headers and content in Korean):

1. **핵심 요약**: Summarize the key findings
2. **주요 토픽**: Categorize and explain main topics discussed
3. **커뮤니티 반응**: Analyze positive/negative sentiment ratios with evidence
4. **인상적인 의견**: Highlight 2-3 most notable opinions or insights
5. **종합 분석**: Overall community perspective and trends

**CRITICAL FOOTNOTE REQUIREMENTS:**
- When referencing specific posts or opinions, you MUST use the exact format [ref:POST_ID] where POST_ID is the Reddit post ID from the data
- Example: "많은 사용자들이 배터리 문제를 지적했습니다 [ref:t3_abc123]. 특히 한 사용자는 성능이 50% 저하되었다고 보고했습니다 [ref:t3_def456]."
- Use [ref:POST_ID] markers for:
  - Direct quotes from posts
  - Specific statistics or claims
  - Notable opinions or insights
  - Any fact that comes from a specific post
- You can use multiple references in one sentence: [ref:id1][ref:id2]
- These markers will be converted to numbered footnotes later, so use them liberally

DO NOT create a References section - the system will handle that automatically.

Important: 
- The input data is in English, but write the ENTIRE report in Korean
- Use markdown format
- Maintain objective and balanced perspective
- Translate key terms appropriately into Korean
- MUST include [ref:POST_ID] markers when referencing specific posts
"""
            
            logger.info(f"🤖 {self.provider.provider_name} API 호출 시작...")
            
            response = await self.provider.generate(
                prompt=prompt,
                system_prompt="You are a professional community analyst who creates insightful reports in Korean.",
                temperature=0.7,
                max_tokens=2000 if length == ReportLength.detailed else 1000
            )
            
            full_report = response.content
            logger.info(f"✅ {self.provider.provider_name} API 응답 수신 - 보고서 길이: {len(full_report)} 문자")
            
            # 각주 매핑 추출 (변환 전)
            footnote_mapping = self._extract_footnote_mapping(full_report, posts)
            
            # [ref:POST_ID]를 번호로 변환
            logger.info("🔄 각주 변환 시작...")
            processed_report = self._convert_refs_to_footnotes(full_report, footnote_mapping)
            logger.info(f"✅ 각주 변환 완료 - {len(footnote_mapping)}개 각주 처리")
            
            # 요약 생성 (한글) - 변환된 보고서 사용
            logger.info("📝 요약 생성 시작...")
            summary_prompt = f"다음 한국어 보고서의 핵심 내용을 한국어로 2-3문장으로 요약해주세요:\n\n{processed_report[:1000]}"
            
            summary_response = await self.provider.generate(
                prompt=summary_prompt,
                system_prompt="You are a summarization expert.",
                temperature=0.5,
                max_tokens=200
            )
            
            summary = summary_response.content
            logger.info(f"✅ 요약 생성 완료 - {len(summary)} 문자")
            
            logger.info(f"🎉 AI 보고서 생성 완료!")
            logger.info(f"   - 전체 보고서: {len(processed_report)} 문자")
            logger.info(f"   - 요약: {len(summary)} 문자")
            logger.info(f"   - 각주 수: {len(footnote_mapping)}개")
            
            return {
                "summary": summary,
                "full_report": processed_report,
                "footnote_mapping": footnote_mapping
            }
            
        except Exception as e:
            logger.error(f"{self.provider.provider_name} API error in generate_report: {str(e)}")
            raise OpenAIAPIException(f"Failed to generate report: {str(e)}")
    
    def _format_posts_for_prompt(self, posts: List[Dict[str, Any]]) -> str:
        """게시물을 프롬프트용으로 포맷팅"""
        formatted_posts = []
        
        for i, post in enumerate(posts, 1):
            # 개선된 포맷팅에 루머 점수와 수집 벡터 정보 포함
            vector_info = post.get('collection_vector', 'unknown')
            rumor_score = post.get('rumor_score', 0)
            linguistic_flags = post.get('linguistic_flags', [])
            
            post_text = f"""[게시물 {i}]
POST_ID: {post['id']}
제목: {post['title']}
점수: {post['score']} | 댓글: {post['num_comments']} | 루머점수: {rumor_score}/10
서브레딧: r/{post['subreddit']} | 수집벡터: {vector_info}
언어신호: {', '.join(linguistic_flags) if linguistic_flags else '없음'}
내용: {post['selftext'][:200] if post['selftext'] else '(내용 없음)'}
---"""
            formatted_posts.append(post_text)
        
        logger.debug(f"📄 게시물 포맷팅: {len(formatted_posts)}개 게시물")
        return "\n".join(formatted_posts)
    
    def _extract_footnote_mapping(self, report: str, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """보고서에서 각주 매핑 추출 및 [ref:POST_ID]를 번호로 변환"""
        import re
        
        footnote_mapping = []
        ref_to_footnote = {}  # POST_ID -> footnote_number 매핑
        
        # [ref:POST_ID] 패턴 찾기
        ref_pattern = r'\[ref:([^\]]+)\]'
        refs = re.findall(ref_pattern, report)
        
        if not refs:
            logger.info("📄 참조가 발견되지 않음")
            return footnote_mapping
        
        logger.info(f"🔗 참조 발견: {len(refs)}개 (고유: {len(set(refs))}개)")
        
        # 고유한 POST_ID들을 추출하고 번호 할당
        unique_refs = []
        for ref in refs:
            if ref not in ref_to_footnote:
                unique_refs.append(ref)
                ref_to_footnote[ref] = len(unique_refs)
        
        # 각 고유한 참조에 대해 게시물 정보 찾기
        posts_by_id = {post['id']: post for post in posts}
        
        for post_id, footnote_number in ref_to_footnote.items():
            if post_id in posts_by_id:
                post = posts_by_id[post_id]
                footnote_mapping.append({
                    "footnote_number": footnote_number,
                    "post_id": post['id'],
                    "url": post['url'],
                    "title": post['title'],
                    "score": post['score'],
                    "comments": post['num_comments'],
                    "created_utc": post['created_utc'],
                    "subreddit": post['subreddit'],
                    "author": post['author'],
                    "position_in_report": footnote_number
                })
            else:
                logger.warning(f"⚠️ 참조된 POST_ID를 찾을 수 없음: {post_id}")
        
        # 각주 번호순으로 정렬
        footnote_mapping.sort(key=lambda x: x['footnote_number'])
        
        logger.info(f"🔗 각주 매핑 완료: {len(footnote_mapping)}개")
        return footnote_mapping
    
    def _convert_refs_to_footnotes(self, report: str, footnote_mapping: List[Dict[str, Any]]) -> str:
        """[ref:POST_ID] 마커를 번호 각주 [1], [2] 등으로 변환"""
        import re
        
        # footnote_mapping에서 post_id -> footnote_number 매핑 생성
        post_id_to_footnote = {
            item['post_id']: item['footnote_number'] 
            for item in footnote_mapping
        }
        
        # 모든 [ref:POST_ID] 패턴을 찾아 번호로 변환
        def replace_ref(match):
            post_id = match.group(1)
            if post_id in post_id_to_footnote:
                return f"[{post_id_to_footnote[post_id]}]"
            return match.group(0)  # 매핑이 없으면 원본 유지
        
        processed_report = re.sub(r'\[ref:([^\]]+)\]', replace_ref, report)
        
        # 보고서 끝에 참조 목록 추가
        if footnote_mapping:
            processed_report += "\n\n## 참조 목록\n\n"
            for item in footnote_mapping:
                processed_report += f"[{item['footnote_number']}] {item['title']} - r/{item['subreddit']} (점수: {item['score']}, 댓글: {item['comments']})\n"
        
        return processed_report

    async def _call_llm(self, prompt: str, temperature: float = 0.7) -> str:
        """내부 헬퍼 메서드 - 기존 코드와의 호환성을 위해 유지"""
        response = await self.provider.generate(
            prompt=prompt,
            system_prompt="You are a professional analyst and expert writer.",
            temperature=temperature,
            max_tokens=4000
        )
        return response.content