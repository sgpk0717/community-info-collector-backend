from fastapi import APIRouter
from app.api.v1.endpoints import simple_test

api_router = APIRouter()

# 간단한 테스트 엔드포인트만 등록
api_router.include_router(simple_test.router, tags=["simple-test"])