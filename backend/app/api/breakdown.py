"""
要件定義ブレークダウンAPI
"""
from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    BreakdownInitializeRequest,
    BreakdownInitializeResponse,
    BreakdownAnswerRequest,
    BreakdownAnswerResponse,
    BreakdownStatusResponse,
    SessionData,
)
from app.services.breakdown_service import breakdown_service
from app.utils.session_manager import session_manager

router = APIRouter(prefix="/api/breakdown", tags=["breakdown"])


@router.post("/initialize", response_model=BreakdownInitializeResponse)
async def initialize_breakdown(request: BreakdownInitializeRequest):
    """
    要件定義のブレークダウンを初期化
    打ち合わせの記録から要件定義書のたたき台と質問を生成する
    """
    try:
        # セッションを初期化
        session_id, draft_requirements, questions = await breakdown_service.initialize_session(
            request.input_text
        )

        # セッションデータを作成
        session_data = SessionData(
            session_id=session_id,
            input_text=request.input_text,
            requirements=draft_requirements,
            questions=questions,
            answered_questions=[],
            answers={},
            completion_rate=0.0,
        )

        # 充足率を計算
        completion_rate = breakdown_service.calculate_completion_rate(session_data)
        session_data.completion_rate = completion_rate

        # セッションを保存
        session_manager.save_session(session_data)
        session_manager.save_requirements(session_id, draft_requirements)

        return BreakdownInitializeResponse(
            session_id=session_id,
            draft_requirements=draft_requirements,
            questions=questions,
            completion_rate=completion_rate,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"初期化エラー: {str(e)}")


@router.post("/answer", response_model=BreakdownAnswerResponse)
async def answer_question(request: BreakdownAnswerRequest):
    """
    質問への回答を処理し、要件定義書を更新
    """
    try:
        # セッションを読み込み
        session_data = session_manager.load_session(request.session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")

        # 回答を処理
        updated_requirements, new_questions = await breakdown_service.process_answer(
            session_data, request.question_id, request.answer
        )

        # セッションデータを更新
        # 回答済みの質問に移動
        answered_question = next(
            (q for q in session_data.questions if q.id == request.question_id), None
        )
        if answered_question:
            session_data.questions.remove(answered_question)
            session_data.answered_questions.append(answered_question)
            session_data.answers[request.question_id] = request.answer

        # 新しい質問を追加
        session_data.questions.extend(new_questions)

        # 要件定義書を更新
        session_data.requirements = updated_requirements

        # 充足率を再計算
        completion_rate = breakdown_service.calculate_completion_rate(session_data)
        session_data.completion_rate = completion_rate

        # セッションを保存
        session_manager.save_session(session_data)
        session_manager.save_requirements(request.session_id, updated_requirements)

        return BreakdownAnswerResponse(
            updated_requirements=updated_requirements,
            new_questions=new_questions,
            completion_rate=completion_rate,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回答処理エラー: {str(e)}")


@router.get("/status/{session_id}", response_model=BreakdownStatusResponse)
async def get_breakdown_status(session_id: str):
    """
    セッションの状態を取得
    """
    try:
        # セッションを読み込み
        session_data = session_manager.load_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")

        return BreakdownStatusResponse(
            session_id=session_data.session_id,
            requirements=session_data.requirements,
            answered_questions=session_data.answered_questions,
            remaining_questions=session_data.questions,
            completion_rate=session_data.completion_rate,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"状態取得エラー: {str(e)}")
