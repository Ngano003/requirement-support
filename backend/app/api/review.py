"""
要件定義書レビューAPI
"""
import uuid
import logging
from fastapi import APIRouter, HTTPException
from app.models.schemas import ReviewRequest, ReviewResponse, EnhancedReviewResponse
from app.services.review_service import review_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/review", tags=["review"])


@router.post("", response_model=ReviewResponse)
async def review_requirements(request: ReviewRequest):
    """
    要件定義書をレビューし、漏れ・矛盾を指摘（既存のAPI）
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
        logger.error(f"Review error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"レビューエラー: {str(e)}")


@router.post("/enhanced", response_model=EnhancedReviewResponse)
async def review_requirements_enhanced(request: ReviewRequest):
    """
    要件定義書をレビューし、抜け漏れと矛盾を詳細に検出（強化版）

    2段階アプローチ：
    1. 抜け漏れ検出（必須セクション、機能要件の記載不足、非機能要件、暗黙的な抜け漏れ）
    2. 矛盾・不整合検出（セクション間の矛盾、用語の不統一、論理的矛盾）
    """
    try:
        # 強化版レビューを実行
        missing_items, contradictions, summary = await review_service.review_requirements_enhanced(
            request.requirements_text
        )

        # レビューIDを生成
        review_id = str(uuid.uuid4())

        return EnhancedReviewResponse(
            review_id=review_id,
            missing_items=missing_items,
            contradictions=contradictions,
            summary=summary,
        )

    except Exception as e:
        logger.error(f"Enhanced review error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"レビュー処理中にエラーが発生しました: {str(e)}"
        )
