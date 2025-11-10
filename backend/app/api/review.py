"""
要件定義書レビューAPI
"""
import uuid
from fastapi import APIRouter, HTTPException
from app.models.schemas import ReviewRequest, ReviewResponse
from app.services.review_service import review_service

router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("", response_model=ReviewResponse)
async def review_requirements(request: ReviewRequest):
    """
    要件定義書をレビューし、漏れ・矛盾を指摘
    """
    try:
        # レビューを実行
        issues, scores = await review_service.review_requirements(request.requirements_text)

        # レビューIDを生成
        review_id = str(uuid.uuid4())

        return ReviewResponse(
            review_id=review_id,
            issues=issues,
            completeness_score=scores["completeness_score"],
            consistency_score=scores["consistency_score"],
            quality_score=scores["quality_score"],
            summary=scores["summary"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"レビューエラー: {str(e)}")
