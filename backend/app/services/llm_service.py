from typing import List, Dict, Any, Optional
from openai import OpenAI
from app.core.exceptions import OpenAIAPIException
from app.schemas.search import ReportLength
import logging
import json

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = OpenAI()
    
    async def translate_to_english(self, query: str) -> str:
        """한글 키워드를 영어로 번역"""
        try:
            prompt = f"""Translate the following Korean keyword to English. 
            If it's already in English, return as is.
            Only return the translated text, nothing else.
            
            Keyword: {query}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "developer", "content": "You are a professional translator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return query  # 실패 시 원본 반환
    
    async def expand_keywords(self, query: str) -> List[str]:
        """주어진 키워드를 확장하여 관련 검색어 생성 (영어)"""
        try:
            # 먼저 영어로 번역
            english_query = await self.translate_to_english(query)
            logger.info(f"Translated query: {query} -> {english_query}")
            
            prompt = f"""Generate 5 related search keywords for: "{english_query}"
            
            Requirements:
            1. All keywords must be in English
            2. Cover different aspects (technical, business, social, future trends)
            3. Be specific and relevant to the original keyword
            4. Return as JSON array only
            
            Example format: ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "developer", "content": "You are a keyword expansion expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 파싱 시도
            try:
                keywords = json.loads(content)
                if isinstance(keywords, list):
                    return keywords[:5]  # 최대 5개
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse keywords JSON: {content}")
            
            # 파싱 실패 시 원본 키워드만 반환
            return []
            
        except Exception as e:
            logger.error(f"OpenAI API error in expand_keywords: {str(e)}")
            return []  # 실패해도 계속 진행
    
    async def generate_report(self, posts: List[Dict[str, Any]], query: str, length: ReportLength) -> Dict[str, Any]:
        """수집된 게시물을 바탕으로 분석 보고서 생성"""
        try:
            # 게시물 정보 포맷팅
            posts_text = self._format_posts_for_prompt(posts[:30])  # 최대 30개 게시물
            
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

**IMPORTANT FOOTNOTE REQUIREMENTS:**
- When referencing specific posts or opinions, add footnotes using [1], [2], [3] format
- Use footnotes for direct quotes, specific claims, or notable opinions
- At the end, provide a "References" section in Korean that lists:
  - **참고 자료**
  - [1] 게시물 1 제목 (r/subreddit)
  - [2] 게시물 2 제목 (r/subreddit)
  - etc.

Important: 
- The input data is in English, but write the ENTIRE report in Korean
- Use markdown format
- Maintain objective and balanced perspective
- Translate key terms appropriately into Korean
- Include footnotes [1], [2], [3] etc. when referencing specific posts
- End with a "References" section mapping footnotes to post information
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "developer", "content": "You are a professional community analyst who creates insightful reports in Korean."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000 if length == ReportLength.detailed else 1000
            )
            
            full_report = response.choices[0].message.content.strip()
            
            # 요약 생성 (한글)
            summary_prompt = f"다음 한국어 보고서의 핵심 내용을 한국어로 2-3문장으로 요약해주세요:\n\n{full_report[:1000]}"
            
            summary_response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "developer", "content": "You are a summarization expert."},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.5,
                max_tokens=200
            )
            
            summary = summary_response.choices[0].message.content.strip()
            
            # 각주 매핑 추출
            footnote_mapping = self._extract_footnote_mapping(full_report, posts)
            
            logger.info(f"🎉 AI 보고서 생성 완료!")
            logger.info(f"   - 전체 보고서: {len(full_report)} 문자")
            logger.info(f"   - 요약: {len(summary)} 문자")
            logger.info(f"   - 각주 수: {len(footnote_mapping)}개")
            
            return {
                "summary": summary,
                "full_report": full_report,
                "footnote_mapping": footnote_mapping
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error in generate_report: {str(e)}")
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
        """보고서에서 각주 매핑 추출"""
        import re
        
        footnote_mapping = []
        
        # 각주 패턴 찾기 [1], [2], [3] 등
        footnote_pattern = r'\[(\d+)\]'
        footnotes = re.findall(footnote_pattern, report)
        
        if not footnotes:
            logger.info("📄 각주가 발견되지 않음")
            return footnote_mapping
        
        logger.info(f"🔗 각주 발견: {footnotes}")
        
        # 각주 번호에 맞는 게시물 매핑
        for footnote_num in set(footnotes):
            footnote_int = int(footnote_num)
            
            # 각주 번호에 맞는 게시물 인덱스 (배열이므로 -1)
            post_index = footnote_int - 1
            
            if 0 <= post_index < len(posts):
                post = posts[post_index]
                footnote_mapping.append({
                    "footnote_number": footnote_int,
                    "post_id": post['id'],
                    "url": post['url'],
                    "title": post['title'],
                    "score": post['score'],
                    "comments": post['num_comments'],
                    "created_utc": post['created_utc'],
                    "subreddit": post['subreddit'],
                    "author": post['author'],
                    "position_in_report": footnote_int
                })
        
        # 각주 번호순으로 정렬
        footnote_mapping.sort(key=lambda x: x['footnote_number'])
        
        logger.info(f"🔗 각주 매핑 완료: {len(footnote_mapping)}개")
        return footnote_mapping