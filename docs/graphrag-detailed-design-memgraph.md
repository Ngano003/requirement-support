# GraphRAG実装 詳細設計書（Memgraph + LlamaIndex版）

## 目次

1. [概要](#概要)
2. [技術スタック選定理由](#技術スタック選定理由)
3. [アーキテクチャ](#アーキテクチャ)
4. [データモデル設計](#データモデル設計)
5. [LlamaIndex統合設計](#llamaindex統合設計)
6. [サービス層設計](#サービス層設計)
7. [API設計](#api設計)
8. [実装タスク](#実装タスク)
9. [環境構築](#環境構築)

---

## 概要

### 目的

LLMによるテキスト分析（フェーズ1）に加えて、**Memgraph + LlamaIndexによる知識グラフ分析**を導入し、レビュー精度を向上させます。

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

---

## 技術スタック選定理由

### Memgraph vs Neo4j

| 項目 | Memgraph | Neo4j |
|------|----------|-------|
| パフォーマンス | ⚡️ インメモリ、超高速 | ディスクベース |
| クエリ言語 | Cypher（互換） | Cypher |
| ライセンス | Community版が充実 | Community版は機能制限あり |
| Docker統合 | ✅ 軽量 | やや重い |
| リアルタイム分析 | ✅ ストリーム処理対応 | - |
| 学習曲線 | Neo4jと同じ | - |

**選定理由**:
- 開発環境での高速性
- Dockerでの軽量性
- Cypherクエリの互換性（Neo4jからの移行も容易）

### LlamaIndex vs 手動実装

| 項目 | LlamaIndex | 手動実装 |
|------|-----------|---------|
| エンティティ抽出 | ✅ 自動化 | プロンプト手動管理 |
| グラフ構築 | ✅ `PropertyGraphIndex` | 手動でノード/エッジ作成 |
| クエリ実行 | ✅ 自然言語対応 | Cypherクエリ手動作成 |
| LLM統合 | ✅ 既存LLM再利用可能 | 個別実装 |
| 保守性 | ✅ 高い | 低い |

**選定理由**:
- GraphRAGのベストプラクティスが組み込み済み
- エンティティ抽出の自動化
- 自然言語クエリによる柔軟な分析

---

## アーキテクチャ

### 全体構成

```
┌─────────────────────────────────────────────────────────────┐
│      要件定義レビューシステム（Memgraph + LlamaIndex版）      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Phase 1] LLMによるテキスト分析（並列実行）                 │
│  ┌────────────────────┬────────────────────┐                │
│  │ 抜け漏れ検出        │ 矛盾・不整合検出    │                │
│  └────────────────────┴────────────────────┘                │
│                          ↓                                  │
│  [Phase 2] GraphRAG（LlamaIndex + Memgraph）                │
│  ┌─────────────────────────────────────────────────┐        │
│  │ ① 知識グラフ構築（LlamaIndex）                   │        │
│  │    PropertyGraphIndex.from_documents()          │        │
│  │    - LLMによる自動エンティティ抽出               │        │
│  │    - 自動リレーションシップ推論                  │        │
│  │    - Memgraphへの保存                            │        │
│  ├─────────────────────────────────────────────────┤        │
│  │ ② グラフクエリ実行（Cypher + LlamaIndex）       │        │
│  │    - パターンマッチング（孤立要件、循環依存）    │        │
│  │    - 自然言語クエリ（LLMによる動的分析）         │        │
│  └─────────────────────────────────────────────────┘        │
│                          ↓                                  │
│  [Phase 3] 統合レポート生成                                  │
│  - LLM検出結果 + GraphRAG検出結果 → 統合JSON                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### LlamaIndexの役割

```
[要件定義書テキスト]
        ↓
┌───────────────────────────┐
│  LlamaIndex処理フロー      │
├───────────────────────────┤
│ 1. Document作成            │
│    ↓                      │
│ 2. PropertyGraphIndex     │
│    - LLMでエンティティ抽出 │
│    - 関係性の自動推論      │
│    ↓                      │
│ 3. Memgraphに保存         │
│    ↓                      │
│ 4. クエリ実行              │
│    - Cypherクエリ          │
│    - 自然言語クエリ        │
└───────────────────────────┘
```

---

## データモデル設計

### ノードタイプ

LlamaIndexは自動的にエンティティを抽出しますが、抽出の精度を高めるため、**エンティティスキーマを定義**します。

#### エンティティタイプ定義

```python
from llama_index.core.graph_stores.types import EntityNode, Relation

# エンティティタイプ
ENTITY_TYPES = [
    "Requirement",      # 要件
    "Function",         # 機能
    "Data",            # データエンティティ
    "User",            # ユーザー種別
    "Constraint",      # 制約条件
]

# リレーションタイプ
RELATION_TYPES = [
    "DEPENDS_ON",      # 依存関係
    "CONFLICTS_WITH",  # 矛盾関係
    "USES",            # 使用関係
    "REQUIRES",        # 要求関係
    "IMPLEMENTS",      # 実装関係
    "USED_BY",         # 利用関係
]
```

#### プロパティ定義

LlamaIndexは柔軟なプロパティをサポートします：

```python
# 要件ノード
{
    "entity_type": "Requirement",
    "title": "ユーザー認証機能",
    "description": "...",
    "req_type": "functional",  # functional | non_functional
    "source_section": "機能要件",
    "priority": "high"
}

# 機能ノード
{
    "entity_type": "Function",
    "name": "ログイン機能",
    "description": "...",
    "inputs": ["メールアドレス", "パスワード"],
    "outputs": ["ログイン結果"]
}
```

---

## LlamaIndex統合設計

### 1. PropertyGraphIndex設定

```python
from llama_index.core import PropertyGraphIndex, Document
from llama_index.core.graph_stores import MemgraphPropertyGraphStore
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding

# Memgraphストア設定
graph_store = MemgraphPropertyGraphStore(
    url="bolt://memgraph:7687",
    username="",
    password="",
    database="memgraph",
)

# LLM設定（既存のOpenRouter/vLLMを使用）
llm = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    api_base=settings.OPENROUTER_API_BASE,
    model=settings.OPENROUTER_MODEL,
)

# PropertyGraphIndex作成
index = PropertyGraphIndex.from_documents(
    documents=[Document(text=requirements_text)],
    llm=llm,
    graph_store=graph_store,
    # エンティティ抽出設定
    kg_extractors=[
        # SimpleLLMPathExtractor: LLMでエンティティとパスを抽出
        SimpleLLMPathExtractor(
            llm=llm,
            max_paths_per_chunk=10,
            num_workers=4,
        )
    ],
    show_progress=True,
)
```

### 2. エンティティ抽出のカスタマイズ

LlamaIndexのデフォルト抽出を、要件定義に特化させます：

```python
from llama_index.core.extractors import (
    SummaryExtractor,
    QuestionsAnsweredExtractor,
    KeywordExtractor,
)
from llama_index.core.schema import MetadataMode

# 要件定義専用のプロンプトテンプレート
ENTITY_EXTRACTION_PROMPT = """
以下のテキストから、要件定義に関連するエンティティを抽出してください。

エンティティタイプ:
- Requirement: 要件項目
- Function: 機能
- Data: データエンティティ
- User: ユーザー種別
- Constraint: 制約条件

リレーションタイプ:
- DEPENDS_ON: 依存関係
- USES: 使用関係
- REQUIRES: 要求関係
- IMPLEMENTS: 実装関係
- USED_BY: 利用関係

テキスト:
{text}

以下の形式でエンティティとリレーションを出力してください:
```json
{{
  "entities": [
    {{"type": "Requirement", "name": "...", "properties": {{...}}}}
  ],
  "relations": [
    {{"source": "...", "type": "DEPENDS_ON", "target": "..."}}
  ]
}}
```
"""

# カスタム抽出器
class RequirementKGExtractor:
    """要件定義専用のKG抽出器"""

    def __init__(self, llm):
        self.llm = llm

    async def extract(self, nodes):
        """ノードからエンティティとリレーションを抽出"""
        results = []
        for node in nodes:
            text = node.get_content(metadata_mode=MetadataMode.LLM)

            # LLMでエンティティ抽出
            response = await self.llm.acomplete(
                ENTITY_EXTRACTION_PROMPT.format(text=text)
            )

            # パース
            data = self._parse_response(response.text)
            results.append(data)

        return results
```

### 3. クエリ実行

#### 方法1: Cypherクエリ（構造化検出）

```python
# 孤立要件の検出
query = """
MATCH (r:Requirement)
WHERE NOT (r)-[]-()
RETURN r.title, r.description
"""

results = graph_store.query(query)
```

#### 方法2: 自然言語クエリ（LLMによる動的分析）

```python
# QueryEngineで自然言語クエリ
query_engine = index.as_query_engine(
    include_text=True,
    response_mode="tree_summarize",
)

# 自然言語で質問
response = query_engine.query(
    "要件間に循環依存はありますか？具体的にどの要件が関係していますか？"
)

print(response.response)
```

---

## サービス層設計

### 1. GraphRAGService（新規作成）

```python
# backend/app/services/graphrag_service.py

import logging
from typing import List, Dict, Any, Optional
from llama_index.core import PropertyGraphIndex, Document
from llama_index.core.graph_stores import MemgraphPropertyGraphStore
from llama_index.llms.openrouter import OpenRouter
from app.utils.config import settings
from app.models.schemas import (
    GraphAnalysisResult,
    GraphMissingItem,
    GraphContradiction,
)

logger = logging.getLogger(__name__)


class GraphRAGService:
    """Memgraph + LlamaIndexによるGraphRAGサービス"""

    def __init__(self):
        # Memgraphストア
        self.graph_store = MemgraphPropertyGraphStore(
            url=settings.MEMGRAPH_URL,
            username=settings.MEMGRAPH_USER,
            password=settings.MEMGRAPH_PASSWORD,
        )

        # LLM設定（既存のOpenRouter/vLLM）
        self.llm = self._create_llm()

    def _create_llm(self):
        """LLMインスタンスを作成"""
        if settings.LLM_PROVIDER == "openrouter":
            return OpenRouter(
                api_key=settings.OPENROUTER_API_KEY,
                model=settings.OPENROUTER_MODEL,
            )
        else:
            # vLLMの場合
            from llama_index.llms.openai import OpenAI
            return OpenAI(
                api_key="dummy",
                api_base=settings.VLLM_API_BASE,
                model=settings.VLLM_MODEL,
            )

    async def analyze_requirements(
        self, requirements_text: str, session_id: str
    ) -> GraphAnalysisResult:
        """
        要件定義書をグラフ分析

        Args:
            requirements_text: 要件定義書
            session_id: セッションID

        Returns:
            GraphAnalysisResult
        """
        try:
            # 1. 既存のグラフをクリア
            await self._clear_graph(session_id)

            # 2. PropertyGraphIndexでグラフ構築
            index = await self._build_graph(requirements_text, session_id)

            # 3. パターンマッチングで問題検出
            missing_items = await self._detect_missing_items(session_id)
            contradictions = await self._detect_contradictions(session_id)

            return GraphAnalysisResult(
                missing_items=missing_items,
                contradictions=contradictions,
            )

        except Exception as e:
            logger.error(f"GraphRAG analysis error: {e}", exc_info=True)
            return GraphAnalysisResult(missing_items=[], contradictions=[])

    async def _clear_graph(self, session_id: str):
        """セッションのグラフをクリア"""
        query = "MATCH (n {session_id: $session_id}) DETACH DELETE n"
        self.graph_store.query(query, {"session_id": session_id})

    async def _build_graph(
        self, requirements_text: str, session_id: str
    ) -> PropertyGraphIndex:
        """PropertyGraphIndexでグラフ構築"""
        # ドキュメント作成
        doc = Document(
            text=requirements_text,
            metadata={"session_id": session_id},
        )

        # PropertyGraphIndexでグラフ構築
        index = PropertyGraphIndex.from_documents(
            documents=[doc],
            llm=self.llm,
            graph_store=self.graph_store,
            kg_extractors=[
                # カスタム抽出器を使用
                RequirementKGExtractor(self.llm)
            ],
            show_progress=False,
        )

        return index

    async def _detect_missing_items(self, session_id: str) -> List[GraphMissingItem]:
        """抜け漏れを検出"""
        items = []

        # 1. 孤立要件
        isolated = self._query_isolated_requirements(session_id)
        for req in isolated:
            items.append(
                GraphMissingItem(
                    type="isolated_requirement",
                    item=req["title"],
                    description=f"要件「{req['title']}」が孤立しています",
                    severity="medium",
                    suggestion="関連する機能や要件を明記してください",
                )
            )

        # 2. 未定義データ
        missing_data = self._query_missing_data(session_id)
        for func in missing_data:
            items.append(
                GraphMissingItem(
                    type="missing_data_definition",
                    item=func["name"],
                    description=f"機能「{func['name']}」が使用するデータが未定義",
                    severity="high",
                    suggestion="データエンティティを定義してください",
                )
            )

        # 3. ユーザー不在の機能
        no_user = self._query_functions_without_users(session_id)
        for func in no_user:
            items.append(
                GraphMissingItem(
                    type="missing_user",
                    item=func["name"],
                    description=f"機能「{func['name']}」を使用するユーザーが未定義",
                    severity="medium",
                    suggestion="対象ユーザーを追加してください",
                )
            )

        return items

    async def _detect_contradictions(self, session_id: str) -> List[GraphContradiction]:
        """矛盾を検出"""
        contradictions = []

        # 1. 循環依存
        cycles = self._query_circular_dependencies(session_id)
        for cycle in cycles:
            contradictions.append(
                GraphContradiction(
                    type="circular_dependency",
                    description=f"要件「{cycle['title']}」に循環依存",
                    items=cycle["path"],
                    severity="high",
                    suggestion="依存関係を見直してください",
                )
            )

        # 2. 矛盾する制約
        conflicts = self._query_conflicting_constraints(session_id)
        for conflict in conflicts:
            contradictions.append(
                GraphContradiction(
                    type="conflicting_constraint",
                    description=f"データ「{conflict['data']}」に矛盾する制約",
                    items=[conflict["constraint1"], conflict["constraint2"]],
                    severity="high",
                    suggestion="制約を統一してください",
                )
            )

        return contradictions

    def _query_isolated_requirements(self, session_id: str) -> List[Dict]:
        """孤立要件を検出するCypherクエリ"""
        query = """
        MATCH (r:Requirement {session_id: $session_id})
        WHERE NOT (r)-[]-()
        RETURN r.title AS title, r.description AS description
        """
        return self.graph_store.query(query, {"session_id": session_id})

    def _query_missing_data(self, session_id: str) -> List[Dict]:
        """未定義データを検出"""
        query = """
        MATCH (f:Function {session_id: $session_id})
        WHERE NOT EXISTS {
            MATCH (f)-[:USES]->(d:Data)
        }
        RETURN f.name AS name
        """
        return self.graph_store.query(query, {"session_id": session_id})

    def _query_functions_without_users(self, session_id: str) -> List[Dict]:
        """ユーザー不在の機能を検出"""
        query = """
        MATCH (f:Function {session_id: $session_id})
        WHERE NOT EXISTS {
            MATCH (u:User)-[:USES]->(f)
        }
        RETURN f.name AS name
        """
        return self.graph_store.query(query, {"session_id": session_id})

    def _query_circular_dependencies(self, session_id: str) -> List[Dict]:
        """循環依存を検出"""
        query = """
        MATCH path = (r:Requirement {session_id: $session_id})-[:DEPENDS_ON*]->(r)
        RETURN r.title AS title,
               [n IN nodes(path) | n.title] AS path
        """
        return self.graph_store.query(query, {"session_id": session_id})

    def _query_conflicting_constraints(self, session_id: str) -> List[Dict]:
        """矛盾する制約を検出"""
        query = """
        MATCH (f1:Function {session_id: $session_id})-[:USES]->(d:Data)<-[:USES]-(f2:Function)
        MATCH (f1)-[:REQUIRES]->(c1:Constraint)
        MATCH (f2)-[:REQUIRES]->(c2:Constraint)
        WHERE c1.target = c2.target
          AND c1.description <> c2.description
          AND id(f1) < id(f2)
        RETURN d.name AS data,
               c1.description AS constraint1,
               c2.description AS constraint2
        """
        return self.graph_store.query(query, {"session_id": session_id})


# シングルトンインスタンス
graphrag_service: Optional[GraphRAGService] = None


def init_graphrag_service():
    """GraphRAGServiceを初期化"""
    global graphrag_service
    graphrag_service = GraphRAGService()


async def close_graphrag_service():
    """GraphRAGServiceをクローズ"""
    # Memgraphストアのクローズ
    pass
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
  "review_id": "uuid",
  "session_id": "uuid",
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
        "suggestion": "関連機能を明記してください"
      }
    ],
    "contradictions": [ ... ]
  },
  "summary": { ... }
}
```

---

## 実装タスク

### タスク1: 環境構築（1日）

**docker-compose.memgraph.yml**:

```yaml
version: '3.8'

services:
  memgraph:
    image: memgraph/memgraph:latest
    container_name: requirement-support-memgraph
    ports:
      - "7687:7687"
      - "7444:7444"  # Memgraph Lab
    environment:
      - MEMGRAPH_USER=
      - MEMGRAPH_PASSWORD=
    volumes:
      - memgraph_data:/var/lib/memgraph
    networks:
      - requirement-support-network

volumes:
  memgraph_data:

networks:
  requirement-support-network:
    external: true
```

**Pythonパッケージ**:

```txt
# backend/requirements.txt に追加
llama-index-core==0.12.0
llama-index-llms-openrouter==0.2.0
llama-index-graph-stores-memgraph==0.1.0
pymgclient==1.3.1
```

### タスク2: データモデル追加（1-2時間）

[schemas.py](backend/app/models/schemas.py)に追加:

```python
class GraphMissingItem(BaseModel):
    """グラフ分析による抜け漏れ"""
    type: Literal["isolated_requirement", "missing_data_definition", "missing_user"]
    item: str
    description: str
    severity: Literal["high", "medium", "low"]
    suggestion: str


class GraphContradiction(BaseModel):
    """グラフ分析による矛盾"""
    type: Literal["circular_dependency", "conflicting_constraint"]
    description: str
    items: List[str]
    severity: Literal["high", "medium"]
    suggestion: str


class GraphAnalysisResult(BaseModel):
    """グラフ分析結果"""
    missing_items: List[GraphMissingItem] = Field(default_factory=list)
    contradictions: List[GraphContradiction] = Field(default_factory=list)
```

### タスク3: GraphRAGService実装（4-6時間）

- [ ] `GraphRAGService` クラス実装
- [ ] LlamaIndex統合
- [ ] カスタムエンティティ抽出器実装
- [ ] Cypherクエリ実装

### タスク4: 統合API実装（2-3時間）

- [ ] `POST /api/review/with-graph` エンドポイント
- [ ] LLM分析とGraphRAG分析の統合

### タスク5: テスト（3-4時間）

- [ ] GraphRAGServiceのユニットテスト
- [ ] 統合テスト

---

## 環境構築

### 1. Memgraph起動

```bash
docker-compose -f docker-compose.memgraph.yml up -d
```

### 2. Memgraph Lab（WebUI）

ブラウザで `http://localhost:7444` にアクセス

### 3. 環境変数設定

```env
# backend/.env
MEMGRAPH_URL=bolt://memgraph:7687
MEMGRAPH_USER=
MEMGRAPH_PASSWORD=

# LLM設定（既存）
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-key
OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct
```

### 4. パッケージインストール

```bash
cd backend
pip install llama-index-core llama-index-llms-openrouter llama-index-graph-stores-memgraph pymgclient
```

---

## パフォーマンス最適化

### 並列実行

```python
# LLM分析とGraphRAG分析を並列実行
llm_task = review_service.review_requirements_enhanced(requirements_text)
graph_task = graphrag_service.analyze_requirements(requirements_text, session_id)

llm_result, graph_result = await asyncio.gather(llm_task, graph_task)
```

### Memgraphインデックス

```cypher
CREATE INDEX ON :Requirement(id);
CREATE INDEX ON :Function(id);
CREATE INDEX ON :Data(id);
```

---

## 総工数見積もり

| タスク | 工数 |
|--------|------|
| 環境構築 | 1日 |
| データモデル追加 | 1-2時間 |
| GraphRAGService実装 | 4-6時間 |
| 統合API実装 | 2-3時間 |
| テスト | 3-4時間 |
| **合計** | **2-3日** |

---

## Memgraph vs Neo4j 移行

Cypherクエリは互換性があるため、将来Neo4jに切り替える場合も容易です：

```python
# Memgraph
from llama_index.graph_stores.memgraph import MemgraphPropertyGraphStore

# Neo4j（切り替え時）
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
```

---

## 参考資料

### Memgraph

- [Memgraph Documentation](https://memgraph.com/docs)
- [Memgraph Cypher Manual](https://memgraph.com/docs/cypher-manual)

### LlamaIndex

- [LlamaIndex PropertyGraph](https://docs.llamaindex.ai/en/stable/examples/property_graph/)
- [Graph Stores](https://docs.llamaindex.ai/en/stable/module_guides/storing/graph_stores/)

### GraphRAG

- [Microsoft GraphRAG](https://microsoft.github.io/graphrag/)
