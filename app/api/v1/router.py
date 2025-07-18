from fastapi import APIRouter
from app.api.v1.endpoints import search, reports, test, simple_test, users

api_router = APIRouter()

# 모든 엔드포인트 등록
api_router.include_router(search.router, tags=["search"])
api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(test.router, tags=["test"])
api_router.include_router(simple_test.router, tags=["simple-test"])
api_router.include_router(users.router, tags=["users"])