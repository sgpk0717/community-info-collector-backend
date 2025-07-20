from typing import List, Dict, Any, Optional
from openai import OpenAI
import logging
from .base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider 구현"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        OpenAI Provider 초기화
        
        Args:
            api_key: OpenAI API 키 (없으면 환경변수에서 자동 로드)
            model: 사용할 모델명 (기본값: o4-mini)
        """
        self.client = OpenAI(api_key=api_key) if api_key else OpenAI()
        self.model = model or "o4-mini"
        logger.info(f"OpenAI Provider 초기화 완료 - 모델: {self.model}")
    
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
        try:
            logger.info(f"🤖 OpenAI API 호출 시작 - 모델: {self.model}, 온도: {temperature}")
            
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
    
    @property
    def provider_name(self) -> str:
        return "OpenAI"
    
    @property
    def default_model(self) -> str:
        return self.model