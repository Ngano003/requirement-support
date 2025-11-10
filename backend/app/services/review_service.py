"""
要件定義書レビューサービス
"""
import json
import uuid
from typing import List
from app.models.schemas import ReviewIssue
from app.services.llm_service import llm_service


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
