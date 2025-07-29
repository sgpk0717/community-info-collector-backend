from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from app.schemas.search import SearchRequest, SearchResponse, SearchSource, ReportLength
from app.api.v1.endpoints.search import search_and_analyze

router = APIRouter()

class SimpleSearchRequest(BaseModel):
    """간단한 검색 요청 (Swagger 테스트용)"""
    query: str = "테슬라의 미래"
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "테슬라의 미래"
            }
        }

@router.post("/test/search", response_model=SearchResponse, 
             summary="간단한 키워드 검색 테스트",
             description="키워드만 입력하여 빠르게 테스트할 수 있습니다. 나머지 값은 기본값이 사용됩니다.")
async def test_search(
    request: SimpleSearchRequest,
    background_tasks: BackgroundTasks
):
    """키워드만으로 간단히 검색 테스트"""
    
    # 기본값으로 SearchRequest 생성
    full_request = SearchRequest(
        query=request.query,
        sources=[SearchSource.reddit],
        user_nickname="test_user",
        length=ReportLength.moderate,
        schedule_yn="N"
    )
    
    # 기존 search_and_analyze 함수 호출
    return await search_and_analyze(full_request, background_tasks)