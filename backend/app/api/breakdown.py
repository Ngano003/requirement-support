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
            answered_count=0,
            total_count=len(questions),
        )

    except Exception as e:
        import traceback
        error_detail = f"初期化エラー: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail=f"初期化エラー: {str(e)}")


@router.post("/answer", response_model=BreakdownAnswerResponse)
async def answer_question(request: BreakdownAnswerRequest):
    """
    質問への回答を処理
    全質問に回答した場合は要件定義書を更新し、新しい質問を生成
    """
    try:
        # セッションを読み込み
        session_data = session_manager.load_session(request.session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")

        # 回答を記録し、妥当性をチェック
        is_valid, follow_up_question = await breakdown_service.process_answer(
            session_data, request.question_id, request.answer
        )

        # 回答が不十分な場合、追加質問を返す
        if not is_valid:
            # セッションを保存
            session_manager.save_session(session_data)

            return BreakdownAnswerResponse(
                updated_requirements=session_data.requirements,
                new_questions=[],
                completion_rate=session_data.completion_rate,
                all_answered=False,
                answered_count=len(session_data.answered_questions),
                total_count=len(session_data.answered_questions) + len(session_data.questions),
                follow_up_question=follow_up_question,
                answer_accepted=False,
            )

        # 充足率を再計算
        completion_rate = breakdown_service.calculate_completion_rate(session_data)
        session_data.completion_rate = completion_rate

        # 全質問に回答したかチェック
        all_answered = len(session_data.questions) == 0
        updated_requirements = session_data.requirements
        new_questions = []

        if all_answered:
            # 要件定義書を一括更新
            updated_requirements = await breakdown_service.update_requirements_with_all_answers(
                session_data
            )
            session_data.requirements = updated_requirements

            # 新しい質問を生成
            new_questions = await breakdown_service.generate_next_questions(
                session_data, updated_requirements
            )

            # 新しい質問を追加
            session_data.questions.extend(new_questions)

            # 回答済み質問をクリアして次のラウンドへ
            session_data.answered_questions = []
            session_data.answers = {}

            # 充足率を再計算
            completion_rate = breakdown_service.calculate_completion_rate(session_data)
            session_data.completion_rate = completion_rate

            # 要件定義書を保存
            session_manager.save_requirements(request.session_id, updated_requirements)

        # セッションを保存
        session_manager.save_session(session_data)

        # 回答済み数と残り質問数を計算
        total_answered = len(session_data.answered_questions)
        total_questions = total_answered + len(session_data.questions)

        return BreakdownAnswerResponse(
            updated_requirements=updated_requirements,
            new_questions=new_questions,
            completion_rate=completion_rate,
            all_answered=all_answered,
            answered_count=total_answered,
            total_count=total_questions,
            follow_up_question=None,
            answer_accepted=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"回答処理エラー: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
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
