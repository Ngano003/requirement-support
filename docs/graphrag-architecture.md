# GraphRAG + Neo4j統合アーキテクチャ設計

## Phase 2実装ガイド

このドキュメントは、Phase 2で実装するGraphRAG + Neo4j統合の詳細設計と実装手順を記載しています。

## 1. アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│                    フロントエンド (Next.js)                    │
│  - グラフ可視化UI                                              │
│  - インタラクティブな関係性表示                                 │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API
┌────────────────────┴────────────────────────────────────────┐
│                  バックエンド (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ GraphRAG Service                                     │   │
│  │  - エンティティ抽出                                    │   │
│  │  - リレーションシップ抽出                              │   │
│  │  - グラフ分析                                         │   │
│  └──────────┬───────────────────────┬────────────────────┘   │
└─────────────┼───────────────────────┼────────────────────────┘
              │                       │
    ┌─────────▼───────┐     ┌────────▼────────┐
    │  vLLM/OpenRouter │     │  Neo4j Database │
    │                  │     │                 │
    │ エンティティ抽出  │     │ 知識グラフ管理   │
    │ 関係性推論       │     │ Cypher Query    │
    └──────────────────┘     └─────────────────┘
```

## 2. Neo4j環境構築

### 2.1 Docker Composeを使用したセットアップ

`docker-compose.neo4j.yml`:
```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15.0
    container_name: requirement-support-neo4j
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    environment:
      - NEO4J_AUTH=neo4j/password123  # 本番環境では変更必須
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=2G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/var/lib/neo4j/import
      - neo4j_plugins:/plugins
    networks:
      - requirement-net

volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
  neo4j_plugins:

networks:
  requirement-net:
    driver: bridge
```

起動方法:
```bash
docker-compose -f docker-compose.neo4j.yml up -d
```

### 2.2 Neo4jブラウザでの確認

1. ブラウザで `http://localhost:7474` にアクセス
2. ユーザー名: `neo4j`, パスワード: `password123` でログイン
3. 接続成功を確認

## 3. データモデル設計

### 3.1 ノード定義

#### Requirement（要件）
```cypher
CREATE CONSTRAINT requirement_id IF NOT EXISTS
FOR (r:Requirement) REQUIRE r.id IS UNIQUE;

CREATE (r:Requirement {
  id: "REQ-001",
  title: "ユーザー認証機能",
  description: "ユーザーがログインできる機能",
  type: "functional",  // functional, non_functional, constraint
  priority: "high",    // high, medium, low
  status: "draft"      // draft, confirmed, implemented
})
```

#### Function（機能）
```cypher
CREATE (f:Function {
  id: "FUNC-001",
  name: "ログイン機能",
  description: "メールアドレスとパスワードでログイン",
  category: "authentication"
})
```

#### Data（データエンティティ）
```cypher
CREATE (d:Data {
  id: "DATA-001",
  name: "ユーザー情報",
  type: "entity",
  attributes: ["id", "email", "password_hash", "created_at"]
})
```

#### User（アクター）
```cypher
CREATE (u:User {
  id: "USER-001",
  name: "一般ユーザー",
  role: "end_user",
  description: "システムを利用する一般ユーザー"
})
```

#### Constraint（制約）
```cypher
CREATE (c:Constraint {
  id: "CONST-001",
  description: "パスワードは8文字以上で英数字を含む",
  type: "security"
})
```

#### NonFunctional（非機能要件）
```cypher
CREATE (nf:NonFunctional {
  id: "NF-001",
  category: "performance",
  description: "ログイン処理は2秒以内に完了",
  metric: "response_time",
  target: "2000ms"
})
```

### 3.2 リレーションシップ定義

```cypher
// 依存関係
MATCH (r1:Requirement {id: "REQ-001"})
MATCH (r2:Requirement {id: "REQ-002"})
CREATE (r1)-[:DEPENDS_ON {type: "prerequisite"}]->(r2)

// 矛盾関係
MATCH (r1:Requirement {id: "REQ-001"})
MATCH (r2:Requirement {id: "REQ-003"})
CREATE (r1)-[:CONFLICTS_WITH {reason: "同時には実現できない"}]->(r2)

// 使用関係
MATCH (f:Function {id: "FUNC-001"})
MATCH (d:Data {id: "DATA-001"})
CREATE (f)-[:USES {access_type: "read_write"}]->(d)

// 要求関係
MATCH (f:Function {id: "FUNC-001"})
MATCH (c:Constraint {id: "CONST-001"})
CREATE (f)-[:REQUIRES {mandatory: true}]->(c)

// ユーザーと機能の関係
MATCH (u:User {id: "USER-001"})
MATCH (f:Function {id: "FUNC-001"})
CREATE (u)-[:USES]->(f)
```

## 4. GraphRAG実装詳細

### 4.1 エンティティ抽出プロンプト

```python
ENTITY_EXTRACTION_PROMPT = """
以下の要件定義書のテキストから、エンティティを抽出してください。

【テキスト】
{text}

【抽出するエンティティタイプ】
1. Requirement: 要件項目
2. Function: 機能
3. Data: データエンティティ
4. User: ユーザー/アクター
5. Constraint: 制約条件
6. NonFunctional: 非機能要件

【出力形式】
JSON形式で以下の構造で出力してください：
```json
{{
  "entities": [
    {{
      "type": "Requirement",
      "id": "REQ-001",
      "properties": {{
        "title": "...",
        "description": "...",
        "type": "functional",
        "priority": "high"
      }}
    }}
  ]
}}
```
"""
```

### 4.2 リレーションシップ抽出プロンプト

```python
RELATIONSHIP_EXTRACTION_PROMPT = """
以下のエンティティ間の関係性を抽出してください。

【エンティティ】
{entities}

【テキスト】
{text}

【抽出する関係性タイプ】
1. DEPENDS_ON: 依存関係
2. CONFLICTS_WITH: 矛盾関係
3. REQUIRES: 要求関係
4. USES: 使用関係
5. IMPLEMENTS: 実装関係
6. PART_OF: 包含関係

【出力形式】
JSON形式で以下の構造で出力してください：
```json
{{
  "relationships": [
    {{
      "type": "DEPENDS_ON",
      "source_id": "REQ-001",
      "target_id": "REQ-002",
      "properties": {{
        "type": "prerequisite",
        "description": "..."
      }}
    }}
  ]
}}
```
"""
```

### 4.3 グラフ構築サービス実装

`backend/app/services/graph_service.py`:
```python
from neo4j import GraphDatabase
from typing import List, Dict
import json


class GraphService:
    """グラフ構築・管理サービス"""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_node(self, label: str, properties: Dict) -> str:
        """ノードを作成"""
        with self.driver.session() as session:
            query = f"""
            CREATE (n:{label} $props)
            RETURN n.id as id
            """
            result = session.run(query, props=properties)
            return result.single()["id"]

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Dict = None
    ):
        """リレーションシップを作成"""
        with self.driver.session() as session:
            query = f"""
            MATCH (a {{id: $source_id}})
            MATCH (b {{id: $target_id}})
            CREATE (a)-[r:{rel_type} $props]->(b)
            RETURN r
            """
            session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                props=properties or {}
            )

    def find_circular_dependencies(self) -> List[Dict]:
        """循環依存を検出"""
        with self.driver.session() as session:
            query = """
            MATCH path = (r:Requirement)-[:DEPENDS_ON*]->(r)
            RETURN r.id as requirement_id,
                   [n in nodes(path) | n.id] as cycle_path
            """
            results = session.run(query)
            return [dict(record) for record in results]

    def find_isolated_requirements(self) -> List[Dict]:
        """孤立要件を検出"""
        with self.driver.session() as session:
            query = """
            MATCH (r:Requirement)
            WHERE NOT (r)-[]-()
            RETURN r.id as id, r.title as title
            """
            results = session.run(query)
            return [dict(record) for record in results]

    def analyze_impact(self, requirement_id: str) -> Dict:
        """影響範囲を分析"""
        with self.driver.session() as session:
            query = """
            MATCH path = (r:Requirement {id: $req_id})-[:DEPENDS_ON*1..5]->(dep)
            RETURN r.id as source,
                   collect(distinct dep.id) as dependencies,
                   length(path) as depth
            """
            result = session.run(query, req_id=requirement_id)
            return dict(result.single())

    def get_graph_for_visualization(self) -> Dict:
        """可視化用のグラフデータを取得"""
        with self.driver.session() as session:
            # ノードを取得
            nodes_query = """
            MATCH (n)
            RETURN id(n) as id, labels(n)[0] as label, properties(n) as properties
            """
            nodes = [dict(record) for record in session.run(nodes_query)]

            # エッジを取得
            edges_query = """
            MATCH (a)-[r]->(b)
            RETURN id(a) as source, id(b) as target,
                   type(r) as type, properties(r) as properties
            """
            edges = [dict(record) for record in session.run(edges_query)]

            return {"nodes": nodes, "edges": edges}
```

## 5. API実装

### 5.1 グラフ構築API

`backend/app/api/graph.py`:
```python
from fastapi import APIRouter, HTTPException
from app.services.graph_service import GraphService
from app.services.llm_service import llm_service
from app.utils.config import settings

router = APIRouter(prefix="/api/graph", tags=["graph"])

graph_service = GraphService(
    uri=settings.neo4j_uri,
    user=settings.neo4j_user,
    password=settings.neo4j_password
)


@router.post("/build")
async def build_knowledge_graph(requirements_text: str):
    """要件定義書から知識グラフを構築"""
    try:
        # 1. エンティティを抽出
        entities = await extract_entities(requirements_text)

        # 2. ノードを作成
        for entity in entities:
            graph_service.create_node(
                label=entity["type"],
                properties=entity["properties"]
            )

        # 3. リレーションシップを抽出
        relationships = await extract_relationships(
            requirements_text, entities
        )

        # 4. リレーションシップを作成
        for rel in relationships:
            graph_service.create_relationship(
                source_id=rel["source_id"],
                target_id=rel["target_id"],
                rel_type=rel["type"],
                properties=rel.get("properties")
            )

        return {"status": "success", "entities_count": len(entities)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze")
async def analyze_graph():
    """グラフを分析"""
    circular_deps = graph_service.find_circular_dependencies()
    isolated_reqs = graph_service.find_isolated_requirements()

    return {
        "circular_dependencies": circular_deps,
        "isolated_requirements": isolated_reqs
    }


@router.get("/visualize")
async def get_visualization_data():
    """グラフ可視化データを取得"""
    return graph_service.get_graph_for_visualization()
```

## 6. フロントエンド実装

### 6.1 グラフ可視化コンポーネント

`frontend/src/components/GraphVisualization.tsx`:
```typescript
"use client";

import { useEffect, useRef } from "react";
import { Network } from "vis-network";

interface GraphVisualizationProps {
  nodes: any[];
  edges: any[];
}

export default function GraphVisualization({
  nodes,
  edges,
}: GraphVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const data = {
      nodes: nodes.map((n) => ({
        id: n.id,
        label: n.properties.title || n.properties.name,
        group: n.label,
      })),
      edges: edges.map((e) => ({
        from: e.source,
        to: e.target,
        label: e.type,
        arrows: "to",
      })),
    };

    const options = {
      nodes: {
        shape: "dot",
        size: 16,
      },
      physics: {
        forceAtlas2Based: {
          gravitationalConstant: -26,
          centralGravity: 0.005,
          springLength: 230,
          springConstant: 0.18,
        },
        maxVelocity: 146,
        solver: "forceAtlas2Based",
        timestep: 0.35,
        stabilization: { iterations: 150 },
      },
    };

    new Network(containerRef.current, data, options);
  }, [nodes, edges]);

  return <div ref={containerRef} style={{ height: "600px" }} />;
}
```

## 7. 実装チェックリスト

### Phase 2 - Step 1: Neo4j環境構築
- [ ] Docker Composeファイル作成
- [ ] Neo4jコンテナ起動
- [ ] Neo4jブラウザでアクセス確認
- [ ] APOCプラグインインストール確認

### Phase 2 - Step 2: グラフ構築サービス
- [ ] Neo4j Pythonドライバーインストール
- [ ] GraphServiceクラス実装
- [ ] エンティティ抽出ロジック実装
- [ ] リレーションシップ抽出ロジック実装
- [ ] 単体テスト作成

### Phase 2 - Step 3: グラフ分析サービス
- [ ] Cypherクエリ実装
- [ ] 循環依存検出機能
- [ ] 孤立要件検出機能
- [ ] 影響範囲分析機能
- [ ] 統計情報取得機能

### Phase 2 - Step 4: API実装
- [ ] /api/graph/build エンドポイント
- [ ] /api/graph/analyze エンドポイント
- [ ] /api/graph/visualize エンドポイント
- [ ] /api/review/enhanced エンドポイント
- [ ] APIドキュメント更新

### Phase 2 - Step 5: フロントエンド
- [ ] グラフ可視化ライブラリ選定・インストール
- [ ] GraphVisualizationコンポーネント実装
- [ ] グラフページ作成
- [ ] インタラクティブ機能実装
- [ ] レスポンシブ対応

### Phase 2 - Step 6: テストと最適化
- [ ] 統合テスト
- [ ] パフォーマンステスト
- [ ] 大規模データでの検証
- [ ] クエリ最適化
- [ ] ドキュメント更新

## 8. 参考資料

- [Neo4j Python Driver Documentation](https://neo4j.com/docs/python-manual/current/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [LlamaIndex GraphRAG](https://docs.llamaindex.ai/en/stable/examples/query_engine/knowledge_graph_query_engine/)
- [vis-network Documentation](https://visjs.github.io/vis-network/docs/network/)
