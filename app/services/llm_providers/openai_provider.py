from typing import List, Dict, Any, Optional
from openai import OpenAI
import logging
from .base import BaseLLMProvider, LLMResponse
import asyncio

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider 구현"""
    
    # 추론 모델 목록 (o1, o3, o4 시리즈)
    REASONING_MODELS = {
        'o1-preview', 'o1-mini', 
        'o3', 'o3-mini',
        'o4', 'o4-mini'
    }
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, api_semaphore: Optional[asyncio.Semaphore] = None):
        """
        OpenAI Provider 초기화
        
        Args:
            api_key: OpenAI API 키 (없으면 환경변수에서 자동 로드)
            model: 사용할 모델명 (기본값: o4-mini)
            api_semaphore: API 동시 호출 제한을 위한 Semaphore
        """
        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()
        self.model = model or "o4-mini"
        self.api_semaphore = api_semaphore or asyncio.Semaphore(3)  # 기본값: 동시 3개 호출
        logger.info(f"OpenAI Provider 초기화 완료 - 모델: {self.model}")
    
    def is_reasoning_model(self, model: Optional[str] = None) -> bool:
        """주어진 모델이 추론 모델인지 확인"""
        check_model = model or self.model
        return check_model in self.REASONING_MODELS
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """OpenAI API를 사용하여 텍스트 생성"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return await self.generate_with_messages(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    async def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """OpenAI Chat Completions API 호출"""
        # Semaphore로 API 호출 제한
        async with self.api_semaphore:
            logger.info(f"🔒 API Semaphore 획듍 - 현재 대기: {self.api_semaphore._value}/{self.api_semaphore._initial_value}")
            
            try:
                # 추론 모델 여부 확인
                is_reasoning = self.is_reasoning_model()
            
            if is_reasoning:
                logger.info(f"🤖 OpenAI 추론 모델 API 호출 시작 - 모델: {self.model}")
                logger.info("   추론 모델이므로 model과 messages 파라미터만 사용합니다.")
                
                # 추론 모델은 model과 messages만 지원
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages
                )
            else:
                logger.info(f"🤖 OpenAI API 호출 시작 - 모델: {self.model}, 온도: {temperature}")
                
                # 일반 모델은 모든 파라미터 지원
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs  # 추가 파라미터 (top_p, frequency_penalty 등)
                )
            
            content = response.choices[0].message.content.strip()
            
            # 사용량 정보 추출
            usage = None
            if hasattr(response, 'usage'):
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            
                logger.info(f"✅ OpenAI API 응답 수신 - 길이: {len(content)} 문자")
                if usage:
                    logger.info(f"   토큰 사용: {usage['total_tokens']} (프롬프트: {usage['prompt_tokens']}, 완성: {usage['completion_tokens']})")
                
                return LLMResponse(
                    content=content,
                    model=self.model,
                    usage=usage,
                    raw_response=response
                )
                
            except Exception as e:
                logger.error(f"❌ OpenAI API 호출 실패: {str(e)}")
                raise
            finally:
                logger.info(f"🔓 API Semaphore 해제")
    
    @property
    def provider_name(self) -> str:
        return "OpenAI"
    
    @property
    def default_model(self) -> str:
        return self.model