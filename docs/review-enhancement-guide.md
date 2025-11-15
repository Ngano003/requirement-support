# 要件定義レビュー機能 強化ガイド

## 目次

1. [概要](#概要)
2. [プロンプト設計](#プロンプト設計)
3. [GraphRAG活用設計](#graphrag活用設計)
4. [実装ロードマップ](#実装ロードマップ)

---

## 概要

このドキュメントは、要件定義支援AIのレビュー機能を強化するための設計ガイドです。

### レビュー機能の目的

**主要な2つの検出目標**:

1. **抜け漏れの検出**
   - 必須セクションの欠落
   - 記載すべき項目の不足（エラーハンドリング、セキュリティ要件等）
   - 定義されていないデータ・機能・制約
   - 未検証の機能要件

2. **矛盾・不整合の検出**
   - 要件間の論理的矛盾
   - セクション間の不整合（システム概要と機能要件の不一致等）
   - 制約条件の矛盾（同じデータに対する矛盾する制約）
   - 用語の不統一
   - 依存関係の矛盾（循環依存等）

### 強化のアプローチ

- **LLMによるテキスト分析**: 抜け漏れと記述内容の矛盾を検出
- **GraphRAGによる構造分析**: 要件間の関係性から矛盾・循環依存・孤立要件を検出

---

## プロンプト設計

### 1. 抜け漏れ検出プロンプト

```python
MISSING_ITEMS_CHECK_PROMPT = """
あなたは要件定義のレビュー専門家です。
以下の要件定義書を分析し、抜け漏れを検出してください。

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
{
  "missing_sections": [
    {
      "section": "セクション名",
      "severity": "high|medium|low",
      "description": "説明",
      "suggestion": "具体的な追加提案"
    }
  ],
  "missing_functional_items": [
    {
      "function_name": "機能名",
      "missing_items": ["エラーハンドリング", "バリデーションルール"],
      "severity": "high|medium|low",
      "suggestion": "具体的な追加提案"
    }
  ],
  "missing_non_functional_categories": [
    {
      "category": "カテゴリ名",
      "severity": "high|medium|low",
      "description": "説明",
      "suggestion": "具体的な追加提案"
    }
  ],
  "implicit_missing": [
    {
      "item": "欠落項目",
      "reason": "なぜ必要と推測されるか",
      "severity": "high|medium|low",
      "suggestion": "具体的な追加提案"
    }
  ]
}
``

JSON形式のみを出力してください。
"""
```

### 2. 矛盾・不整合検出プロンプト

```python
CONTRADICTION_CHECK_PROMPT = """
あなたは要件定義のレビュー専門家です。
以下の要件定義書を分析し、矛盾・不整合を検出してください。

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
{
  "cross_section_contradictions": [
    {
      "type": "section_mismatch|user_mismatch|constraint_violation",
      "sections": ["セクション1", "セクション2"],
      "description": "矛盾の具体的な内容",
      "evidence": {
        "section1_statement": "セクション1での記述",
        "section2_statement": "セクション2での記述"
      },
      "severity": "high|medium|low",
      "suggestion": "矛盾を解消するための提案"
    }
  ],
  "terminology_inconsistencies": [
    {
      "concept": "概念名",
      "variations": ["用語1", "用語2"],
      "locations": ["セクション名"],
      "severity": "medium|low",
      "recommended_term": "推奨する統一用語"
    }
  ],
  "logical_contradictions": [
    {
      "contradiction_type": "mutual_exclusive|constraint_conflict|data_conflict",
      "requirements": ["要件A", "要件B"],
      "description": "矛盾の内容",
      "severity": "high|medium",
      "suggestion": "解決方法"
    }
  ]
}
``

JSON形式のみを出力してください。
"""
```

### 3. 統合レビュー出力フォーマット

```json
{
  "missing_items": {
    "missing_sections": [...],
    "missing_functional_items": [...],
    "missing_non_functional_categories": [...],
    "implicit_missing": [...]
  },
  "contradictions": {
    "cross_section_contradictions": [...],
    "terminology_inconsistencies": [...],
    "logical_contradictions": [...]
  },
  "summary": {
    "total_missing_items": 12,
    "total_contradictions": 5,
    "high_severity_count": 4,
    "medium_severity_count": 8,
    "low_severity_count": 5,
    "overall_assessment": "抜け漏れと矛盾の概要"
  }
}
```

---

## GraphRAG活用設計

### 基本方針

GraphRAGは **「抜け漏れ検出」** と **「矛盾・不整合検出」** を強化するために使用します。

### アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│    要件定義レビューシステム（2層アーキテクチャ）           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 1: LLMによるテキスト分析                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ① 抜け漏れ検出                                   │    │
│  │   - 必須セクションの欠落                         │    │
│  │   - 機能要件の記載不足                           │    │
│  │   - 非機能要件の欠如                             │    │
│  │   - 暗黙的な抜け漏れ                             │    │
│  │                                                 │    │
│  │ ② 矛盾・不整合検出                               │    │
│  │   - セクション間の矛盾                           │    │
│  │   - 用語の不統一                                 │    │
│  │   - 論理的矛盾                                   │    │
│  └─────────────────────────────────────────────────┘    │
│                          ↓                              │
│  Layer 2: GraphRAGによる構造分析                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ ① 抜け漏れ検出（グラフパターン）                 │    │
│  │   - 孤立要件（他と関連性が無い）                 │    │
│  │   - 参照されているが未定義のデータ               │    │
│  │   - 機能に対応するユーザーが無い                 │    │
│  │                                                 │    │
│  │ ② 矛盾検出（グラフパターン）                     │    │
│  │   - 循環依存                                     │    │
│  │   - 矛盾する制約（同じデータに対して）           │    │
│  │   - データアクセスの矛盾                         │    │
│  └─────────────────────────────────────────────────┘    │
│                          ↓                              │
│                  統合レポート生成                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 知識グラフのデータモデル

#### ノードタイプ（最小限）

```cypher
# 1. Requirement（要件）
CREATE (r:Requirement {
  id: "REQ-001",
  title: "ユーザー認証機能",
  description: "...",
  type: "functional",  // functional, non_functional
  source_section: "機能要件"
})

# 2. Function（機能）
CREATE (f:Function {
  id: "FUNC-001",
  name: "ログイン機能",
  description: "..."
})

# 3. Data（データエンティティ）
CREATE (d:Data {
  id: "DATA-001",
  name: "ユーザー情報",
  attributes: ["id", "email", "password_hash"]
})

# 4. User（ユーザー種別）
CREATE (u:User {
  id: "USER-001",
  name: "一般ユーザー"
})

# 5. Constraint（制約）
CREATE (c:Constraint {
  id: "CONST-001",
  description: "パスワードは8文字以上",
  type: "validation"
})
```

#### リレーションシップ（最小限）

```cypher
# 1. DEPENDS_ON（依存）
(r1:Requirement)-[:DEPENDS_ON]->(r2:Requirement)

# 2. CONFLICTS_WITH（矛盾）
(r1:Requirement)-[:CONFLICTS_WITH]->(r2:Requirement)

# 3. USES（使用）
(f:Function)-[:USES {access_type: "read|write"}]->(d:Data)

# 4. REQUIRES（要求）
(f:Function)-[:REQUIRES]->(c:Constraint)

# 5. IMPLEMENTS（実装）
(f:Function)-[:IMPLEMENTS]->(r:Requirement)

# 6. USED_BY（利用）
(u:User)-[:USES]->(f:Function)
```

### GraphRAGによる検出ロジック

#### 1. 抜け漏れ検出

##### 1.1 孤立要件の検出

```cypher
# 他のノードと関連性が無い要件を検出
MATCH (r:Requirement)
WHERE NOT (r)-[]-()
RETURN r.id, r.title
```

**検出例**:
- 「REQ-010: データバックアップ」が定義されているが、どの機能・データとも関連が無い
→ この要件は本当に必要か？または関連付けが漏れているか？

##### 1.2 未定義データの検出

```cypher
# 機能が使用しているが定義されていないデータを検出
MATCH (f:Function)
WHERE f.description CONTAINS '予約情報'
  AND NOT EXISTS {
    MATCH (d:Data {name: '予約情報'})
  }
RETURN f.id, f.name
```

**検出例**:
- 「予約一覧表示機能」が「予約情報を表示」と記述
- しかし「予約情報」というデータエンティティが未定義
→ データ定義が抜けている

##### 1.3 ユーザー不在の機能検出

```cypher
# 機能を使うユーザーが定義されていない
MATCH (f:Function)
WHERE NOT EXISTS {
  MATCH (u:User)-[:USES]->(f)
}
RETURN f.id, f.name
```

**検出例**:
- 「管理者承認機能」が定義されているが、「管理者」というユーザー種別が未定義
→ 対象ユーザーの定義が抜けている

#### 2. 矛盾検出

##### 2.1 循環依存の検出

```cypher
# 要件間の循環依存を検出
MATCH path = (r:Requirement)-[:DEPENDS_ON*]->(r)
RETURN r.id, r.title, [n in nodes(path) | n.id] as cycle_path
```

**検出例**:
- REQ-001 → REQ-003 → REQ-005 → REQ-001
→ 実装順序を決定できない（矛盾）

##### 2.2 制約の矛盾検出

```cypher
# 同じデータに対して矛盾する制約を検出
MATCH (f1:Function)-[:USES]->(d:Data)<-[:USES]-(f2:Function)
MATCH (f1)-[:REQUIRES]->(c1:Constraint)
MATCH (f2)-[:REQUIRES]->(c2:Constraint)
WHERE c1.type = c2.type
  AND c1.description <> c2.description
  AND f1.id < f2.id
RETURN f1.name, f2.name, d.name, c1.description, c2.description
```

**検出例**:
- 「ログイン機能」: 「パスワードは8文字以上」
- 「パスワード変更機能」: 「パスワードは12文字以上」
→ 制約が矛盾（統一が必要）

### エンティティ・リレーションシップ抽出プロンプト

#### エンティティ抽出

```python
ENTITY_EXTRACTION_PROMPT = """
以下の要件定義書から、エンティティを抽出してください。

【要件定義書】
{requirements_text}

【抽出するエンティティ】
1. Requirement: 要件項目
2. Function: 機能
3. Data: データエンティティ
4. User: ユーザー種別
5. Constraint: 制約条件

【出力形式】
```json
{
  "entities": [
    {
      "type": "Requirement",
      "id": "REQ-001",
      "properties": {
        "title": "ユーザー認証機能",
        "description": "...",
        "type": "functional",
        "source_section": "機能要件"
      }
    },
    {
      "type": "Function",
      "id": "FUNC-001",
      "properties": {
        "name": "ログイン機能",
        "description": "..."
      }
    },
    {
      "type": "Data",
      "id": "DATA-001",
      "properties": {
        "name": "ユーザー情報",
        "attributes": ["id", "email", "password_hash"]
      }
    }
  ]
}
``

JSON形式のみを出力してください。
"""
```

#### リレーションシップ抽出

```python
RELATIONSHIP_EXTRACTION_PROMPT = """
以下のエンティティとテキストから、関係性を抽出してください。

【エンティティ】
{entities_json}

【元のテキスト】
{text}

【抽出する関係性】
1. DEPENDS_ON: 依存関係
2. CONFLICTS_WITH: 矛盾関係
3. USES: 使用関係（機能→データ）
4. REQUIRES: 要求関係（機能→制約）
5. IMPLEMENTS: 実装関係（機能→要件）
6. USED_BY: 利用関係（ユーザー→機能）

【推論ルール】
- 「〜が前提」「〜に依存」→ DEPENDS_ON
- 「〜を使用」「〜にアクセス」→ USES
- パスワード処理を行う機能 → パスワード制約を REQUIRES

【出力形式】
```json
{
  "relationships": [
    {
      "type": "DEPENDS_ON",
      "source_id": "REQ-005",
      "target_id": "REQ-001",
      "properties": {
        "description": "..."
      }
    },
    {
      "type": "USES",
      "source_id": "FUNC-001",
      "target_id": "DATA-001",
      "properties": {
        "access_type": "read"
      }
    }
  ]
}
``

JSON形式のみを出力してください。
"""
```

---

## 実装ロードマップ

### フェーズ1: LLMプロンプト実装（2-3日）

**目標**: 抜け漏れと矛盾検出のプロンプトを実装

**タスク**:
1. ✅ 抜け漏れ検出プロンプトの実装
2. ✅ 矛盾・不整合検出プロンプトの実装
3. ✅ 統合レポート生成ロジックの実装
4. ✅ 既存の`review_service.py`の拡張

**成果物**:
- 強化された`review_service.py`
- プロンプトテンプレート

---

### フェーズ2: GraphRAG基盤構築（6-8日）

#### Step 1: Neo4j環境構築（1日）

**タスク**:
1. ✅ `docker-compose.neo4j.yml` 作成
2. ✅ Neo4jコンテナ起動・動作確認
3. ✅ データモデル（制約・インデックス）の作成

#### Step 2: エンティティ・リレーションシップ抽出（3-4日）

**タスク**:
1. ✅ エンティティ抽出プロンプトの実装
2. ✅ リレーションシップ抽出プロンプトの実装
3. ✅ `GraphService` クラスの実装
   - Neo4j接続管理
   - ノード作成
   - リレーションシップ作成
4. ✅ パーサー実装（LLM出力 → 構造化データ）
5. ✅ 単体テスト

**成果物**:
- `backend/app/services/graph_service.py`
- エンティティ・リレーションシップ抽出ロジック

#### Step 3: グラフ分析機能（2-3日）

**タスク**:
1. ✅ 抜け漏れ検出Cypherクエリ
   - 孤立要件検出
   - 未定義データ検出
   - ユーザー不在機能検出
2. ✅ 矛盾検出Cypherクエリ
   - 循環依存検出
   - 制約矛盾検出
3. ✅ API実装（`/api/review/with-graph`）
4. ✅ 統合テスト

**成果物**:
- グラフ分析機能
- APIエンドポイント

---

### フェーズ3: 統合とテスト（3-4日）

**タスク**:
1. ✅ LLMレビューとGraphRAGレビューの統合
2. ✅ 統合レポート生成
3. ✅ E2Eテスト
4. ✅ サンプルデータでの検証

**成果物**:
- 統合レビューサービス
- テストコード
- ドキュメント

---

## 総工数見積もり

| フェーズ | 内容 | 工数 |
|---------|------|------|
| フェーズ1 | LLMプロンプト実装 | 2-3日 |
| フェーズ2 | GraphRAG基盤構築 | 6-8日 |
| フェーズ3 | 統合とテスト | 3-4日 |
| **合計** | | **11-15日** |

---

## 参考資料

### GraphRAG・Knowledge Graph

1. **Microsoft GraphRAG**
   - https://microsoft.github.io/graphrag/
   - エンティティ・リレーションシップ抽出のベストプラクティス

2. **Neo4j**
   - [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
   - [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)

### 要件定義ベストプラクティス

3. **ISO/IEC/IEEE 29148**
   - Systems and software engineering — Requirements engineering
   - 要件定義の国際標準
