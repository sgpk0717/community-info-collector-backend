from typing import List, Dict, Any, Optional
import requests
import json
import logging
import os
from .base import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API Provider 구현"""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Gemini Provider 초기화
        
        Args:
            api_key: Gemini API 키 (없으면 환경변수에서 로드)
            model: 사용할 모델명 (기본값: gemini-2.5-flash-latest)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
        
        self.model = model or "gemini-1.5-flash"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        logger.info(f"Gemini Provider 초기화 완료 - 모델: {self.model}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """Gemini API를 사용하여 텍스트 생성"""
        try:
            logger.info(f"🤖 Gemini API 호출 시작 - 모델: {self.model}, 온도: {temperature}")
            
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            
            # 요청 데이터 구성
            data = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens
                }
            }
            
            # 시스템 프롬프트가 있으면 추가
            if system_prompt:
                data["systemInstruction"] = {
                    "parts": [{
                        "text": system_prompt
                    }]
                }
            
            # 추가 파라미터 병합
            if kwargs:
                data["generationConfig"].update(kwargs)
            
            # API 호출
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            
            result = response.json()
            
            # 응답 파싱
            if "candidates" in result and result["candidates"]:
                content = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # 사용량 정보 추출 (Gemini는 토큰 정보를 직접 제공하지 않음)
                usage = None
                if "usageMetadata" in result:
                    usage = {
                        "prompt_tokens": result["usageMetadata"].get("promptTokenCount", 0),
                        "completion_tokens": result["usageMetadata"].get("candidatesTokenCount", 0),
                        "total_tokens": result["usageMetadata"].get("totalTokenCount", 0)
                    }
                
                logger.info(f"✅ Gemini API 응답 수신 - 길이: {len(content)} 문자")
                if usage:
                    logger.info(f"   토큰 사용: {usage['total_tokens']} (프롬프트: {usage['prompt_tokens']}, 완성: {usage['completion_tokens']})")
                
                return LLMResponse(
                    content=content.strip(),
                    model=self.model,
                    usage=usage,
                    raw_response=result
                )
            else:
                raise ValueError("Gemini API 응답에 유효한 콘텐츠가 없습니다.")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Gemini API 요청 실패: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"   응답 내용: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Gemini API 호출 실패: {str(e)}")
            raise
    
    async def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> LLMResponse:
        """메시지 형식을 Gemini 형식으로 변환하여 호출"""
        # 시스템 메시지와 사용자 메시지 분리
        system_prompt = None
        user_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            elif msg["role"] == "user":
                user_messages.append(msg["content"])
            elif msg["role"] == "assistant":
                # Gemini는 다중 턴 대화를 다르게 처리하므로 지금은 간단히 처리
                user_messages.append(f"Assistant: {msg['content']}")
        
        # 모든 사용자 메시지를 하나로 결합
        prompt = "\n\n".join(user_messages)
        
        return await self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    
    @property
    def provider_name(self) -> str:
        return "Gemini"
    
    @property
    def default_model(self) -> str:
        return self.model