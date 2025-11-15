"""
強化版レビュー機能のテストコード
"""
import pytest
import json
from unittest.mock import AsyncMock, patch
from app.services.review_service import review_service
from app.models.schemas import (
    MissingItemsResult,
    MissingSection,
    ContradictionsResult,
    CrossSectionContradiction,
    Evidence,
    EnhancedReviewSummary,
)


@pytest.fixture
def sample_requirements_text():
    """サンプル要件定義書"""
    return """# システム概要
書籍管理システム

## 機能要件
### ログイン機能
ユーザーがログインできる
"""


@pytest.fixture
def sample_missing_items_response():
    """抜け漏れ検出のサンプルレスポンス"""
    return {
        "missing_sections": [
            {
                "section": "非機能要件",
                "severity": "high",
                "description": "非機能要件セクションが存在しません",
                "suggestion": "パフォーマンス、セキュリティ、可用性などの非機能要件を追加してください",
            }
        ],
        "missing_functional_items": [
            {
                "function_name": "ログイン機能",
                "missing_items": ["エラーハンドリング", "バリデーションルール"],
                "severity": "medium",
                "suggestion": "パスワード間違い時の処理、入力値チェックのルールを明記してください",
            }
        ],
        "missing_non_functional_categories": [],
        "implicit_missing": [],
    }


@pytest.fixture
def sample_contradictions_response():
    """矛盾検出のサンプルレスポンス"""
    return {
        "cross_section_contradictions": [],
        "terminology_inconsistencies": [],
        "logical_contradictions": [],
    }


class TestReviewServiceEnhanced:
    """強化版レビューサービスのテスト"""

    @pytest.mark.asyncio
    async def test_parse_json_response_with_code_block(self):
        """JSONコードブロックを正しくパースできることを確認"""
        json_str = """```json
{
  "missing_sections": [],
  "missing_functional_items": [],
  "missing_non_functional_categories": [],
  "implicit_missing": []
}
```"""
        result = review_service._parse_json_response(json_str)
        assert isinstance(result, dict)
        assert "missing_sections" in result

    @pytest.mark.asyncio
    async def test_parse_json_response_without_code_block(self):
        """コードブロックなしのJSONをパースできることを確認"""
        json_str = """
{
  "missing_sections": [],
  "missing_functional_items": [],
  "missing_non_functional_categories": [],
  "implicit_missing": []
}
"""
        result = review_service._parse_json_response(json_str)
        assert isinstance(result, dict)
        assert "missing_sections" in result

    @pytest.mark.asyncio
    async def test_generate_summary_no_issues(self):
        """問題なしの場合のサマリー生成"""
        missing_items = MissingItemsResult()
        contradictions = ContradictionsResult()

        summary = review_service._generate_summary(missing_items, contradictions)

        assert isinstance(summary, EnhancedReviewSummary)
        assert summary.total_missing_items == 0
        assert summary.total_contradictions == 0
        assert summary.high_severity_count == 0
        assert "良好" in summary.overall_assessment or "問題は検出されません" in summary.overall_assessment

    @pytest.mark.asyncio
    async def test_generate_summary_with_issues(self):
        """問題ありの場合のサマリー生成"""
        missing_items = MissingItemsResult(
            missing_sections=[
                MissingSection(
                    section="非機能要件",
                    severity="high",
                    description="非機能要件セクションが存在しません",
                    suggestion="追加してください",
                )
            ]
        )
        contradictions = ContradictionsResult(
            cross_section_contradictions=[
                CrossSectionContradiction(
                    type="section_mismatch",
                    sections=["システム概要", "機能要件"],
                    description="矛盾があります",
                    evidence=Evidence(
                        section1_statement="予約管理システム",
                        section2_statement="ログイン機能のみ",
                    ),
                    severity="high",
                    suggestion="修正してください",
                )
            ]
        )

        summary = review_service._generate_summary(missing_items, contradictions)

        assert isinstance(summary, EnhancedReviewSummary)
        assert summary.total_missing_items == 1
        assert summary.total_contradictions == 1
        assert summary.high_severity_count == 2
        assert "重大" in summary.overall_assessment

    @pytest.mark.asyncio
    async def test_build_missing_items_prompt(self, sample_requirements_text):
        """抜け漏れ検出用プロンプトの構築を確認"""
        prompt = review_service._build_missing_items_prompt(sample_requirements_text)

        assert "要件定義書" in prompt
        assert sample_requirements_text in prompt
        assert "必須セクション" in prompt
        assert "機能要件" in prompt
        assert "非機能要件" in prompt
        assert "JSON形式" in prompt

    @pytest.mark.asyncio
    async def test_build_contradiction_prompt(self, sample_requirements_text):
        """矛盾検出用プロンプトの構築を確認"""
        prompt = review_service._build_contradiction_prompt(sample_requirements_text)

        assert "要件定義書" in prompt
        assert sample_requirements_text in prompt
        assert "セクション間の矛盾" in prompt
        assert "用語の不統一" in prompt
        assert "論理的矛盾" in prompt
        assert "JSON形式" in prompt

    @pytest.mark.asyncio
    async def test_check_missing_items_success(
        self, sample_requirements_text, sample_missing_items_response
    ):
        """抜け漏れ検出が正常に動作することを確認"""
        with patch(
            "app.services.review_service.llm_service.generate_with_system_prompt"
        ) as mock_llm:
            mock_llm.return_value = json.dumps(sample_missing_items_response)

            result = await review_service._check_missing_items(sample_requirements_text)

            assert isinstance(result, MissingItemsResult)
            assert len(result.missing_sections) == 1
            assert result.missing_sections[0].section == "非機能要件"
            assert len(result.missing_functional_items) == 1
            assert result.missing_functional_items[0].function_name == "ログイン機能"

    @pytest.mark.asyncio
    async def test_check_missing_items_json_error(self, sample_requirements_text):
        """JSONパースエラー時に空の結果を返すことを確認"""
        with patch(
            "app.services.review_service.llm_service.generate_with_system_prompt"
        ) as mock_llm:
            mock_llm.return_value = "invalid json"

            result = await review_service._check_missing_items(sample_requirements_text)

            assert isinstance(result, MissingItemsResult)
            assert len(result.missing_sections) == 0

    @pytest.mark.asyncio
    async def test_check_contradictions_success(
        self, sample_requirements_text, sample_contradictions_response
    ):
        """矛盾検出が正常に動作することを確認"""
        with patch(
            "app.services.review_service.llm_service.generate_with_system_prompt"
        ) as mock_llm:
            mock_llm.return_value = json.dumps(sample_contradictions_response)

            result = await review_service._check_contradictions(sample_requirements_text)

            assert isinstance(result, ContradictionsResult)
            assert len(result.cross_section_contradictions) == 0
            assert len(result.terminology_inconsistencies) == 0
            assert len(result.logical_contradictions) == 0

    @pytest.mark.asyncio
    async def test_review_requirements_enhanced_integration(
        self,
        sample_requirements_text,
        sample_missing_items_response,
        sample_contradictions_response,
    ):
        """強化版レビューの統合テスト"""
        with patch(
            "app.services.review_service.llm_service.generate_with_system_prompt"
        ) as mock_llm:
            # 並列実行されるので、2回のLLM呼び出しに対して異なるレスポンスを返す
            mock_llm.side_effect = [
                json.dumps(sample_missing_items_response),
                json.dumps(sample_contradictions_response),
            ]

            missing_items, contradictions, summary = (
                await review_service.review_requirements_enhanced(sample_requirements_text)
            )

            # 結果の検証
            assert isinstance(missing_items, MissingItemsResult)
            assert isinstance(contradictions, ContradictionsResult)
            assert isinstance(summary, EnhancedReviewSummary)

            assert summary.total_missing_items == 2  # missing_sections(1) + missing_functional_items(1)
            assert summary.total_contradictions == 0
            assert summary.high_severity_count == 1
            assert summary.medium_severity_count == 1

            # LLMが2回呼ばれることを確認
            assert mock_llm.call_count == 2


class TestGenerateOverallAssessment:
    """全体評価テキスト生成のテスト"""

    def test_high_severity_many(self):
        """重大度Highが多い場合"""
        assessment = review_service._generate_overall_assessment(5, 2, 5, 2)
        assert "重大な抜け漏れと矛盾" in assessment
        assert "見直しが必要" in assessment

    def test_high_severity_few(self):
        """重大度Highが少しある場合"""
        assessment = review_service._generate_overall_assessment(3, 1, 2, 1)
        assert "重大な問題" in assessment
        assert "優先" in assessment

    def test_medium_severity_many(self):
        """重大度Mediumが多い場合"""
        assessment = review_service._generate_overall_assessment(6, 2, 0, 8)
        assert "中程度の問題" in assessment
        assert "推奨" in assessment

    def test_no_issues(self):
        """問題なしの場合"""
        assessment = review_service._generate_overall_assessment(0, 0, 0, 0)
        assert "問題は検出されません" in assessment or "良好" in assessment

    def test_low_severity_only(self):
        """軽微な問題のみの場合"""
        assessment = review_service._generate_overall_assessment(2, 1, 0, 3)
        assert "良好" in assessment or "軽微" in assessment
