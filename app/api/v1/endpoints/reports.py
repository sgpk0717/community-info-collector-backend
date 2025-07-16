from fastapi import APIRouter, HTTPException
from app.services.database_service import DatabaseService
from app.schemas.report import Report, ReportList
from typing import List
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/reports/{user_nickname}", response_model=ReportList)
async def get_user_reports(user_nickname: str):
    """사용자의 보고서 목록 조회"""
    try:
        db_service = DatabaseService()
        reports = await db_service.get_user_reports(user_nickname)
        
        return ReportList(
            reports=reports,
            total=len(reports)
        )
        
    except Exception as e:
        logger.error(f"Error getting reports: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/detail/{report_id}")
async def get_report_detail(report_id: str):
    """보고서 상세 조회 (각주 링크 포함)"""
    try:
        db_service = DatabaseService()
        
        # 보고서 조회
        reports = await db_service.get_user_reports("")
        report = next((r for r in reports if r['id'] == report_id), None)
        
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # 각주 링크 조회
        report_links = await db_service.get_report_links(report_id)
        
        return {
            "report": report,
            "links": report_links
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report detail: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reports/{report_id}/links")
async def get_report_links(report_id: str):
    """보고서 각주 링크 조회"""
    try:
        db_service = DatabaseService()
        links = await db_service.get_report_links(report_id)
        
        return {
            "report_id": report_id,
            "links": links,
            "total": len(links)
        }
        
    except Exception as e:
        logger.error(f"Error getting report links: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))