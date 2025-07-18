from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM 응답을 위한 통합 데이터 클래스"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None
    raw_response: Optional[Any] = None


class BaseLLMProvider(ABC):
    """LLM Provider를 위한 추상 베이스 클래스"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """
        LLM에 프롬프트를 전송하고 응답을 받습니다.
        
        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (optional)
            temperature: 창의성 조절 (0.0 ~ 1.0)
            max_tokens: 최대 응답 토큰 수
            **kwargs: provider별 추가 파라미터
            
        Returns:
            LLMResponse 객체
        """
        pass
    
    @abstractmethod
    async def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """
        대화 형식의 메시지로 LLM에 요청합니다.
        
        Args:
            messages: [{"role": "system|user|assistant", "content": "..."}] 형식
            temperature: 창의성 조절 (0.0 ~ 1.0)
            max_tokens: 최대 응답 토큰 수
            **kwargs: provider별 추가 파라미터
            
        Returns:
            LLMResponse 객체
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 이름을 반환합니다."""
        pass
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        """기본 모델명을 반환합니다."""
        pass