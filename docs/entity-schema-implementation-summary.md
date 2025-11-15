# エンティティスキーマ実装サマリー

## 📦 実装済みコンポーネント

### 1. スキーマ定義
**ファイル**: `backend/app/schemas/knowledge_graph_schema.py`

#### 4つのノード（エンティティ）

| エンティティ | 説明 | 必須プロパティ | 抽出パターン例 |
|------------|------|--------------|--------------|
| **Actor** | システムを利用する人、役割、外部システム | `name` | 〜ユーザー、〜管理者 |
| **Function** | システムが提供する機能・ユースケース | `name` | 〜機能、ユーザーは〜できる |
| **Data** | 扱う情報、DBテーブル、データエンティティ | `name` | 〜情報、〜データ、〜マスタ |
| **Requirement** | 機能/非機能要件、ルール、制約 | `name`, `type` | 〜要件、〜しなければならない |

#### 5つのエッジ（リレーション）

| リレーション | 方向 | プロパティ | 検出可能な問題 |
|------------|------|----------|--------------|
| **USES** | Actor → Function | - | 利用されない機能の検出 |
| **MANIPULATES** | Function → Data | `action` (Read/Write/Delete) | データアクセス矛盾の検出 |
| **DEPENDS_ON** | Function → Function | - | 循環依存の検出 |
| **APPLIES_TO** | Requirement → Function/Data | - | セキュリティ要件漏れの検出 |
| **AUTHORIZES** | Actor → Function | `permission` (Allow/Deny) | 権限競合の検出 |

#### Requirement のサブタイプ

```python
class RequirementTypeEnum:
    FUNCTIONAL = "Functional"              # 機能要件
    SECURITY = "Security"                  # セキュリティ要件
    PERFORMANCE = "Performance"            # 性能要件
    AVAILABILITY = "Availability"          # 可用性要件
    MAINTAINABILITY = "Maintainability"    # 保守性要件
    BUSINESS_RULE = "BusinessRule"         # ビジネスルール
    CONSTRAINT = "Constraint"              # 制約条件
```

---

### 2. プロンプトテンプレート
**ファイル**: `backend/app/prompts/entity_extraction_prompt.py`

#### 主要機能

- **エンティティ抽出プロンプト生成**: `build_entity_extraction_prompt()`
- **リレーション推論プロンプト生成**: `build_relation_inference_prompt()`（オプショナル）

#### プロンプトの特徴

1. **スキーマベース**: knowledge_graph_schema.py から自動生成
2. **具体例付き**: LLMの抽出精度を向上
3. **構造化出力**: JSON形式を強制

#### 例

```python
from app.prompts.entity_extraction_prompt import build_entity_extraction_prompt

prompt = build_entity_extraction_prompt(requirements_text)
# → LLMに渡すプロンプトが生成される
```

---

### 3. エンティティ抽出器
**ファイル**: `backend/app/services/entity_extractor.py`

#### 主要機能

```python
from app.services.entity_extractor import entity_extractor

# エンティティとリレーションを抽出
result = await entity_extractor.extract(requirements_text)

# 結果
{
    "entities": [
        {
            "type": "Actor",
            "id": "ACTOR-001",
            "properties": {"name": "一般ユーザー"}
        },
        ...
    ],
    "relations": [
        {
            "type": "USES",
            "source_id": "ACTOR-001",
            "target_id": "FUNC-001",
            "properties": {}
        },
        ...
    ],
    "validation_errors": [...]  # バリデーションエラーログ
}
```

#### バリデーション機能

- ✅ エンティティタイプの検証
- ✅ 必須プロパティの検証
- ✅ リレーションの整合性検証（source/targetの存在確認）
- ✅ 不正なデータの自動除外

---

## 🎯 検出可能な問題

### ヌケモレ検出

#### 1. 利用されない機能

**Cypherクエリ**:
```cypher
MATCH (f:Function)
WHERE NOT EXISTS {
    MATCH (a:Actor)-[:USES]->(f)
}
RETURN f.name AS function_name
```

**意味**: どのActorからもUSESされていないFunctionを検出

---

#### 2. セキュリティ要件の漏れ

**Cypherクエリ**:
```cypher
MATCH (d:Data)
WHERE (d.name CONTAINS '個人情報' OR d.name CONTAINS '決済情報' OR d.sensitivity = 'confidential')
AND NOT EXISTS {
    MATCH (r:Requirement {type: 'Security'})-[:APPLIES_TO]->(d)
}
RETURN d.name AS data_name
```

**意味**: 機密データにセキュリティ要件が適用されていない場合を検出

---

#### 3. 孤立データ

**Cypherクエリ**:
```cypher
MATCH (d:Data)
WHERE NOT EXISTS {
    MATCH (f:Function)-[:MANIPULATES]->(d)
}
RETURN d.name AS data_name
```

**意味**: どのFunctionからもMANIPULATESされていないDataを検出

---

### 矛盾検出

#### 1. 循環依存

**Cypherクエリ**:
```cypher
MATCH path = (f1:Function)-[:DEPENDS_ON*]->(f1)
RETURN f1.name AS function_name,
       [n IN nodes(path) | n.name] AS cycle_path
```

**意味**: DEPENDS_ONのループを検出（実装順序が決められない）

---

#### 2. 権限の競合

**Cypherクエリ**:
```cypher
MATCH (a:Actor)-[r1:AUTHORIZES {permission: 'Allow'}]->(f:Function),
      (a)-[r2:AUTHORIZES {permission: 'Deny'}]->(f)
RETURN a.name AS actor_name,
       f.name AS function_name,
       'Permission conflict' AS conflict_type
```

**意味**: 同一ActorがAllowとDenyの両方を持つ矛盾を検出

---

#### 3. データアクセスの矛盾

**Cypherクエリ**:
```cypher
MATCH (f1:Function)-[m1:MANIPULATES {action: 'Write'}]->(d:Data),
      (f2:Function)-[m2:MANIPULATES {action: 'Write'}]->(d)
WHERE f1.name <> f2.name
AND NOT EXISTS {
    MATCH (f1)-[:DEPENDS_ON]->(f2)
    UNION
    MATCH (f2)-[:DEPENDS_ON]->(f1)
}
RETURN d.name AS data_name,
       f1.name AS function1,
       f2.name AS function2
```

**意味**: 依存関係なしに複数FunctionがWriteする矛盾を検出

---

## 🚀 使い方

### ステップ1: エンティティ抽出

```python
from app.services.entity_extractor import entity_extractor

requirements_text = """
## 対象ユーザー
- 一般ユーザー: 書籍の検索が可能
- 管理者: ユーザー管理が可能

## 機能要件
### ログイン機能
ユーザーはメールアドレスとパスワードでログインできる。
ユーザー情報を参照してログイン認証を行う。

## 非機能要件
ユーザー情報は暗号化して保存すること。
"""

# 抽出実行
result = await entity_extractor.extract(requirements_text)

print(f"抽出されたエンティティ: {len(result['entities'])}")
print(f"抽出されたリレーション: {len(result['relations'])}")
```

### ステップ2: Memgraphに保存

```python
from app.services.graphrag_service import graphrag_service

# Memgraphにノードとエッジを作成
await graphrag_service.create_graph(
    session_id="session-001",
    entities=result['entities'],
    relations=result['relations']
)
```

### ステップ3: 問題検出

```python
# ヌケモレ検出
unused_functions = await graphrag_service.detect_unused_functions("session-001")
missing_security = await graphrag_service.detect_missing_security_requirements("session-001")

# 矛盾検出
circular_deps = await graphrag_service.detect_circular_dependencies("session-001")
permission_conflicts = await graphrag_service.detect_permission_conflicts("session-001")
```

---

## 📊 抽出品質の評価

### 評価方法

1. **サンプル要件定義でテスト**
2. **期待値と実際の抽出結果を比較**
3. **精度・再現率を計算**

### チューニング

#### パターンの追加

```python
# backend/app/schemas/knowledge_graph_schema.py

EntityType(
    name="Function",
    extraction_patterns=[
        "〜機能",
        "〜処理",
        # 新規追加
        "〜画面",
        "〜API",
    ]
)
```

#### プロンプトの改善

```python
# backend/app/prompts/entity_extraction_prompt.py

# 抽出例を追加してLLMの精度を向上
```

---

## 🎓 スキーマ設計のベストプラクティス

### 1. ドメイン駆動設計

✅ 良い例:
- `Actor`, `Function`, `Data`, `Requirement`（要件定義の用語）

❌ 悪い例:
- `Thing`, `Object`, `Entity`（抽象的すぎ）

### 2. 粒度の一貫性

✅ 良い例:
```
Actor → Function → Data
（同じ抽象レベル）
```

❌ 悪い例:
```
Actor → LoginButton → Database
（レベルが混在）
```

### 3. 最小限主義

- ✅ **4-6種類のエンティティ**から始める
- ❌ 最初から20種類は作らない

### 4. プロパティの明確化

✅ 良い例:
```python
required_properties=["name", "type"]
optional_properties=["description", "priority"]
```

❌ 悪い例:
```python
properties=["stuff"]  # 曖昧
```

---

## 🔧 トラブルシューティング

### 問題: エンティティが抽出されない

**原因**: 抽出パターンがマッチしていない

**解決策**:
```python
# extraction_patterns に新しいパターンを追加
EntityType(
    extraction_patterns=[
        "〜機能",
        "〜処理",
        "〜する",  # 追加
    ]
)
```

---

### 問題: リレーションが抽出されない

**原因**: detection_patterns がマッチしていない

**解決策**:
```python
# detection_patterns に新しいパターンを追加
RelationType(
    detection_patterns=[
        "を参照",
        "にアクセス",  # 追加
    ]
)
```

---

### 問題: JSON parse error

**原因**: LLMがJSON形式以外を出力

**解決策**:
```python
# プロンプトに「JSON形式のみ」を強調
# temperature を下げる（0.1-0.2）
```

---

## 📚 次のステップ

1. ✅ スキーマ定義完了
2. ✅ プロンプト作成完了
3. ✅ エンティティ抽出器実装完了
4. ⬜ Memgraph統合（GraphRAGService実装）
5. ⬜ 検出クエリ実装
6. ⬜ API統合
7. ⬜ テスト・検証

---

## 🎯 まとめ

### 実装済み

- ✅ **4エンティティ、5リレーション**の実戦的スキーマ
- ✅ **検証機能付き**エンティティ抽出器
- ✅ **Cypher検出クエリ**テンプレート

### このスキーマの強み

1. **実務的**: 要件定義の実態に即している
2. **検出力が高い**: ヌケモレ・矛盾を機械的に発見可能
3. **拡張可能**: 必要に応じてエンティティ/リレーションを追加可能

### 次の実装

[graphrag-detailed-design-memgraph.md](graphrag-detailed-design-memgraph.md) に従って、Memgraph統合を実装します。
