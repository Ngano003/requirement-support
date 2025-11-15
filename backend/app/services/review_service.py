"""
要件定義書レビューサービス
"""
import json
import uuid
import asyncio
import logging
from typing import List, Tuple
from pydantic import ValidationError
from app.models.schemas import (
    ReviewIssue,
    MissingItemsResult,
    MissingSection,
    MissingFunctionalItem,
    MissingNonFunctionalCategory,
    ImplicitMissingItem,
    ContradictionsResult,
    CrossSectionContradiction,
    TerminologyInconsistency,
    LogicalContradiction,
    EnhancedReviewSummary,
    Evidence,
)
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class ReviewService:
    """要件定義書レビューサービス"""

    SYSTEM_PROMPT = """あなたは優秀なシステムエンジニアであり、要件定義のレビューエキスパートです。
要件定義書を分析し、漏れ・矛盾・曖昧な表現を指摘します。

レビューの観点：
1. **必須項目の確認**: システム概要、目的、機能要件、非機能要件などが含まれているか
2. **整合性チェック**: 機能間の矛盾、データの整合性などをチェック
3. **漏れチェック**: エラーハンドリング、セキュリティ、パフォーマンス、バックアップ等の漏れ
4. **品質チェック**: 曖昧な表現、定量化されていない要件の検出

指摘の重大度：
- High: 致命的な漏れや矛盾、セキュリティリスク
- Medium: 重要だが致命的ではない漏れ、明確化が必要な点
- Low: 改善推奨事項、用語の統一など
"""

    MISSING_ITEMS_SYSTEM_PROMPT = """あなたは要件定義のレビュー専門家です。
抜け漏れの検出に特化して分析を行います。

必須セクション、機能要件の記載不足、非機能要件の欠如、暗黙的な抜け漏れを徹底的に検出してください。
"""

    CONTRADICTION_SYSTEM_PROMPT = """あなたは要件定義のレビュー専門家です。
矛盾・不整合の検出に特化して分析を行います。

セクション間の矛盾、用語の不統一、論理的矛盾を徹底的に検出してください。
"""

    async def review_requirements(self, requirements_text: str) -> tuple[List[ReviewIssue], dict]:
        """
        要件定義書をレビュー

        Args:
            requirements_text: 要件定義書（マークダウン形式）

        Returns:
            (issues, scores)
        """
        # レビューを実行
        review_prompt = f"""以下の要件定義書をレビューし、漏れ・矛盾・曖昧な表現を指摘してください。

【要件定義書】
{requirements_text}

【指示】
各指摘について以下の情報を含めてください：
- severity: high, medium, low
- category: missing, inconsistency, ambiguity, quality
- section: 該当セクション名
- line: 該当行番号（推定可能な場合）
- description: 指摘内容の説明
- suggestion: 具体的な改善提案

JSON形式で出力してください：
```json
{{
  "issues": [
    {{
      "severity": "high",
      "category": "missing",
      "section": "セクション名",
      "line": 10,
      "description": "指摘内容",
      "suggestion": "改善提案"
    }}
  ],
  "completeness_score": 75.0,
  "consistency_score": 90.0,
  "quality_score": 80.0,
  "summary": "全体的な評価サマリー"
}}
```

JSON形式で出力してください。他の説明は不要です。
"""

        review_json = await llm_service.generate_with_system_prompt(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=review_prompt,
            temperature=0.3,
        )

        # JSONをパース
        review_data = self._parse_review(review_json)

        issues = [ReviewIssue(**issue) for issue in review_data.get("issues", [])]
        scores = {
            "completeness_score": review_data.get("completeness_score", 0.0),
            "consistency_score": review_data.get("consistency_score", 0.0),
            "quality_score": review_data.get("quality_score", 0.0),
            "summary": review_data.get("summary", ""),
        }

        return issues, scores

    async def review_requirements_enhanced(
        self, requirements_text: str
    ) -> Tuple[MissingItemsResult, ContradictionsResult, EnhancedReviewSummary]:
        """
        強化版レビュー（2段階アプローチ）

        Args:
            requirements_text: 要件定義書（マークダウン形式）

        Returns:
            (missing_items_result, contradictions_result, summary)
        """
        # 並列実行で処理時間を短縮
        missing_items_task = self._check_missing_items(requirements_text)
        contradictions_task = self._check_contradictions(requirements_text)

        missing_items_result, contradictions_result = await asyncio.gather(
            missing_items_task, contradictions_task
        )

        # 統合レポートを生成
        summary = self._generate_summary(missing_items_result, contradictions_result)

        return missing_items_result, contradictions_result, summary

    async def _check_missing_items(self, requirements_text: str) -> MissingItemsResult:
        """抜け漏れ検出"""
        try:
            prompt = self._build_missing_items_prompt(requirements_text)

            response_json = await llm_service.generate_with_system_prompt(
                system_prompt=self.MISSING_ITEMS_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.3,
            )

            data = self._parse_json_response(response_json)

            # Pydanticでバリデーション
            return MissingItemsResult(**data)

        except (json.JSONDecodeError, ValidationError) as e:
            # JSONパースエラーまたはバリデーションエラー → 空の結果を返す
            logger.error(f"Failed to parse missing items response: {e}")
            return MissingItemsResult()

        except Exception as e:
            # その他のエラー → 空の結果を返す
            logger.error(f"Unexpected error in _check_missing_items: {e}", exc_info=True)
            return MissingItemsResult()

    async def _check_contradictions(self, requirements_text: str) -> ContradictionsResult:
        """矛盾・不整合検出"""
        try:
            prompt = self._build_contradiction_prompt(requirements_text)

            response_json = await llm_service.generate_with_system_prompt(
                system_prompt=self.CONTRADICTION_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.3,
            )

            data = self._parse_json_response(response_json)

            # Pydanticでバリデーション
            return ContradictionsResult(**data)

        except (json.JSONDecodeError, ValidationError) as e:
            # JSONパースエラーまたはバリデーションエラー → 空の結果を返す
            logger.error(f"Failed to parse contradictions response: {e}")
            return ContradictionsResult()

        except Exception as e:
            # その他のエラー → 空の結果を返す
            logger.error(f"Unexpected error in _check_contradictions: {e}", exc_info=True)
            return ContradictionsResult()

    def _build_missing_items_prompt(self, requirements_text: str) -> str:
        """抜け漏れ検出用プロンプト構築"""
        return f"""以下の要件定義書を分析し、抜け漏れを検出してください。

【要件定義書】
{requirements_text}

【チェック項目】

## 1. 必須セクションの有無
- [ ] システム概要
- [ ] 目的・背景
- [ ] 対象ユーザー
- [ ] 機能要件
- [ ] 非機能要件
- [ ] 制約条件
- [ ] 前提条件

## 2. 各機能要件に必要な情報
機能要件セクションの各機能について以下が記載されているか：
- [ ] 機能の目的
- [ ] 入力・出力の定義
- [ ] 操作フロー（誰が、何を、どうする）
- [ ] バリデーションルール
- [ ] エラーハンドリング（異常系の処理）

## 3. 非機能要件の網羅性
- [ ] パフォーマンス要件（応答時間、スループット等）
- [ ] セキュリティ要件（認証、暗号化、脆弱性対策等）
- [ ] 可用性要件（稼働時間、障害復旧等）
- [ ] 保守性要件（ログ、監視、バックアップ等）

## 4. 暗黙的な抜け漏れ
文脈から必要と思われるのに記載されていない項目：
- ある機能が言及されているが、前提となる機能が定義されているか
  例: 「ログアウト」があるのに「ログイン」の定義が無い
- 機能で使用されるデータが定義されているか
  例: 「予約情報を表示」と書いてあるのに「予約情報」の定義が無い

【出力形式】
```json
{{
  "missing_sections": [
    {{
      "section": "セクション名",
      "severity": "high",
      "description": "説明",
      "suggestion": "具体的な追加提案"
    }}
  ],
  "missing_functional_items": [
    {{
      "function_name": "機能名",
      "missing_items": ["エラーハンドリング", "バリデーションルール"],
      "severity": "medium",
      "suggestion": "具体的な追加提案"
    }}
  ],
  "missing_non_functional_categories": [
    {{
      "category": "カテゴリ名",
      "severity": "high",
      "description": "説明",
      "suggestion": "具体的な追加提案"
    }}
  ],
  "implicit_missing": [
    {{
      "item": "欠落項目",
      "reason": "なぜ必要と推測されるか",
      "severity": "medium",
      "suggestion": "具体的な追加提案"
    }}
  ]
}}
```

JSON形式のみを出力してください。
"""

    def _build_contradiction_prompt(self, requirements_text: str) -> str:
        """矛盾・不整合検出用プロンプト構築"""
        return f"""以下の要件定義書を分析し、矛盾・不整合を検出してください。

【要件定義書】
{requirements_text}

【チェック観点】

## 1. セクション間の矛盾
- システム概要で言及されている機能が、機能要件で定義されているか
- 対象ユーザーで定義されたユーザー種別が、機能要件で使われているか
- 制約条件と機能要件が両立可能か

例：
❌ システム概要: 「予約管理システム」
   機能要件: ログイン、書籍検索のみ（予約機能が無い）

## 2. 用語の不統一
- 同じ概念が異なる用語で表現されている
  例: 「ユーザー」「利用者」「会員」が混在
- 表記ゆれ
  例: 「ログイン」「ログ イン」「log in」

## 3. 論理的矛盾
- 同時に満たせない要件
  例: 「全データを公開」と「認証ユーザーのみアクセス可」
- 制約の矛盾
  例: 「パスワードは8文字以上」と「パスワードは6文字で固定」
- データの矛盾
  例: 「ユーザーIDは自動採番」と「ユーザーIDは手動入力」

【出力形式】
```json
{{
  "cross_section_contradictions": [
    {{
      "type": "section_mismatch",
      "sections": ["セクション1", "セクション2"],
      "description": "矛盾の具体的な内容",
      "evidence": {{
        "section1_statement": "セクション1での記述",
        "section2_statement": "セクション2での記述"
      }},
      "severity": "high",
      "suggestion": "矛盾を解消するための提案"
    }}
  ],
  "terminology_inconsistencies": [
    {{
      "concept": "概念名",
      "variations": ["用語1", "用語2"],
      "locations": ["セクション名"],
      "severity": "medium",
      "recommended_term": "推奨する統一用語"
    }}
  ],
  "logical_contradictions": [
    {{
      "contradiction_type": "constraint_conflict",
      "requirements": ["要件A", "要件B"],
      "description": "矛盾の内容",
      "severity": "high",
      "suggestion": "解決方法"
    }}
  ]
}}
```

JSON形式のみを出力してください。
"""

    def _generate_summary(
        self, missing_items: MissingItemsResult, contradictions: ContradictionsResult
    ) -> EnhancedReviewSummary:
        """統合サマリーを生成"""
        # 抜け漏れの総数をカウント
        total_missing = (
            len(missing_items.missing_sections)
            + len(missing_items.missing_functional_items)
            + len(missing_items.missing_non_functional_categories)
            + len(missing_items.implicit_missing)
        )

        # 矛盾の総数をカウント
        total_contradictions = (
            len(contradictions.cross_section_contradictions)
            + len(contradictions.terminology_inconsistencies)
            + len(contradictions.logical_contradictions)
        )

        # 重大度別にカウント
        high_count = 0
        medium_count = 0
        low_count = 0

        # 抜け漏れの重大度をカウント
        for item in missing_items.missing_sections:
            if item.severity == "high":
                high_count += 1
            elif item.severity == "medium":
                medium_count += 1
            else:
                low_count += 1

        for item in missing_items.missing_functional_items:
            if item.severity == "high":
                high_count += 1
            elif item.severity == "medium":
                medium_count += 1
            else:
                low_count += 1

        for item in missing_items.missing_non_functional_categories:
            if item.severity == "high":
                high_count += 1
            elif item.severity == "medium":
                medium_count += 1
            else:
                low_count += 1

        for item in missing_items.implicit_missing:
            if item.severity == "high":
                high_count += 1
            elif item.severity == "medium":
                medium_count += 1
            else:
                low_count += 1

        # 矛盾の重大度をカウント
        for item in contradictions.cross_section_contradictions:
            if item.severity == "high":
                high_count += 1
            elif item.severity == "medium":
                medium_count += 1
            else:
                low_count += 1

        for item in contradictions.terminology_inconsistencies:
            if item.severity == "medium":
                medium_count += 1
            else:
                low_count += 1

        for item in contradictions.logical_contradictions:
            if item.severity == "high":
                high_count += 1
            else:
                medium_count += 1

        # 全体評価を生成
        overall_assessment = self._generate_overall_assessment(
            total_missing, total_contradictions, high_count, medium_count
        )

        return EnhancedReviewSummary(
            total_missing_items=total_missing,
            total_contradictions=total_contradictions,
            high_severity_count=high_count,
            medium_severity_count=medium_count,
            low_severity_count=low_count,
            overall_assessment=overall_assessment,
        )

    def _generate_overall_assessment(
        self, total_missing: int, total_contradictions: int, high_count: int, medium_count: int
    ) -> str:
        """全体評価テキストを生成"""
        if high_count > 3:
            return f"重大な抜け漏れと矛盾が{high_count}件検出されました。要件定義の見直しが必要です。"
        elif high_count > 0:
            return f"重大な問題が{high_count}件検出されました。該当箇所の修正を優先してください。"
        elif medium_count > 5:
            return f"中程度の問題が{medium_count}件検出されました。品質向上のため修正を推奨します。"
        elif total_missing + total_contradictions == 0:
            return "問題は検出されませんでした。要件定義書は良好です。"
        else:
            return "全体的に良好な要件定義です。軽微な改善提案のみです。"

    def _parse_json_response(self, json_str: str) -> dict:
        """JSON文字列をパース"""
        json_str = json_str.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()

        return json.loads(json_str)

    def _parse_review(self, json_str: str) -> dict:
        """
        JSON文字列からレビュー結果をパース

        Args:
            json_str: JSON形式の文字列

        Returns:
            レビューデータ
        """
        try:
            # コードブロックを除去
            json_str = json_str.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()

            # JSONをパース
            review_data = json.loads(json_str)

            return review_data

        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"JSON string: {json_str}")
            return {
                "issues": [],
                "completeness_score": 0.0,
                "consistency_score": 0.0,
                "quality_score": 0.0,
                "summary": "レビューの解析に失敗しました",
            }
        except Exception as e:
            print(f"Error parsing review: {e}")
            return {
                "issues": [],
                "completeness_score": 0.0,
                "consistency_score": 0.0,
                "quality_score": 0.0,
                "summary": "レビューの解析に失敗しました",
            }


# シングルトンインスタンス
review_service = ReviewService()
