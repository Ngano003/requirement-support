# GraphRAG実装 詳細設計書

## 目次

1. [概要](#概要)
2. [アーキテクチャ](#アーキテクチャ)
3. [技術スタック](#技術スタック)
4. [データモデル設計](#データモデル設計)
5. [サービス層設計](#サービス層設計)
6. [API設計](#api設計)
7. [実装タスク](#実装タスク)
8. [環境構築](#環境構築)

---

## 概要

### 目的

LLMによるテキスト分析（フェーズ1）に加えて、**知識グラフによる構造分析**を導入し、レビュー精度を向上させます。

### GraphRAGの役割

**2つの主要な検出目標**:

1. **抜け漏れ検出（グラフパターン）**
   - 孤立要件（他と関連性が無い）
   - 参照されているが未定義のデータ
   - 機能に対応するユーザーが無い

2. **矛盾検出（グラフパターン）**
   - 循環依存
   - 矛盾する制約（同じデータに対して）
   - データアクセスの矛盾

### なぜGraphRAGが必要か

LLMだけでは以下の検出が困難：
- **複雑な依存関係**: 3つ以上の要件が絡む循環依存
- **暗黙的な関係性**: テキストに明示されていないが、構造から推測できる問題
- **大規模文書の全体整合性**: 100ページ以上の要件定義書の一貫性チェック

---

## アーキテクチャ

### 全体構成

```
┌─────────────────────────────────────────────────────────────┐
│           要件定義レビューシステム（統合版）                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Phase 1] LLMによるテキスト分析（並列実行）                 │
│  ┌────────────────────┬────────────────────┐                │
│  │ 抜け漏れ検出        │ 矛盾・不整合検出    │                │
│  └────────────────────┴────────────────────┘                │
│                          ↓                                  │
│  [Phase 2] GraphRAGによる構造分析                            │
│  ┌─────────────────────────────────────────────────┐        │
│  │ ① エンティティ・リレーションシップ抽出（LLM）    │        │
│  │    要件定義書 → 構造化データ                     │        │
│  ├─────────────────────────────────────────────────┤        │
│  │ ② 知識グラフ構築（Neo4j）                        │        │
│  │    構造化データ → ノード/エッジの作成             │        │
│  ├─────────────────────────────────────────────────┤        │
│  │ ③ グラフクエリ実行（Cypher）                     │        │
│  │    パターンマッチング → 問題検出                 │        │
│  └─────────────────────────────────────────────────┘        │
│                          ↓                                  │
│  [Phase 3] 統合レポート生成                                  │
│  - LLM検出結果 + GraphRAG検出結果 → 統合JSON                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 処理フロー

```
[要件定義書]
     ↓
┌────┴────┐
│         │
↓         ↓
[LLM分析] [GraphRAG分析]
(Phase1)  (Phase2)
│         │
│         ├─ ① エンティティ抽出（LLM）
│         ├─ ② リレーションシップ抽出（LLM）
│         ├─ ③ Neo4jへ保存
│         └─ ④ Cypherクエリで問題検出
│
└────┬────┘
     ↓
[統合レポート]
```

**並列実行による最適化**:
- Phase 1のLLM分析（抜け漏れ + 矛盾）: 並列実行
- Phase 2のエンティティ抽出とリレーションシップ抽出: 逐次実行（リレーションシップ抽出はエンティティに依存）

---

## 技術スタック

### Neo4j（グラフデータベース）

**選定理由**:
- 業界標準のグラフDB
- Cypherクエリ言語が直感的
- Pythonドライバーが充実（`neo4j` パッケージ）
- Docker対応

**バージョン**: 5.x (Community Edition)

### Python Neo4j Driver

```python
neo4j==5.25.0
```

**主要機能**:
- 非同期対応（`AsyncGraphDatabase`）
- トランザクション管理
- コネクションプール

### LLM（エンティティ抽出）

既存の`llm_service`を活用：
- OpenRouter（開発/テスト）
- vLLM（本番）

---

## データモデル設計

### ノードタイプ

#### 1. Requirement（要件）

```python
{
  "id": "REQ-001",
  "title": "ユーザー認証機能",
  "description": "詳細説明...",
  "type": "functional",  # functional | non_functional
  "source_section": "機能要件",
  "priority": "high"  # high | medium | low
}
```

#### 2. Function（機能）

```python
{
  "id": "FUNC-001",
  "name": "ログイン機能",
  "description": "メールアドレスとパスワードでログイン",
  "inputs": ["メールアドレス", "パスワード"],
  "outputs": ["ログイン結果", "セッショントークン"]
}
```

#### 3. Data（データエンティティ）

```python
{
  "id": "DATA-001",
  "name": "ユーザー情報",
  "attributes": ["id", "email", "password_hash", "created_at"],
  "description": "システムユーザーのマスターデータ"
}
```

#### 4. User（ユーザー種別）

```python
{
  "id": "USER-001",
  "name": "一般ユーザー",
  "description": "サービスを利用する一般ユーザー",
  "permissions": ["read", "create"]
}
```

#### 5. Constraint（制約）

```python
{
  "id": "CONST-001",
  "description": "パスワードは8文字以上",
  "type": "validation",  # validation | business_rule | technical
  "target": "パスワード"
}
```

### リレーションシップタイプ

#### 1. DEPENDS_ON（依存）

```cypher
(r1:Requirement)-[:DEPENDS_ON {reason: "ログインが前提"}]->(r2:Requirement)
```

**使用例**:
- 「予約管理機能」 DEPENDS_ON 「ユーザー認証機能」

#### 2. CONFLICTS_WITH（矛盾）

```cypher
(r1:Requirement)-[:CONFLICTS_WITH {reason: "同時に満たせない"}]->(r2:Requirement)
```

**使用例**:
- 「全データ公開」 CONFLICTS_WITH 「認証必須」

#### 3. USES（使用）

```cypher
(f:Function)-[:USES {access_type: "read"}]->(d:Data)
(f:Function)-[:USES {access_type: "write"}]->(d:Data)
```

**使用例**:
- 「ログイン機能」 USES[write] 「セッション情報」
- 「ユーザー情報表示」 USES[read] 「ユーザー情報」

#### 4. REQUIRES（要求）

```cypher
(f:Function)-[:REQUIRES]->(c:Constraint)
```

**使用例**:
- 「パスワード変更機能」 REQUIRES 「パスワードは8文字以上」

#### 5. IMPLEMENTS（実装）

```cypher
(f:Function)-[:IMPLEMENTS]->(r:Requirement)
```

**使用例**:
- 「ログイン機能」 IMPLEMENTS 「ユーザー認証機能」

#### 6. USED_BY（利用）

```cypher
(u:User)-[:USES]->(f:Function)
```

**使用例**:
- 「一般ユーザー」 USES 「書籍検索機能」

---

## サービス層設計

### 1. GraphService（新規作成）

**責務**: Neo4jとの接続、ノード/エッジの作成、クエリ実行

```python
# backend/app/services/graph_service.py

from neo4j import AsyncGraphDatabase
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GraphService:
    """Neo4jグラフデータベースサービス"""

    def __init__(self, uri: str, user: str, password: str):
        """
        Args:
            uri: Neo4j接続URI (例: bolt://localhost:7687)
            user: 認証ユーザー名
            password: 認証パスワード
        """
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    async def close(self):
        """ドライバーを閉じる"""
        await self.driver.close()

    async def clear_graph(self, session_id: str):
        """指定セッションのグラフをクリア"""
        async with self.driver.session() as session:
            await session.run(
                "MATCH (n {session_id: $session_id}) DETACH DELETE n",
                session_id=session_id
            )

    async def create_nodes(self, nodes: List[Dict[str, Any]], session_id: str):
        """ノードを一括作成"""
        async with self.driver.session() as session:
            for node in nodes:
                node_type = node["type"]
                properties = node["properties"]
                properties["session_id"] = session_id
                properties["id"] = node["id"]

                await session.run(
                    f"CREATE (n:{node_type} $properties)",
                    properties=properties
                )

    async def create_relationships(
        self, relationships: List[Dict[str, Any]], session_id: str
    ):
        """リレーションシップを一括作成"""
        async with self.driver.session() as session:
            for rel in relationships:
                rel_type = rel["type"]
                source_id = rel["source_id"]
                target_id = rel["target_id"]
                properties = rel.get("properties", {})

                await session.run(
                    f"""
                    MATCH (a {{id: $source_id, session_id: $session_id}})
                    MATCH (b {{id: $target_id, session_id: $session_id}})
                    CREATE (a)-[r:{rel_type} $properties]->(b)
                    """,
                    source_id=source_id,
                    target_id=target_id,
                    session_id=session_id,
                    properties=properties
                )

    async def detect_isolated_requirements(self, session_id: str) -> List[Dict[str, Any]]:
        """孤立要件を検出"""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (r:Requirement {session_id: $session_id})
                WHERE NOT (r)-[]-()
                RETURN r.id AS id, r.title AS title, r.description AS description
                """,
                session_id=session_id
            )
            records = await result.data()
            return records

    async def detect_missing_data_definitions(self, session_id: str) -> List[Dict[str, Any]]:
        """未定義データを検出"""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (f:Function {session_id: $session_id})
                WHERE NOT EXISTS {
                    MATCH (f)-[:USES]->(d:Data)
                }
                RETURN f.id AS function_id, f.name AS function_name
                """,
                session_id=session_id
            )
            records = await result.data()
            return records

    async def detect_functions_without_users(self, session_id: str) -> List[Dict[str, Any]]:
        """ユーザー不在の機能を検出"""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (f:Function {session_id: $session_id})
                WHERE NOT EXISTS {
                    MATCH (u:User)-[:USES]->(f)
                }
                RETURN f.id AS function_id, f.name AS function_name
                """,
                session_id=session_id
            )
            records = await result.data()
            return records

    async def detect_circular_dependencies(self, session_id: str) -> List[Dict[str, Any]]:
        """循環依存を検出"""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH path = (r:Requirement {session_id: $session_id})-[:DEPENDS_ON*]->(r)
                RETURN r.id AS requirement_id,
                       r.title AS title,
                       [n IN nodes(path) | n.id] AS cycle_path
                """,
                session_id=session_id
            )
            records = await result.data()
            return records

    async def detect_conflicting_constraints(self, session_id: str) -> List[Dict[str, Any]]:
        """矛盾する制約を検出"""
        async with self.driver.session() as session:
            result = await session.run(
                """
                MATCH (f1:Function {session_id: $session_id})-[:USES]->(d:Data)<-[:USES]-(f2:Function {session_id: $session_id})
                MATCH (f1)-[:REQUIRES]->(c1:Constraint)
                MATCH (f2)-[:REQUIRES]->(c2:Constraint)
                WHERE c1.type = c2.type
                  AND c1.target = c2.target
                  AND c1.description <> c2.description
                  AND f1.id < f2.id
                RETURN f1.name AS function1,
                       f2.name AS function2,
                       d.name AS data_name,
                       c1.description AS constraint1,
                       c2.description AS constraint2
                """,
                session_id=session_id
            )
            records = await result.data()
            return records


# シングルトンインスタンス（環境変数から設定を取得）
graph_service: Optional[GraphService] = None

def init_graph_service(uri: str, user: str, password: str):
    """GraphServiceを初期化"""
    global graph_service
    graph_service = GraphService(uri, user, password)

async def close_graph_service():
    """GraphServiceをクローズ"""
    if graph_service:
        await graph_service.close()
```

### 2. GraphAnalysisService（新規作成）

**責務**: エンティティ抽出、グラフ分析の統合処理

```python
# backend/app/services/graph_analysis_service.py

import asyncio
import logging
from typing import Tuple, List, Dict, Any
from app.services.llm_service import llm_service
from app.services.graph_service import graph_service
from app.models.schemas import (
    GraphAnalysisResult,
    GraphMissingItem,
    GraphContradiction,
)

logger = logging.getLogger(__name__)


class GraphAnalysisService:
    """グラフ分析サービス"""

    ENTITY_EXTRACTION_PROMPT_TEMPLATE = """以下の要件定義書から、エンティティを抽出してください。

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
{{
  "entities": [
    {{
      "type": "Requirement",
      "id": "REQ-001",
      "properties": {{
        "title": "ユーザー認証機能",
        "description": "...",
        "type": "functional",
        "source_section": "機能要件"
      }}
    }},
    {{
      "type": "Function",
      "id": "FUNC-001",
      "properties": {{
        "name": "ログイン機能",
        "description": "..."
      }}
    }},
    {{
      "type": "Data",
      "id": "DATA-001",
      "properties": {{
        "name": "ユーザー情報",
        "attributes": ["id", "email", "password_hash"]
      }}
    }}
  ]
}}
```

JSON形式のみを出力してください。
"""

    RELATIONSHIP_EXTRACTION_PROMPT_TEMPLATE = """以下のエンティティとテキストから、関係性を抽出してください。

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
{{
  "relationships": [
    {{
      "type": "DEPENDS_ON",
      "source_id": "REQ-005",
      "target_id": "REQ-001",
      "properties": {{
        "description": "..."
      }}
    }},
    {{
      "type": "USES",
      "source_id": "FUNC-001",
      "target_id": "DATA-001",
      "properties": {{
        "access_type": "read"
      }}
    }}
  ]
}}
```

JSON形式のみを出力してください。
"""

    async def analyze_requirements(
        self, requirements_text: str, session_id: str
    ) -> GraphAnalysisResult:
        """
        要件定義書をグラフ分析

        Args:
            requirements_text: 要件定義書
            session_id: セッションID（グラフの名前空間として使用）

        Returns:
            GraphAnalysisResult
        """
        try:
            # 既存のグラフをクリア
            await graph_service.clear_graph(session_id)

            # 1. エンティティ抽出（LLM）
            entities = await self._extract_entities(requirements_text)

            # 2. リレーションシップ抽出（LLM）
            relationships = await self._extract_relationships(
                requirements_text, entities
            )

            # 3. Neo4jにノード/エッジを作成
            await graph_service.create_nodes(entities, session_id)
            await graph_service.create_relationships(relationships, session_id)

            # 4. グラフクエリで問題検出（並列実行）
            (
                isolated_reqs,
                missing_data,
                functions_without_users,
                circular_deps,
                conflicting_constraints,
            ) = await asyncio.gather(
                graph_service.detect_isolated_requirements(session_id),
                graph_service.detect_missing_data_definitions(session_id),
                graph_service.detect_functions_without_users(session_id),
                graph_service.detect_circular_dependencies(session_id),
                graph_service.detect_conflicting_constraints(session_id),
            )

            # 5. 結果を構造化
            missing_items = self._build_missing_items(
                isolated_reqs, missing_data, functions_without_users
            )
            contradictions = self._build_contradictions(
                circular_deps, conflicting_constraints
            )

            return GraphAnalysisResult(
                missing_items=missing_items,
                contradictions=contradictions,
            )

        except Exception as e:
            logger.error(f"Graph analysis error: {e}", exc_info=True)
            # エラー時は空の結果を返す
            return GraphAnalysisResult(missing_items=[], contradictions=[])

    async def _extract_entities(self, requirements_text: str) -> List[Dict[str, Any]]:
        """エンティティ抽出"""
        prompt = self.ENTITY_EXTRACTION_PROMPT_TEMPLATE.format(
            requirements_text=requirements_text
        )

        response = await llm_service.generate_with_system_prompt(
            system_prompt="あなたは要件定義書からエンティティを抽出する専門家です。",
            user_prompt=prompt,
            temperature=0.2,
        )

        data = self._parse_json(response)
        return data.get("entities", [])

    async def _extract_relationships(
        self, requirements_text: str, entities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """リレーションシップ抽出"""
        import json

        entities_json = json.dumps(entities, ensure_ascii=False, indent=2)
        prompt = self.RELATIONSHIP_EXTRACTION_PROMPT_TEMPLATE.format(
            entities_json=entities_json, text=requirements_text
        )

        response = await llm_service.generate_with_system_prompt(
            system_prompt="あなたは要件間の関係性を抽出する専門家です。",
            user_prompt=prompt,
            temperature=0.2,
        )

        data = self._parse_json(response)
        return data.get("relationships", [])

    def _parse_json(self, json_str: str) -> dict:
        """JSON文字列をパース"""
        import json

        json_str = json_str.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        if json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()

        return json.loads(json_str)

    def _build_missing_items(
        self,
        isolated_reqs: List[Dict],
        missing_data: List[Dict],
        functions_without_users: List[Dict],
    ) -> List[GraphMissingItem]:
        """抜け漏れ項目を構築"""
        items = []

        for req in isolated_reqs:
            items.append(
                GraphMissingItem(
                    type="isolated_requirement",
                    item=req["title"],
                    description=f"要件「{req['title']}」が孤立しています（他の要件や機能と関連性がありません）",
                    severity="medium",
                    suggestion="この要件が本当に必要か確認するか、関連する機能や要件を明記してください",
                )
            )

        for func in missing_data:
            items.append(
                GraphMissingItem(
                    type="missing_data_definition",
                    item=func["function_name"],
                    description=f"機能「{func['function_name']}」が使用するデータが定義されていません",
                    severity="high",
                    suggestion="この機能が使用するデータエンティティを定義してください",
                )
            )

        for func in functions_without_users:
            items.append(
                GraphMissingItem(
                    type="missing_user",
                    item=func["function_name"],
                    description=f"機能「{func['function_name']}」を使用するユーザーが定義されていません",
                    severity="medium",
                    suggestion="対象ユーザーセクションにこの機能を使用するユーザー種別を追加してください",
                )
            )

        return items

    def _build_contradictions(
        self, circular_deps: List[Dict], conflicting_constraints: List[Dict]
    ) -> List[GraphContradiction]:
        """矛盾項目を構築"""
        contradictions = []

        for dep in circular_deps:
            contradictions.append(
                GraphContradiction(
                    type="circular_dependency",
                    description=f"要件「{dep['title']}」に循環依存が検出されました",
                    items=dep["cycle_path"],
                    severity="high",
                    suggestion="依存関係を見直し、実装順序を決定できるようにしてください",
                )
            )

        for constraint in conflicting_constraints:
            contradictions.append(
                GraphContradiction(
                    type="conflicting_constraint",
                    description=f"データ「{constraint['data_name']}」に対して矛盾する制約があります",
                    items=[
                        f"{constraint['function1']}: {constraint['constraint1']}",
                        f"{constraint['function2']}: {constraint['constraint2']}",
                    ],
                    severity="high",
                    suggestion="制約を統一してください",
                )
            )

        return contradictions


# シングルトンインスタンス
graph_analysis_service = GraphAnalysisService()
```

---

## API設計

### 新規エンドポイント

```
POST /api/review/with-graph
```

**リクエスト**:

```json
{
  "requirements_text": "# システム概要\n...",
  "session_id": "optional-session-id"
}
```

**レスポンス**:

```json
{
  "review_id": "uuid-string",
  "session_id": "uuid-string",
  "llm_analysis": {
    "missing_items": { ... },
    "contradictions": { ... }
  },
  "graph_analysis": {
    "missing_items": [
      {
        "type": "isolated_requirement",
        "item": "データバックアップ機能",
        "description": "要件が孤立しています",
        "severity": "medium",
        "suggestion": "関連する機能や要件を明記してください"
      }
    ],
    "contradictions": [
      {
        "type": "circular_dependency",
        "description": "循環依存が検出されました",
        "items": ["REQ-001", "REQ-003", "REQ-005", "REQ-001"],
        "severity": "high",
        "suggestion": "依存関係を見直してください"
      }
    ]
  },
  "summary": {
    "total_missing_items": 15,
    "total_contradictions": 7,
    "high_severity_count": 5,
    "medium_severity_count": 10,
    "low_severity_count": 7,
    "overall_assessment": "グラフ分析により循環依存が検出されました。..."
  }
}
```

---

## 実装タスク

### タスク1: Neo4j環境構築（1日）

**ファイル**: `docker-compose.neo4j.yml`（新規作成）

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.25.0
    container_name: requirement-support-neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/password123
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    networks:
      - requirement-support-network

volumes:
  neo4j_data:
  neo4j_logs:

networks:
  requirement-support-network:
    external: true
```

**タスク**:
- [ ] `docker-compose.neo4j.yml` 作成
- [ ] Neo4jコンテナ起動・動作確認
- [ ] ブラウザでNeo4j UI（http://localhost:7474）にアクセス確認
- [ ] 制約・インデックスの作成

### タスク2: データモデル追加（2時間）

**ファイル**: `backend/app/models/schemas.py`

```python
class GraphMissingItem(BaseModel):
    """グラフ分析による抜け漏れ項目"""
    type: Literal["isolated_requirement", "missing_data_definition", "missing_user"]
    item: str = Field(..., description="項目名")
    description: str = Field(..., description="説明")
    severity: Literal["high", "medium", "low"]
    suggestion: str = Field(..., description="改善提案")


class GraphContradiction(BaseModel):
    """グラフ分析による矛盾"""
    type: Literal["circular_dependency", "conflicting_constraint"]
    description: str = Field(..., description="説明")
    items: List[str] = Field(..., description="関連項目")
    severity: Literal["high", "medium"]
    suggestion: str = Field(..., description="解決方法")


class GraphAnalysisResult(BaseModel):
    """グラフ分析結果"""
    missing_items: List[GraphMissingItem] = Field(default_factory=list)
    contradictions: List[GraphContradiction] = Field(default_factory=list)


class IntegratedReviewRequest(BaseModel):
    """統合レビューリクエスト"""
    requirements_text: str
    session_id: Optional[str] = None


class IntegratedReviewResponse(BaseModel):
    """統合レビューレスポンス（LLM + GraphRAG）"""
    review_id: str
    session_id: str
    llm_analysis: Dict[str, Any]  # MissingItemsResult + ContradictionsResult
    graph_analysis: GraphAnalysisResult
    summary: EnhancedReviewSummary
```

### タスク3: GraphService実装（3-4時間）

**ファイル**: `backend/app/services/graph_service.py`（新規作成）

- [ ] `GraphService` クラス実装
- [ ] Neo4j接続管理
- [ ] ノード/エッジ作成メソッド
- [ ] Cypherクエリメソッド（孤立要件、循環依存等）

### タスク4: GraphAnalysisService実装（4-5時間）

**ファイル**: `backend/app/services/graph_analysis_service.py`（新規作成）

- [ ] エンティティ抽出プロンプト実装
- [ ] リレーションシップ抽出プロンプト実装
- [ ] `analyze_requirements()` メソッド実装
- [ ] 結果の構造化

### タスク5: 統合API実装（2-3時間）

**ファイル**: `backend/app/api/review.py`

- [ ] `POST /api/review/with-graph` エンドポイント追加
- [ ] LLM分析とグラフ分析の統合
- [ ] 環境変数設定（`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`）

### タスク6: テストコード（3-4時間）

**ファイル**: `backend/tests/test_graph_analysis.py`（新規作成）

- [ ] GraphServiceのユニットテスト
- [ ] GraphAnalysisServiceのユニットテスト
- [ ] 統合APIのテスト

### タスク7: ドキュメント（1-2時間）

- [ ] 使用方法ドキュメント
- [ ] GraphRAGの仕組み説明
- [ ] Cypherクエリ例

---

## 環境構築

### 1. Neo4j起動

```bash
docker-compose -f docker-compose.neo4j.yml up -d
```

### 2. 環境変数設定

**backend/.env**:

```env
# 既存の設定
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-key

# 新規追加
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123
```

### 3. Pythonパッケージ追加

**backend/requirements.txt**:

```
neo4j==5.25.0
```

### 4. アプリケーション起動時の初期化

**backend/app/main.py**:

```python
from app.services.graph_service import init_graph_service, close_graph_service
from app.utils.config import settings

@app.on_event("startup")
async def startup_event():
    # GraphServiceを初期化
    init_graph_service(
        uri=settings.NEO4J_URI,
        user=settings.NEO4J_USER,
        password=settings.NEO4J_PASSWORD,
    )

@app.on_event("shutdown")
async def shutdown_event():
    # GraphServiceをクローズ
    await close_graph_service()
```

---

## パフォーマンス最適化

### 並列実行戦略

```python
# LLM分析とGraphRAG分析を並列実行
llm_task = review_service.review_requirements_enhanced(requirements_text)
graph_task = graph_analysis_service.analyze_requirements(requirements_text, session_id)

llm_result, graph_result = await asyncio.gather(llm_task, graph_task)
```

**効果**:
- 逐次実行: LLM(10秒) + GraphRAG(15秒) = **25秒**
- 並列実行: max(10秒, 15秒) = **15秒**

### Neo4jインデックス

```cypher
CREATE INDEX requirement_id IF NOT EXISTS FOR (r:Requirement) ON (r.id);
CREATE INDEX function_id IF NOT EXISTS FOR (f:Function) ON (f.id);
CREATE INDEX data_id IF NOT EXISTS FOR (d:Data) ON (d.id);
CREATE INDEX user_id IF NOT EXISTS FOR (u:User) ON (u.id);
CREATE INDEX constraint_id IF NOT EXISTS FOR (c:Constraint) ON (c.id);
```

---

## エラーハンドリング

### Neo4j接続エラー

```python
try:
    await graph_service.create_nodes(entities, session_id)
except Exception as e:
    logger.error(f"Neo4j error: {e}")
    # グラフ分析をスキップして、LLM分析のみを返す
    return GraphAnalysisResult()
```

### エンティティ抽出失敗

```python
try:
    entities = await self._extract_entities(requirements_text)
except Exception as e:
    logger.error(f"Entity extraction failed: {e}")
    return []  # 空のリストを返す
```

---

## 今後の拡張

### Phase 3: 高度なグラフ分析

- **コミュニティ検出**: 密に関連する要件群を自動抽出
- **重要度スコアリング**: PageRankアルゴリズムで重要な要件を特定
- **変更影響分析**: 要件変更時の影響範囲を自動計算

---

## 総工数見積もり

| タスク | 工数 |
|--------|------|
| Neo4j環境構築 | 1日 |
| データモデル追加 | 2時間 |
| GraphService実装 | 3-4時間 |
| GraphAnalysisService実装 | 4-5時間 |
| 統合API実装 | 2-3時間 |
| テストコード | 3-4時間 |
| ドキュメント | 1-2時間 |
| **合計** | **2-3日** |

---

## 参考資料

### Neo4j公式ドキュメント

- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [Graph Data Modeling](https://neo4j.com/developer/guide-data-modeling/)

### GraphRAG

- [Microsoft GraphRAG](https://microsoft.github.io/graphrag/)
- [LangChain Graph QA](https://python.langchain.com/docs/use_cases/graph/)

### グラフアルゴリズム

- [Cycle Detection](https://neo4j.com/docs/graph-data-science/current/algorithms/cycles/)
- [PageRank](https://neo4j.com/docs/graph-data-science/current/algorithms/page-rank/)
