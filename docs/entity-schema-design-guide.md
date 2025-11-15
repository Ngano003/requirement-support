# エンティティスキーマ設計ガイド

## 目次

1. [なぜエンティティスキーマが重要か](#なぜエンティティスキーマが重要か)
2. [スキーマ設計の3原則](#スキーマ設計の3原則)
3. [要件定義用エンティティスキーマ](#要件定義用エンティティスキーマ)
4. [リレーションシップスキーマ](#リレーションシップスキーマ)
5. [LlamaIndexへの組み込み](#llamaindexへの組み込み)
6. [実装例](#実装例)
7. [検証とチューニング](#検証とチューニング)

---

## なぜエンティティスキーマが重要か

### 問題：スキーマがないと何が起きるか

```python
# ❌ スキーマなしでLLMに任せた場合
index = PropertyGraphIndex.from_documents([doc], llm=llm)

# 結果：不安定な抽出
# - 「ユーザー」が User, Actor, Person, Stakeholder とバラバラ
# - 「機能」が Function, Feature, Capability と混在
# - 「依存関係」が depends, requires, needs と不統一
# → グラフクエリが書けない！
```

### 解決：スキーマを定義すると

```python
# ✅ スキーマを定義
schema = EntitySchema(
    entity_types=["Requirement", "Function", "Data", "User", "Constraint"],
    relation_types=["DEPENDS_ON", "USES", "REQUIRES", "IMPLEMENTS"]
)

# 結果：安定した抽出
# - すべて統一された用語で抽出
# - Cypherクエリが確実に動作
# - グラフの品質が向上
```

### スキーマの役割

1. **LLMへのガイド**: 「何を抽出すべきか」を明示
2. **用語の統一**: エンティティ名・リレーション名を統一
3. **クエリの安定性**: Cypherクエリが確実に動作
4. **プロパティの標準化**: 必須プロパティを強制

---

## スキーマ設計の3原則

### 原則1: ドメイン駆動設計（DDD）

要件定義という**ドメインの言語**でスキーマを設計します。

**良い例**:
- ✅ `Requirement`（要件）
- ✅ `Function`（機能）
- ✅ `Constraint`（制約）

**悪い例**:
- ❌ `Thing`（抽象的すぎ）
- ❌ `Object`（何でも入ってしまう）
- ❌ `Entity`（メタな用語）

### 原則2: 粒度の一貫性

エンティティの**抽象度レベルを揃える**。

**良い例**（同じレベル）:
```
Requirement（要件）
 └─ Function（機能）
     └─ Data（データ）
```

**悪い例**（レベルが混在）:
```
Requirement（要件）← 抽象的
 └─ LoginButton（ログインボタン）← 具体的すぎ
```

### 原則3: 最小限主義

**必要最小限のエンティティ型**から始めて、必要に応じて拡張。

**推奨**: 5-7種類のエンティティ型
**非推奨**: 20種類以上（複雑すぎて管理不能）

---

## 要件定義用エンティティスキーマ

### コアエンティティ（5種類）

#### 1. Requirement（要件）

**定義**: システムが満たすべき条件・仕様

**プロパティ**:

```python
class RequirementEntity:
    # 必須プロパティ
    id: str                    # 例: "REQ-001"
    title: str                 # 例: "ユーザー認証機能"
    description: str           # 詳細説明
    type: RequirementType      # "functional" | "non_functional"

    # オプショナル
    priority: Priority         # "high" | "medium" | "low"
    source_section: str        # 例: "機能要件"
    status: str                # "draft" | "approved" | "implemented"
    tags: List[str]            # ["認証", "セキュリティ"]
```

**抽出ルール**:
- 「〜機能」「〜要件」「〜できること」で終わる文
- 番号付きリスト内の項目
- 「システムは〜」で始まる文

**抽出例**:

```markdown
## 機能要件

### FR-001: ユーザー認証機能
システムは、メールアドレスとパスワードによるユーザー認証を提供すること。

→ Requirement {
    id: "REQ-001",
    title: "ユーザー認証機能",
    description: "メールアドレスとパスワードによるユーザー認証",
    type: "functional",
    source_section: "機能要件"
}
```

#### 2. Function（機能）

**定義**: システムが提供する具体的な機能・操作

**プロパティ**:

```python
class FunctionEntity:
    # 必須
    id: str                    # 例: "FUNC-001"
    name: str                  # 例: "ログイン"
    description: str           # 処理内容

    # オプショナル
    actor: str                 # 誰が使うか（例: "一般ユーザー"）
    inputs: List[str]          # 入力（例: ["メールアドレス", "パスワード"]）
    outputs: List[str]         # 出力（例: ["ログイン結果", "セッショントークン"]）
    preconditions: List[str]   # 前提条件
    postconditions: List[str]  # 事後条件
```

**抽出ルール**:
- 動詞で終わる機能名（「ログイン」「検索」「登録」）
- 「ユーザーは〜できる」形式の文
- ユースケースのタイトル

**抽出例**:

```markdown
### ログイン機能
ユーザーはメールアドレスとパスワードを入力してログインできる。

→ Function {
    id: "FUNC-001",
    name: "ログイン",
    description: "メールアドレスとパスワードでログイン",
    actor: "ユーザー",
    inputs: ["メールアドレス", "パスワード"],
    outputs: ["ログイン結果"]
}
```

#### 3. Data（データエンティティ）

**定義**: システムが扱う情報・データ構造

**プロパティ**:

```python
class DataEntity:
    # 必須
    id: str                    # 例: "DATA-001"
    name: str                  # 例: "ユーザー情報"
    description: str           # データの説明

    # オプショナル
    attributes: List[str]      # 属性リスト（例: ["id", "email", "password_hash"]）
    data_type: str             # "master" | "transaction" | "reference"
    persistence: str           # "database" | "cache" | "session"
    sensitivity: str           # "public" | "internal" | "confidential"
```

**抽出ルール**:
- 「〜情報」「〜データ」「〜マスタ」で終わる名詞
- データモデル図内のエンティティ
- データベーステーブル名

**抽出例**:

```markdown
### データ定義

#### ユーザー情報
- id: ユーザーID（自動採番）
- email: メールアドレス
- password_hash: パスワードハッシュ
- created_at: 登録日時

→ Data {
    id: "DATA-001",
    name: "ユーザー情報",
    description: "システムユーザーのマスターデータ",
    attributes: ["id", "email", "password_hash", "created_at"],
    data_type: "master"
}
```

#### 4. User（ユーザー種別・アクター）

**定義**: システムを利用するユーザーの種類・役割

**プロパティ**:

```python
class UserEntity:
    # 必須
    id: str                    # 例: "USER-001"
    name: str                  # 例: "一般ユーザー"
    description: str           # 役割の説明

    # オプショナル
    permissions: List[str]     # 権限（例: ["read", "create"]）
    responsibilities: List[str] # 責務
```

**抽出ルール**:
- 「〜ユーザー」「〜管理者」「〜担当者」
- アクター図内の登場人物
- 「対象ユーザー」セクション内の項目

**抽出例**:

```markdown
## 対象ユーザー

### 一般ユーザー
サービスを利用する一般の利用者。書籍の検索・予約が可能。

→ User {
    id: "USER-001",
    name: "一般ユーザー",
    description: "サービスを利用する一般の利用者",
    permissions: ["read", "create"]
}
```

#### 5. Constraint（制約条件）

**定義**: システムの動作を制限するルール・条件

**プロパティ**:

```python
class ConstraintEntity:
    # 必須
    id: str                    # 例: "CONST-001"
    description: str           # 制約内容
    type: ConstraintType       # "validation" | "business_rule" | "technical"

    # オプショナル
    target: str                # 対象（例: "パスワード"）
    rule: str                  # ルール表現（例: "8文字以上"）
    error_message: str         # エラーメッセージ
```

**抽出ルール**:
- 「〜でなければならない」「〜すること」
- バリデーションルール
- 制約条件セクション内の項目

**抽出例**:

```markdown
### バリデーションルール

- パスワードは8文字以上でなければならない
- メールアドレスは重複不可

→ Constraint {
    id: "CONST-001",
    description: "パスワードは8文字以上でなければならない",
    type: "validation",
    target: "パスワード",
    rule: "8文字以上"
}
```

---

## リレーションシップスキーマ

### コアリレーション（6種類）

#### 1. DEPENDS_ON（依存関係）

**定義**: ある要件・機能が別の要件・機能に依存

**方向**: 依存する側 → 依存される側

**プロパティ**:

```python
class DependsOn:
    reason: str                # 依存理由
    dependency_type: str       # "hard" | "soft"
```

**検出パターン**:
- 「〜が前提」
- 「〜に依存する」
- 「〜の後に実行」
- 「〜が必要」

**例**:

```
(予約管理機能)-[:DEPENDS_ON {reason: "認証が前提"}]->(ユーザー認証機能)
```

#### 2. USES（使用関係）

**定義**: 機能がデータを使用

**方向**: Function → Data

**プロパティ**:

```python
class Uses:
    access_type: str           # "read" | "write" | "read_write"
    frequency: str             # "always" | "sometimes" | "rarely"
```

**検出パターン**:
- 「〜を参照」→ read
- 「〜を更新」→ write
- 「〜に保存」→ write
- 「〜を表示」→ read

**例**:

```
(ログイン機能)-[:USES {access_type: "read"}]->(ユーザー情報)
(ユーザー登録機能)-[:USES {access_type: "write"}]->(ユーザー情報)
```

#### 3. REQUIRES（要求関係）

**定義**: 機能が制約を要求

**方向**: Function → Constraint

**プロパティ**:

```python
class Requires:
    enforcement: str           # "mandatory" | "optional"
```

**検出パターン**:
- 「〜の制約がある」
- 「〜を満たす必要がある」
- バリデーション処理の記述

**例**:

```
(パスワード変更機能)-[:REQUIRES]->(パスワード8文字以上制約)
```

#### 4. IMPLEMENTS（実装関係）

**定義**: 機能が要件を実装

**方向**: Function → Requirement

**プロパティ**:

```python
class Implements:
    coverage: str              # "full" | "partial"
```

**検出パターン**:
- 「〜を実現する」
- 「〜を提供する」
- 要件定義と機能仕様の対応関係

**例**:

```
(ログイン機能)-[:IMPLEMENTS]->(ユーザー認証機能要件)
```

#### 5. USED_BY（利用関係）

**定義**: ユーザーが機能を利用

**方向**: User → Function

**プロパティ**:

```python
class UsedBy:
    usage_frequency: str       # "daily" | "weekly" | "rarely"
```

**検出パターン**:
- 「〜ユーザーは〜できる」
- ユースケース図のアクターと機能の関係

**例**:

```
(一般ユーザー)-[:USES]->(書籍検索機能)
(管理者)-[:USES]->(ユーザー管理機能)
```

#### 6. CONFLICTS_WITH（矛盾関係）

**定義**: 要件同士が矛盾

**方向**: 双方向

**プロパティ**:

```python
class ConflictsWith:
    conflict_type: str         # "logical" | "resource" | "priority"
    severity: str              # "high" | "medium" | "low"
```

**検出パターン**:
- 論理的に両立不可能な要件
- 同じデータに対する矛盾する制約
- リソース競合

**例**:

```
(全データ公開要件)-[:CONFLICTS_WITH {conflict_type: "logical"}]->(認証必須要件)
```

---

## LlamaIndexへの組み込み

### 方法1: スキーマ定義ファイル

```python
# backend/app/schemas/knowledge_graph_schema.py

from typing import List, Literal
from pydantic import BaseModel, Field

# ========== エンティティタイプ定義 ==========

class EntityType(BaseModel):
    """エンティティタイプの定義"""
    name: str                          # 例: "Requirement"
    description: str                   # 説明
    properties: List[str]              # 必須プロパティ
    optional_properties: List[str]     # オプショナルプロパティ
    extraction_patterns: List[str]     # 抽出パターン（正規表現）

# ========== リレーションタイプ定義 ==========

class RelationType(BaseModel):
    """リレーションタイプの定義"""
    name: str                          # 例: "DEPENDS_ON"
    description: str                   # 説明
    source_types: List[str]            # ソースエンティティタイプ
    target_types: List[str]            # ターゲットエンティティタイプ
    properties: List[str]              # プロパティ
    detection_patterns: List[str]      # 検出パターン

# ========== スキーマ定義 ==========

REQUIREMENT_ENTITY_TYPES = [
    EntityType(
        name="Requirement",
        description="システムが満たすべき条件・仕様",
        properties=["id", "title", "description", "type"],
        optional_properties=["priority", "source_section", "status"],
        extraction_patterns=[
            r"(?:機能|要件)[:：]\s*(.+)",
            r"(?:REQ|FR|NFR)-\d+[:：]\s*(.+)",
            r"システムは(.+)すること",
        ]
    ),
    EntityType(
        name="Function",
        description="システムが提供する具体的な機能",
        properties=["id", "name", "description"],
        optional_properties=["actor", "inputs", "outputs"],
        extraction_patterns=[
            r"(.+)機能",
            r"ユーザーは(.+)できる",
            r"(.+)処理",
        ]
    ),
    EntityType(
        name="Data",
        description="システムが扱う情報・データ構造",
        properties=["id", "name", "description"],
        optional_properties=["attributes", "data_type"],
        extraction_patterns=[
            r"(.+)(?:情報|データ|マスタ)",
            r"テーブル[:：]\s*(.+)",
        ]
    ),
    EntityType(
        name="User",
        description="システムを利用するユーザーの種類",
        properties=["id", "name", "description"],
        optional_properties=["permissions"],
        extraction_patterns=[
            r"(.+)(?:ユーザー|管理者|担当者)",
            r"アクター[:：]\s*(.+)",
        ]
    ),
    EntityType(
        name="Constraint",
        description="システムの動作を制限するルール",
        properties=["id", "description", "type"],
        optional_properties=["target", "rule"],
        extraction_patterns=[
            r"(.+)(?:でなければならない|すること)",
            r"制約[:：]\s*(.+)",
        ]
    ),
]

REQUIREMENT_RELATION_TYPES = [
    RelationType(
        name="DEPENDS_ON",
        description="依存関係",
        source_types=["Requirement", "Function"],
        target_types=["Requirement", "Function"],
        properties=["reason"],
        detection_patterns=[
            "が前提",
            "に依存",
            "が必要",
            "の後に",
        ]
    ),
    RelationType(
        name="USES",
        description="使用関係",
        source_types=["Function"],
        target_types=["Data"],
        properties=["access_type"],
        detection_patterns=[
            "を参照",
            "を更新",
            "に保存",
            "を表示",
            "にアクセス",
        ]
    ),
    RelationType(
        name="REQUIRES",
        description="要求関係",
        source_types=["Function"],
        target_types=["Constraint"],
        properties=[],
        detection_patterns=[
            "を満たす",
            "の制約",
            "に従う",
        ]
    ),
    RelationType(
        name="IMPLEMENTS",
        description="実装関係",
        source_types=["Function"],
        target_types=["Requirement"],
        properties=["coverage"],
        detection_patterns=[
            "を実現",
            "を提供",
            "を満たす",
        ]
    ),
    RelationType(
        name="USED_BY",
        description="利用関係",
        source_types=["User"],
        target_types=["Function"],
        properties=[],
        detection_patterns=[
            "は.*できる",
            "が使用",
            "が利用",
        ]
    ),
]
```

### 方法2: プロンプトテンプレート

スキーマをLLMに渡すプロンプトテンプレート：

```python
# backend/app/prompts/entity_extraction_prompt.py

ENTITY_EXTRACTION_PROMPT_TEMPLATE = """
あなたは要件定義書から構造化されたエンティティとリレーションシップを抽出する専門家です。

【エンティティタイプ】
{entity_types_description}

【リレーションタイプ】
{relation_types_description}

【抽出ルール】
1. 各エンティティには一意のIDを付与（例: REQ-001, FUNC-001）
2. エンティティタイプは上記の5種類のみ使用
3. リレーションタイプは上記の5種類のみ使用
4. プロパティは必須項目を必ず含める

【要件定義書】
{requirements_text}

【出力形式】
以下のJSON形式で出力してください：

```json
{{
  "entities": [
    {{
      "type": "Requirement",
      "id": "REQ-001",
      "properties": {{
        "title": "ユーザー認証機能",
        "description": "...",
        "type": "functional"
      }}
    }}
  ],
  "relations": [
    {{
      "type": "DEPENDS_ON",
      "source_id": "REQ-002",
      "target_id": "REQ-001",
      "properties": {{
        "reason": "認証が前提"
      }}
    }}
  ]
}}
```

JSON形式のみを出力してください。
"""

def build_entity_extraction_prompt(
    requirements_text: str,
    entity_types: List[EntityType],
    relation_types: List[RelationType]
) -> str:
    """エンティティ抽出プロンプトを構築"""

    # エンティティタイプの説明を生成
    entity_descriptions = []
    for et in entity_types:
        desc = f"- **{et.name}**: {et.description}\n"
        desc += f"  必須プロパティ: {', '.join(et.properties)}\n"
        desc += f"  抽出パターン: {', '.join(et.extraction_patterns[:3])}"
        entity_descriptions.append(desc)

    # リレーションタイプの説明を生成
    relation_descriptions = []
    for rt in relation_types:
        desc = f"- **{rt.name}**: {rt.description}\n"
        desc += f"  方向: {' | '.join(rt.source_types)} → {' | '.join(rt.target_types)}\n"
        desc += f"  検出パターン: {', '.join(rt.detection_patterns[:3])}"
        relation_descriptions.append(desc)

    return ENTITY_EXTRACTION_PROMPT_TEMPLATE.format(
        entity_types_description="\n".join(entity_descriptions),
        relation_types_description="\n".join(relation_descriptions),
        requirements_text=requirements_text
    )
```

---

## 実装例

### カスタムエンティティ抽出器

```python
# backend/app/services/entity_extractor.py

import json
import logging
from typing import List, Dict, Any
from app.schemas.knowledge_graph_schema import (
    REQUIREMENT_ENTITY_TYPES,
    REQUIREMENT_RELATION_TYPES,
)
from app.prompts.entity_extraction_prompt import build_entity_extraction_prompt
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class RequirementEntityExtractor:
    """要件定義専用エンティティ抽出器"""

    def __init__(self):
        self.entity_types = REQUIREMENT_ENTITY_TYPES
        self.relation_types = REQUIREMENT_RELATION_TYPES

    async def extract(self, requirements_text: str) -> Dict[str, Any]:
        """
        要件定義書からエンティティとリレーションを抽出

        Args:
            requirements_text: 要件定義書

        Returns:
            {"entities": [...], "relations": [...]}
        """
        # プロンプト構築
        prompt = build_entity_extraction_prompt(
            requirements_text=requirements_text,
            entity_types=self.entity_types,
            relation_types=self.relation_types,
        )

        # LLMで抽出
        response = await llm_service.generate_with_system_prompt(
            system_prompt="あなたは要件定義書から構造化されたエンティティを抽出する専門家です。",
            user_prompt=prompt,
            temperature=0.2,  # 一貫性のため低め
        )

        # JSONパース
        data = self._parse_json(response)

        # バリデーション
        validated = self._validate_entities_and_relations(data)

        return validated

    def _parse_json(self, json_str: str) -> dict:
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

    def _validate_entities_and_relations(self, data: dict) -> dict:
        """エンティティとリレーションをバリデーション"""
        validated_entities = []
        validated_relations = []

        # エンティティのバリデーション
        for entity in data.get("entities", []):
            if self._is_valid_entity(entity):
                validated_entities.append(entity)
            else:
                logger.warning(f"Invalid entity: {entity}")

        # リレーションのバリデーション
        entity_ids = {e["id"] for e in validated_entities}
        for relation in data.get("relations", []):
            if self._is_valid_relation(relation, entity_ids):
                validated_relations.append(relation)
            else:
                logger.warning(f"Invalid relation: {relation}")

        return {
            "entities": validated_entities,
            "relations": validated_relations,
        }

    def _is_valid_entity(self, entity: dict) -> bool:
        """エンティティが有効かチェック"""
        # 必須フィールドチェック
        if not all(k in entity for k in ["type", "id", "properties"]):
            return False

        # エンティティタイプチェック
        valid_types = [et.name for et in self.entity_types]
        if entity["type"] not in valid_types:
            return False

        # 必須プロパティチェック
        entity_type_def = next(
            (et for et in self.entity_types if et.name == entity["type"]),
            None
        )
        if entity_type_def:
            required_props = entity_type_def.properties
            if not all(p in entity["properties"] for p in required_props):
                return False

        return True

    def _is_valid_relation(self, relation: dict, entity_ids: set) -> bool:
        """リレーションが有効かチェック"""
        # 必須フィールドチェック
        if not all(k in relation for k in ["type", "source_id", "target_id"]):
            return False

        # リレーションタイプチェック
        valid_types = [rt.name for rt in self.relation_types]
        if relation["type"] not in valid_types:
            return False

        # エンティティ存在チェック
        if relation["source_id"] not in entity_ids:
            return False
        if relation["target_id"] not in entity_ids:
            return False

        return True


# シングルトンインスタンス
entity_extractor = RequirementEntityExtractor()
```

---

## 検証とチューニング

### 抽出品質の評価指標

1. **精度（Precision）**: 抽出されたエンティティが正しい割合
2. **再現率（Recall）**: 本来抽出されるべきエンティティが抽出された割合
3. **F1スコア**: 精度と再現率の調和平均

### チューニング手順

#### ステップ1: サンプルで評価

```python
# テスト用サンプル
sample_requirements = """
# システム概要
書籍予約システム

## 機能要件
### FR-001: ログイン機能
ユーザーはメールアドレスとパスワードでログインできる。
"""

# 抽出実行
result = await entity_extractor.extract(sample_requirements)

# 評価
print(f"抽出されたエンティティ数: {len(result['entities'])}")
print(f"抽出されたリレーション数: {len(result['relations'])}")

# 期待値と比較
expected_entities = 3  # Requirement, Function, Data
actual_entities = len(result['entities'])
recall = actual_entities / expected_entities
print(f"再現率: {recall:.2%}")
```

#### ステップ2: パターンの調整

抽出漏れがある場合、`extraction_patterns`を追加：

```python
EntityType(
    name="Function",
    extraction_patterns=[
        r"(.+)機能",
        r"ユーザーは(.+)できる",
        r"(.+)処理",
        # 新規追加
        r"(.+)操作",
        r"(.+)画面",
    ]
)
```

#### ステップ3: プロンプトの改善

抽出精度が低い場合、プロンプトに例を追加：

```python
ENTITY_EXTRACTION_PROMPT_TEMPLATE = """
...

【抽出例】

入力:
「ユーザーはメールアドレスとパスワードでログインできる」

出力:
{{
  "entities": [
    {{
      "type": "Function",
      "id": "FUNC-001",
      "properties": {{
        "name": "ログイン",
        "description": "メールアドレスとパスワードでログイン",
        "inputs": ["メールアドレス", "パスワード"]
      }}
    }}
  ]
}}

...
"""
```

---

## まとめ

### エンティティスキーマ設計のチェックリスト

- [ ] **ドメイン駆動**: 要件定義の用語を使用
- [ ] **粒度の一貫性**: 同じ抽象レベルのエンティティ
- [ ] **最小限**: 5-7種類から始める
- [ ] **明確なプロパティ**: 必須・オプショナルを定義
- [ ] **抽出パターン**: 正規表現で具体的に
- [ ] **バリデーション**: 抽出後に検証
- [ ] **反復改善**: サンプルで評価→調整

### 次のステップ

1. スキーマファイルを作成（`knowledge_graph_schema.py`）
2. プロンプトテンプレートを実装
3. カスタム抽出器を実装
4. サンプルで評価
5. チューニング

スキーマ設計は**GraphRAGの成否の8割を決める**重要なステップです。慎重に設計し、反復的に改善していくことが成功の鍵です。
