# 要件定義レビュー機能 強化実装 詳細設計書

## 目次

1. [概要](#概要)
2. [フェーズ1: LLMプロンプト実装](#フェーズ1-llmプロンプト実装)
3. [データモデル設計](#データモデル設計)
4. [API設計](#api設計)
5. [サービス層設計](#サービス層設計)
6. [実装タスク](#実装タスク)

---

## 概要

### 目的

現在のレビュー機能は単一のプロンプトで抜け漏れと矛盾を同時に検出していますが、検出精度を向上させるため、以下の2段階アプローチに変更します：

1. **抜け漏れ検出**（Missing Items Check）
2. **矛盾・不整合検出**（Contradiction Check）

### スコープ

**フェーズ1のみ実装**（GraphRAGは含まない）

- LLMによる2段階レビュー（抜け漏れ検出 + 矛盾検出）
- 既存APIとの互換性を保ちつつ、新しいエンドポイントを追加
- 詳細なレビュー結果の構造化

---

## フェーズ1: LLMプロンプト実装

### アーキテクチャ

```
┌─────────────────────────────────────────────┐
│          ReviewService                       │
├─────────────────────────────────────────────┤
│                                             │
│  review_requirements() [既存]                │
│  ├─ 単一プロンプトで全体レビュー              │
│  └─ 既存APIとの互換性を維持                  │
│                                             │
│  review_requirements_enhanced() [新規]       │
│  ├─ Phase 1: 抜け漏れ検出                   │
│  │   └─ _check_missing_items()             │
│  ├─ Phase 2: 矛盾・不整合検出                │
│  │   └─ _check_contradictions()            │
│  └─ Phase 3: 統合レポート生成                │
│      └─ _generate_integrated_report()      │
│                                             │
└─────────────────────────────────────────────┘
```

### 処理フロー

```
[ユーザー] → POST /api/review/enhanced
                    ↓
           [review_requirements_enhanced()]
                    ↓
         ┌──────────┴──────────┐
         ↓                     ↓
 [抜け漏れ検出]          [矛盾検出]
   (並列実行)             (並列実行)
         ↓                     ↓
         └──────────┬──────────┘
                    ↓
          [統合レポート生成]
                    ↓
                [レスポンス]
```

**最適化ポイント**:
- 抜け漏れ検出と矛盾検出は**並列実行**（`asyncio.gather`を使用）
- LLMへの同時リクエスト数を最大2に制限することで処理時間を短縮

---

## データモデル設計

### 1. 抜け漏れ検出の結果モデル

```python
# schemas.py に追加

class MissingSection(BaseModel):
    """欠落しているセクション"""
    section: str = Field(..., description="セクション名")
    severity: Literal["high", "medium", "low"] = Field(..., description="重大度")
    description: str = Field(..., description="説明")
    suggestion: str = Field(..., description="具体的な追加提案")


class MissingFunctionalItem(BaseModel):
    """機能要件の記載不足"""
    function_name: str = Field(..., description="機能名")
    missing_items: List[str] = Field(..., description="不足している項目リスト")
    severity: Literal["high", "medium", "low"] = Field(..., description="重大度")
    suggestion: str = Field(..., description="具体的な追加提案")


class MissingNonFunctionalCategory(BaseModel):
    """非機能要件の欠落カテゴリ"""
    category: str = Field(..., description="カテゴリ名")
    severity: Literal["high", "medium", "low"] = Field(..., description="重大度")
    description: str = Field(..., description="説明")
    suggestion: str = Field(..., description="具体的な追加提案")


class ImplicitMissingItem(BaseModel):
    """暗黙的な抜け漏れ"""
    item: str = Field(..., description="欠落項目")
    reason: str = Field(..., description="なぜ必要と推測されるか")
    severity: Literal["high", "medium", "low"] = Field(..., description="重大度")
    suggestion: str = Field(..., description="具体的な追加提案")


class MissingItemsResult(BaseModel):
    """抜け漏れ検出の結果"""
    missing_sections: List[MissingSection] = Field(default_factory=list)
    missing_functional_items: List[MissingFunctionalItem] = Field(default_factory=list)
    missing_non_functional_categories: List[MissingNonFunctionalCategory] = Field(default_factory=list)
    implicit_missing: List[ImplicitMissingItem] = Field(default_factory=list)
```

### 2. 矛盾・不整合検出の結果モデル

```python
class Evidence(BaseModel):
    """矛盾の証拠"""
    section1_statement: str = Field(..., description="セクション1での記述")
    section2_statement: str = Field(..., description="セクション2での記述")


class CrossSectionContradiction(BaseModel):
    """セクション間の矛盾"""
    type: Literal["section_mismatch", "user_mismatch", "constraint_violation"] = Field(
        ..., description="矛盾のタイプ"
    )
    sections: List[str] = Field(..., description="矛盾が発生しているセクション")
    description: str = Field(..., description="矛盾の具体的な内容")
    evidence: Evidence = Field(..., description="矛盾の証拠")
    severity: Literal["high", "medium", "low"] = Field(..., description="重大度")
    suggestion: str = Field(..., description="矛盾を解消するための提案")


class TerminologyInconsistency(BaseModel):
    """用語の不統一"""
    concept: str = Field(..., description="概念名")
    variations: List[str] = Field(..., description="使用されている用語のバリエーション")
    locations: List[str] = Field(..., description="使用箇所（セクション名）")
    severity: Literal["medium", "low"] = Field(..., description="重大度")
    recommended_term: str = Field(..., description="推奨する統一用語")


class LogicalContradiction(BaseModel):
    """論理的矛盾"""
    contradiction_type: Literal["mutual_exclusive", "constraint_conflict", "data_conflict"] = Field(
        ..., description="矛盾のタイプ"
    )
    requirements: List[str] = Field(..., description="矛盾している要件")
    description: str = Field(..., description="矛盾の内容")
    severity: Literal["high", "medium"] = Field(..., description="重大度")
    suggestion: str = Field(..., description="解決方法")


class ContradictionsResult(BaseModel):
    """矛盾・不整合検出の結果"""
    cross_section_contradictions: List[CrossSectionContradiction] = Field(default_factory=list)
    terminology_inconsistencies: List[TerminologyInconsistency] = Field(default_factory=list)
    logical_contradictions: List[LogicalContradiction] = Field(default_factory=list)
```

### 3. 統合レビュー結果モデル

```python
class EnhancedReviewSummary(BaseModel):
    """統合レビューサマリー"""
    total_missing_items: int = Field(..., description="抜け漏れの総数")
    total_contradictions: int = Field(..., description="矛盾の総数")
    high_severity_count: int = Field(..., description="重大度Highの総数")
    medium_severity_count: int = Field(..., description="重大度Mediumの総数")
    low_severity_count: int = Field(..., description="重大度Lowの総数")
    overall_assessment: str = Field(..., description="全体評価")


class EnhancedReviewResponse(BaseModel):
    """強化版レビューレスポンス"""
    review_id: str = Field(..., description="レビューID")
    missing_items: MissingItemsResult = Field(..., description="抜け漏れ検出結果")
    contradictions: ContradictionsResult = Field(..., description="矛盾検出結果")
    summary: EnhancedReviewSummary = Field(..., description="統合サマリー")
```

---

## API設計

### 既存エンドポイント（互換性維持）

```
POST /api/review
```

**変更なし** - 既存のクライアントとの互換性を保つため、現在の実装を維持します。

### 新規エンドポイント

```
POST /api/review/enhanced
```

**リクエスト**:

```json
{
  "requirements_text": "# システム概要\n..."
}
```

**レスポンス**:

```json
{
  "review_id": "uuid-string",
  "missing_items": {
    "missing_sections": [
      {
        "section": "非機能要件",
        "severity": "high",
        "description": "非機能要件セクションが存在しません",
        "suggestion": "パフォーマンス、セキュリティ、可用性などの非機能要件を追加してください"
      }
    ],
    "missing_functional_items": [
      {
        "function_name": "ログイン機能",
        "missing_items": ["エラーハンドリング", "バリデーションルール"],
        "severity": "medium",
        "suggestion": "パスワード間違い時の処理、入力値チェックのルールを明記してください"
      }
    ],
    "missing_non_functional_categories": [...],
    "implicit_missing": [...]
  },
  "contradictions": {
    "cross_section_contradictions": [
      {
        "type": "section_mismatch",
        "sections": ["システム概要", "機能要件"],
        "description": "システム概要で予約管理システムと記載されているが、機能要件に予約機能が無い",
        "evidence": {
          "section1_statement": "予約管理システム",
          "section2_statement": "ログイン、書籍検索のみ"
        },
        "severity": "high",
        "suggestion": "予約機能を追加するか、システム概要を修正してください"
      }
    ],
    "terminology_inconsistencies": [...],
    "logical_contradictions": [...]
  },
  "summary": {
    "total_missing_items": 12,
    "total_contradictions": 5,
    "high_severity_count": 4,
    "medium_severity_count": 8,
    "low_severity_count": 5,
    "overall_assessment": "重大な抜け漏れと矛盾が複数検出されました。特に非機能要件とエラーハンドリングの記載が不足しています。"
  }
}
```

---

## サービス層設計

### ReviewService の拡張

```python
# backend/app/services/review_service.py

class ReviewService:
    """要件定義書レビューサービス"""

    # プロンプト定義
    SYSTEM_PROMPT = """..."""  # 既存
    MISSING_ITEMS_SYSTEM_PROMPT = """あなたは要件定義のレビュー専門家です。
抜け漏れの検出に特化して分析を行います。"""

    CONTRADICTION_SYSTEM_PROMPT = """あなたは要件定義のレビュー専門家です。
矛盾・不整合の検出に特化して分析を行います。"""

    # 既存メソッド（互換性維持）
    async def review_requirements(self, requirements_text: str) -> tuple[List[ReviewIssue], dict]:
        """既存のレビュー処理（変更なし）"""
        ...

    # 新規メソッド
    async def review_requirements_enhanced(
        self, requirements_text: str
    ) -> tuple[MissingItemsResult, ContradictionsResult, EnhancedReviewSummary]:
        """
        強化版レビュー（2段階アプローチ）

        Returns:
            (missing_items_result, contradictions_result, summary)
        """
        # 並列実行で処理時間を短縮
        missing_items_task = self._check_missing_items(requirements_text)
        contradictions_task = self._check_contradictions(requirements_text)

        missing_items_result, contradictions_result = await asyncio.gather(
            missing_items_task,
            contradictions_task
        )

        # 統合レポートを生成
        summary = self._generate_summary(missing_items_result, contradictions_result)

        return missing_items_result, contradictions_result, summary

    async def _check_missing_items(self, requirements_text: str) -> MissingItemsResult:
        """抜け漏れ検出"""
        prompt = self._build_missing_items_prompt(requirements_text)

        response_json = await llm_service.generate_with_system_prompt(
            system_prompt=self.MISSING_ITEMS_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3,
        )

        data = self._parse_json_response(response_json)
        return MissingItemsResult(**data)

    async def _check_contradictions(self, requirements_text: str) -> ContradictionsResult:
        """矛盾・不整合検出"""
        prompt = self._build_contradiction_prompt(requirements_text)

        response_json = await llm_service.generate_with_system_prompt(
            system_prompt=self.CONTRADICTION_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3,
        )

        data = self._parse_json_response(response_json)
        return ContradictionsResult(**data)

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
      "severity": "high|medium|low",
      "description": "説明",
      "suggestion": "具体的な追加提案"
    }}
  ],
  "missing_functional_items": [
    {{
      "function_name": "機能名",
      "missing_items": ["エラーハンドリング", "バリデーションルール"],
      "severity": "high|medium|low",
      "suggestion": "具体的な追加提案"
    }}
  ],
  "missing_non_functional_categories": [
    {{
      "category": "カテゴリ名",
      "severity": "high|medium|low",
      "description": "説明",
      "suggestion": "具体的な追加提案"
    }}
  ],
  "implicit_missing": [
    {{
      "item": "欠落項目",
      "reason": "なぜ必要と推測されるか",
      "severity": "high|medium|low",
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
      "type": "section_mismatch|user_mismatch|constraint_violation",
      "sections": ["セクション1", "セクション2"],
      "description": "矛盾の具体的な内容",
      "evidence": {{
        "section1_statement": "セクション1での記述",
        "section2_statement": "セクション2での記述"
      }},
      "severity": "high|medium|low",
      "suggestion": "矛盾を解消するための提案"
    }}
  ],
  "terminology_inconsistencies": [
    {{
      "concept": "概念名",
      "variations": ["用語1", "用語2"],
      "locations": ["セクション名"],
      "severity": "medium|low",
      "recommended_term": "推奨する統一用語"
    }}
  ],
  "logical_contradictions": [
    {{
      "contradiction_type": "mutual_exclusive|constraint_conflict|data_conflict",
      "requirements": ["要件A", "要件B"],
      "description": "矛盾の内容",
      "severity": "high|medium",
      "suggestion": "解決方法"
    }}
  ]
}}
```

JSON形式のみを出力してください。
"""

    def _generate_summary(
        self,
        missing_items: MissingItemsResult,
        contradictions: ContradictionsResult
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

        # （他のアイテムも同様にカウント...）

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
            overall_assessment=overall_assessment
        )

    def _generate_overall_assessment(
        self, total_missing: int, total_contradictions: int,
        high_count: int, medium_count: int
    ) -> str:
        """全体評価テキストを生成"""
        if high_count > 3:
            return f"重大な抜け漏れと矛盾が{high_count}件検出されました。要件定義の見直しが必要です。"
        elif high_count > 0:
            return f"重大な問題が{high_count}件検出されました。該当箇所の修正を優先してください。"
        elif medium_count > 5:
            return f"中程度の問題が{medium_count}件検出されました。品質向上のため修正を推奨します。"
        else:
            return "全体的に良好な要件定義です。軽微な改善提案のみです。"

    def _parse_json_response(self, json_str: str) -> dict:
        """JSON文字列をパース（既存の_parse_reviewと同じロジック）"""
        try:
            json_str = json_str.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            json_str = json_str.strip()

            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"JSON string: {json_str}")
            raise
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            raise
```

---

## 実装タスク

### タスク1: データモデル追加（1-2時間）

**ファイル**: `backend/app/models/schemas.py`

- [ ] `MissingSection` モデル追加
- [ ] `MissingFunctionalItem` モデル追加
- [ ] `MissingNonFunctionalCategory` モデル追加
- [ ] `ImplicitMissingItem` モデル追加
- [ ] `MissingItemsResult` モデル追加
- [ ] `Evidence` モデル追加
- [ ] `CrossSectionContradiction` モデル追加
- [ ] `TerminologyInconsistency` モデル追加
- [ ] `LogicalContradiction` モデル追加
- [ ] `ContradictionsResult` モデル追加
- [ ] `EnhancedReviewSummary` モデル追加
- [ ] `EnhancedReviewResponse` モデル追加

### タスク2: ReviewService拡張（3-4時間）

**ファイル**: `backend/app/services/review_service.py`

- [ ] `MISSING_ITEMS_SYSTEM_PROMPT` 定数追加
- [ ] `CONTRADICTION_SYSTEM_PROMPT` 定数追加
- [ ] `review_requirements_enhanced()` メソッド実装
- [ ] `_check_missing_items()` メソッド実装
- [ ] `_check_contradictions()` メソッド実装
- [ ] `_build_missing_items_prompt()` メソッド実装
- [ ] `_build_contradiction_prompt()` メソッド実装
- [ ] `_generate_summary()` メソッド実装
- [ ] `_generate_overall_assessment()` メソッド実装
- [ ] `_parse_json_response()` メソッド実装（既存の_parse_reviewをリファクタ）

### タスク3: API追加（1-2時間）

**ファイル**: `backend/app/api/review.py`

- [ ] `POST /api/review/enhanced` エンドポイント実装
- [ ] リクエスト/レスポンスハンドリング
- [ ] エラーハンドリング

### タスク4: テストコード作成（2-3時間）

**ファイル**: `backend/tests/test_review_enhanced.py`（新規作成）

- [ ] 抜け漏れ検出のユニットテスト
- [ ] 矛盾検出のユニットテスト
- [ ] 統合レポート生成のテスト
- [ ] APIエンドポイントのテスト

### タスク5: サンプルデータでの検証（1時間）

- [ ] 既存のサンプル要件定義書でテスト
- [ ] 意図的に抜け漏れを含むサンプルで検証
- [ ] 意図的に矛盾を含むサンプルで検証

---

## エラーハンドリング

### LLM応答のバリデーション

```python
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

    except json.JSONDecodeError as e:
        # JSONパースエラー → 空の結果を返す
        logger.error(f"Failed to parse missing items JSON: {e}")
        return MissingItemsResult()

    except ValidationError as e:
        # Pydanticバリデーションエラー → 空の結果を返す
        logger.error(f"Invalid missing items data structure: {e}")
        return MissingItemsResult()

    except Exception as e:
        # その他のエラー → 再スロー
        logger.error(f"Unexpected error in _check_missing_items: {e}")
        raise
```

### API層でのエラーハンドリング

```python
@router.post("/enhanced", response_model=EnhancedReviewResponse)
async def review_requirements_enhanced(request: ReviewRequest):
    """強化版レビューAPI"""
    try:
        missing_items, contradictions, summary = \
            await review_service.review_requirements_enhanced(request.requirements_text)

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
            status_code=500,
            detail=f"レビュー処理中にエラーが発生しました: {str(e)}"
        )
```

---

## パフォーマンス最適化

### 並列実行

```python
# 抜け漏れ検出と矛盾検出を並列実行
missing_items_result, contradictions_result = await asyncio.gather(
    self._check_missing_items(requirements_text),
    self._check_contradictions(requirements_text)
)
```

**効果**:
- 逐次実行: 抜け漏れ検出(10秒) + 矛盾検出(10秒) = **20秒**
- 並列実行: max(10秒, 10秒) = **10秒**

### LLMリクエストの最適化

- `temperature=0.3`: 一貫性のある構造化出力を得るため低めに設定
- JSON形式での出力を明示的に指示
- プロンプトに具体例を含めることで精度向上

---

## 今後の拡張（フェーズ2）

GraphRAG実装時には以下を追加します：

```python
# review_service.py に追加

async def review_requirements_with_graph(
    self, requirements_text: str
) -> tuple[MissingItemsResult, ContradictionsResult, GraphAnalysisResult, EnhancedReviewSummary]:
    """
    GraphRAGを使用した強化版レビュー

    Phase 1: LLMレビュー（並列実行）
    Phase 2: GraphRAG分析
    Phase 3: 統合レポート生成
    """
    # Phase 1: LLMレビュー
    missing_items, contradictions, _ = await self.review_requirements_enhanced(requirements_text)

    # Phase 2: GraphRAG分析
    graph_result = await graph_service.analyze_requirements(requirements_text)

    # Phase 3: 統合
    summary = self._generate_integrated_summary(missing_items, contradictions, graph_result)

    return missing_items, contradictions, graph_result, summary
```

---

## まとめ

### 実装スコープ

**フェーズ1のみ**:
- LLMによる2段階レビュー（抜け漏れ + 矛盾）
- 既存APIとの互換性維持
- 新規エンドポイント `/api/review/enhanced`

### 見積もり工数

| タスク | 工数 |
|--------|------|
| データモデル追加 | 1-2時間 |
| ReviewService拡張 | 3-4時間 |
| API追加 | 1-2時間 |
| テストコード | 2-3時間 |
| 検証 | 1時間 |
| **合計** | **8-12時間（1-1.5日）** |

### 次のステップ

1. このドキュメントのレビュー
2. 実装タスクの実行
3. テスト・検証
4. フェーズ2（GraphRAG）の詳細設計へ進む
