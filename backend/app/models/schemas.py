"""
データモデル定義
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ========== ブレークダウン機能のスキーマ ==========

class BreakdownInitializeRequest(BaseModel):
    """要件定義のブレークダウン初期化リクエスト"""
    input_text: str = Field(..., description="打ち合わせの記録やメモ")
    session_id: Optional[str] = Field(None, description="セッションID（オプション）")


class Question(BaseModel):
    """AIが生成する質問"""
    id: str = Field(..., description="質問ID")
    category: Literal["functional", "non_functional", "constraint", "other"] = Field(
        ..., description="質問のカテゴリ"
    )
    question: str = Field(..., description="質問文")
    priority: Literal["high", "medium", "low"] = Field(..., description="優先度")
    context: Optional[str] = Field(None, description="質問の背景・コンテキスト")


class BreakdownInitializeResponse(BaseModel):
    """要件定義のブレークダウン初期化レスポンス"""
    session_id: str = Field(..., description="セッションID")
    draft_requirements: str = Field(..., description="要件定義書のたたき台（マークダウン形式）")
    questions: List[Question] = Field(..., description="生成された質問リスト")
    completion_rate: float = Field(..., description="要件の充足率（0-100）")
    answered_count: int = Field(default=0, description="回答済みの質問数")
    total_count: int = Field(..., description="総質問数")
    system_message: Optional[str] = Field(None, description="システムメッセージ")


class BreakdownAnswerRequest(BaseModel):
    """質問への回答リクエスト"""
    session_id: str = Field(..., description="セッションID")
    question_id: str = Field(..., description="質問ID")
    answer: str = Field(..., description="ユーザーの回答")


class BreakdownAnswerResponse(BaseModel):
    """質問への回答レスポンス"""
    updated_requirements: str = Field(..., description="更新された要件定義書")
    new_questions: List[Question] = Field(..., description="新たに生成された質問")
    completion_rate: float = Field(..., description="要件の充足率（0-100）")
    all_answered: bool = Field(..., description="全質問に回答済みかどうか")
    answered_count: int = Field(..., description="現在のラウンドで回答済みの質問数")
    total_count: int = Field(..., description="現在のラウンドの総質問数")
    follow_up_question: Optional[str] = Field(None, description="回答が不十分な場合の追加質問")
    answer_accepted: bool = Field(..., description="回答が受け入れられたかどうか")
    system_message: Optional[str] = Field(None, description="システムメッセージ（更新開始）")
    update_summary: Optional[str] = Field(None, description="要件定義書更新の要点")
    next_questions_message: Optional[str] = Field(None, description="次の質問についてのメッセージ")


class BreakdownStatusResponse(BaseModel):
    """ブレークダウンセッションの状態レスポンス"""
    session_id: str = Field(..., description="セッションID")
    requirements: str = Field(..., description="現在の要件定義書")
    answered_questions: List[Question] = Field(..., description="回答済みの質問")
    remaining_questions: List[Question] = Field(..., description="未回答の質問")
    completion_rate: float = Field(..., description="要件の充足率（0-100）")


# ========== レビュー機能のスキーマ ==========

class ReviewRequest(BaseModel):
    """要件定義書レビューリクエスト"""
    requirements_text: str = Field(..., description="要件定義書（マークダウン形式）")


class ReviewIssue(BaseModel):
    """レビューで検出された指摘事項"""
    severity: Literal["high", "medium", "low"] = Field(..., description="重大度")
    category: Literal["missing", "inconsistency", "ambiguity", "quality"] = Field(
        ..., description="指摘のカテゴリ"
    )
    section: str = Field(..., description="該当セクション")
    line: Optional[int] = Field(None, description="該当行番号")
    description: str = Field(..., description="指摘内容の説明")
    suggestion: str = Field(..., description="改善提案")


class ReviewResponse(BaseModel):
    """要件定義書レビューレスポンス"""
    review_id: str = Field(..., description="レビューID")
    issues: List[ReviewIssue] = Field(..., description="指摘事項リスト")
    completeness_score: float = Field(..., description="完全性スコア（0-100）")
    consistency_score: float = Field(..., description="整合性スコア（0-100）")
    quality_score: float = Field(..., description="品質スコア（0-100）")
    summary: str = Field(..., description="レビュー結果のサマリー")


# ========== 内部データモデル ==========

class SessionData(BaseModel):
    """セッションデータ（内部用）"""
    session_id: str
    input_text: str
    requirements: str
    questions: List[Question]
    answered_questions: List[Question]
    answers: dict[str, str]  # question_id -> answer
    completion_rate: float
