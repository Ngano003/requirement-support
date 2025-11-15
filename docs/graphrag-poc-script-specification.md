# GraphRAGレビュー機能 実現性検討スクリプト仕様書

## 目次

1. [概要](#概要)
2. [目的](#目的)
3. [スクリプト構成](#スクリプト構成)
4. [詳細仕様](#詳細仕様)
5. [実行フロー](#実行フロー)
6. [入出力仕様](#入出力仕様)
7. [環境設定](#環境設定)

---

## 概要

### スクリプトの目的

GraphRAG（Memgraph + LLM）を使った要件定義レビュー機能の**実現性を検証**するPythonスクリプトを作成します。

### 検証する項目

1. ✅ **エンティティ抽出の精度**
   - LLM（OpenAI API / vLLM API）がスキーマに従ってエンティティを抽出できるか

2. ✅ **グラフ構築の正確性**
   - 抽出されたエンティティをMemgraphに正しく保存できるか

3. ✅ **問題検出の有効性**
   - Cypherクエリで実際にヌケモレ・矛盾を検出できるか

4. ✅ **処理時間の測定**
   - 実用的な速度で動作するか

### スコープ

- ✅ 単体で動作する検証用スクリプト
- ✅ サンプル要件定義書を使用
- ✅ 結果をコンソールとファイルに出力
- ❌ 本番システムへの統合は含まない（PoC段階）

---

## スクリプト構成

### ファイル構成

```
backend/scripts/
├── graphrag_poc.py              # メインスクリプト
├── config.py                    # 設定（LLM, Memgraph接続情報）
├── entity_extractor.py          # エンティティ抽出ロジック
├── graph_builder.py             # Memgraphへのグラフ構築
├── problem_detector.py          # 問題検出ロジック
├── samples/
│   ├── sample_requirements_1.md # サンプル要件定義（正常系）
│   ├── sample_requirements_2.md # サンプル要件定義（ヌケモレあり）
│   └── sample_requirements_3.md # サンプル要件定義（矛盾あり）
└── output/
    ├── extracted_entities.json  # 抽出結果
    ├── detection_results.json   # 検出結果
    └── performance_metrics.json # パフォーマンス測定結果
```

---

## 詳細仕様

### 1. メインスクリプト（graphrag_poc.py）

#### 責務
- 全体のフロー制御
- 各モジュールの呼び出し
- 結果の出力

#### 主要機能

```python
class GraphRAGPoC:
    """GraphRAG実現性検証スクリプト"""

    def __init__(self, config: Config):
        self.config = config
        self.entity_extractor = EntityExtractor(config)
        self.graph_builder = GraphBuilder(config)
        self.problem_detector = ProblemDetector(config)

    async def run(self, requirements_file: str):
        """
        検証を実行

        Args:
            requirements_file: 要件定義書ファイルパス

        Returns:
            検証結果（dict）
        """
        # 1. 要件定義書を読み込み
        requirements_text = self._load_requirements(requirements_file)

        # 2. エンティティ抽出（LLM使用）
        print("[1/4] エンティティ抽出中...")
        extraction_result = await self.entity_extractor.extract(requirements_text)

        # 3. グラフ構築（Memgraphに保存）
        print("[2/4] グラフ構築中...")
        session_id = self._generate_session_id()
        await self.graph_builder.build_graph(
            session_id=session_id,
            entities=extraction_result['entities'],
            relations=extraction_result['relations']
        )

        # 4. 問題検出（Cypherクエリ実行）
        print("[3/4] 問題検出中...")
        detection_result = await self.problem_detector.detect_all(session_id)

        # 5. 結果の集計・出力
        print("[4/4] 結果出力中...")
        result = self._generate_report(
            extraction_result,
            detection_result
        )

        return result

    def _load_requirements(self, file_path: str) -> str:
        """要件定義書を読み込み"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _generate_session_id(self) -> str:
        """セッションIDを生成"""
        import uuid
        return f"poc-{uuid.uuid4()}"

    def _generate_report(self, extraction, detection) -> dict:
        """検証結果レポートを生成"""
        return {
            "extraction": {
                "entities_count": len(extraction['entities']),
                "relations_count": len(extraction['relations']),
                "validation_errors": extraction['validation_errors'],
            },
            "detection": {
                "missing_items": detection['missing_items'],
                "contradictions": detection['contradictions'],
            },
            "performance": {
                "extraction_time": extraction['elapsed_time'],
                "detection_time": detection['elapsed_time'],
            }
        }
```

---

### 2. 設定モジュール（config.py）

#### 責務
- LLM API設定
- Memgraph接続設定
- スキーマ定義の読み込み

#### 設定項目

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class LLMConfig:
    """LLM設定"""
    provider: Literal["openai", "vllm"]

    # OpenAI API設定
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"

    # vLLM API設定
    vllm_api_base: str = "http://localhost:8000/v1"
    vllm_model: str = "Qwen/Qwen2.5-Coder-32B-Instruct"

    # 共通設定
    temperature: float = 0.2
    max_tokens: int = 4096

@dataclass
class MemgraphConfig:
    """Memgraph設定"""
    url: str = "bolt://localhost:7687"
    username: str = ""
    password: str = ""
    database: str = "memgraph"

@dataclass
class Config:
    """全体設定"""
    llm: LLMConfig
    memgraph: MemgraphConfig
    schema_file: str = "backend/app/schemas/knowledge_graph_schema.py"
    output_dir: str = "backend/scripts/output"


def load_config_from_env() -> Config:
    """環境変数から設定を読み込み"""
    import os

    llm_provider = os.getenv("LLM_PROVIDER", "openai")

    llm_config = LLMConfig(
        provider=llm_provider,
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_api_base=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
        vllm_api_base=os.getenv("VLLM_API_BASE", "http://localhost:8000/v1"),
        vllm_model=os.getenv("VLLM_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct"),
    )

    memgraph_config = MemgraphConfig(
        url=os.getenv("MEMGRAPH_URL", "bolt://localhost:7687"),
        username=os.getenv("MEMGRAPH_USER", ""),
        password=os.getenv("MEMGRAPH_PASSWORD", ""),
    )

    return Config(llm=llm_config, memgraph=memgraph_config)
```

---

### 3. エンティティ抽出モジュール（entity_extractor.py）

#### 責務
- LLM APIを呼び出してエンティティを抽出
- スキーマに基づいたバリデーション
- 処理時間の測定

#### 主要機能

```python
import time
import json
from openai import AsyncOpenAI

class EntityExtractor:
    """エンティティ抽出器（LLM使用）"""

    def __init__(self, config: Config):
        self.config = config
        self.client = self._create_llm_client()
        self.schema = self._load_schema()

    def _create_llm_client(self) -> AsyncOpenAI:
        """LLMクライアントを作成"""
        if self.config.llm.provider == "openai":
            return AsyncOpenAI(
                api_key=self.config.llm.openai_api_key,
                base_url=self.config.llm.openai_api_base,
            )
        else:  # vllm
            return AsyncOpenAI(
                api_key="dummy",
                base_url=self.config.llm.vllm_api_base,
            )

    def _load_schema(self) -> dict:
        """スキーマ定義を読み込み"""
        # backend/app/schemas/knowledge_graph_schema.py から読み込み
        import sys
        sys.path.insert(0, "backend")
        from app.schemas.knowledge_graph_schema import (
            ENTITY_TYPES,
            RELATION_TYPES,
        )
        return {
            "entity_types": ENTITY_TYPES,
            "relation_types": RELATION_TYPES,
        }

    async def extract(self, requirements_text: str) -> dict:
        """
        エンティティとリレーションを抽出

        Returns:
            {
                "entities": [...],
                "relations": [...],
                "validation_errors": [...],
                "elapsed_time": 1.23,  # 秒
            }
        """
        start_time = time.time()

        # プロンプト構築
        prompt = self._build_prompt(requirements_text)

        # LLM呼び出し
        response = await self._call_llm(prompt)

        # JSONパース
        data = self._parse_json(response)

        # バリデーション
        validated = self._validate(data)

        elapsed_time = time.time() - start_time
        validated['elapsed_time'] = elapsed_time

        return validated

    def _build_prompt(self, requirements_text: str) -> str:
        """プロンプトを構築"""
        # app/prompts/entity_extraction_prompt.py のロジックを使用
        from app.prompts.entity_extraction_prompt import (
            build_entity_extraction_prompt
        )
        return build_entity_extraction_prompt(requirements_text)

    async def _call_llm(self, prompt: str) -> str:
        """LLM APIを呼び出し"""
        model = (
            self.config.llm.openai_model
            if self.config.llm.provider == "openai"
            else self.config.llm.vllm_model
        )

        response = await self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたは要件定義書から構造化された知識グラフを構築する専門家です。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
        )

        return response.choices[0].message.content

    def _parse_json(self, json_str: str) -> dict:
        """JSON文字列をパース"""
        # コードブロック除去
        json_str = json_str.strip()
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        elif json_str.startswith("```"):
            json_str = json_str[3:]
        if json_str.endswith("```"):
            json_str = json_str[:-3]
        json_str = json_str.strip()

        return json.loads(json_str)

    def _validate(self, data: dict) -> dict:
        """バリデーション（app/services/entity_extractor.py のロジック使用）"""
        # 簡略化版: 必須フィールドのみチェック
        validated_entities = []
        validated_relations = []
        errors = []

        for entity in data.get("entities", []):
            if all(k in entity for k in ["type", "id", "properties"]):
                validated_entities.append(entity)
            else:
                errors.append(f"Invalid entity: {entity}")

        entity_ids = {e["id"] for e in validated_entities}

        for relation in data.get("relations", []):
            if (
                all(k in relation for k in ["type", "source_id", "target_id"])
                and relation["source_id"] in entity_ids
                and relation["target_id"] in entity_ids
            ):
                validated_relations.append(relation)
            else:
                errors.append(f"Invalid relation: {relation}")

        return {
            "entities": validated_entities,
            "relations": validated_relations,
            "validation_errors": errors,
        }
```

---

### 4. グラフ構築モジュール（graph_builder.py）

#### 責務
- Memgraphへの接続
- ノードとエッジの作成
- セッション管理

#### 主要機能

```python
from neo4j import AsyncGraphDatabase

class GraphBuilder:
    """Memgraphグラフ構築器"""

    def __init__(self, config: Config):
        self.config = config
        self.driver = AsyncGraphDatabase.driver(
            self.config.memgraph.url,
            auth=(
                self.config.memgraph.username,
                self.config.memgraph.password,
            ),
        )

    async def build_graph(
        self, session_id: str, entities: list, relations: list
    ):
        """
        グラフを構築

        Args:
            session_id: セッションID
            entities: エンティティリスト
            relations: リレーションリスト
        """
        async with self.driver.session(database=self.config.memgraph.database) as session:
            # 既存データをクリア
            await self._clear_session(session, session_id)

            # ノード作成
            await self._create_nodes(session, session_id, entities)

            # エッジ作成
            await self._create_edges(session, session_id, relations)

    async def _clear_session(self, session, session_id: str):
        """セッションのグラフをクリア"""
        await session.run(
            "MATCH (n {session_id: $session_id}) DETACH DELETE n",
            session_id=session_id,
        )

    async def _create_nodes(self, session, session_id: str, entities: list):
        """ノードを作成"""
        for entity in entities:
            node_type = entity["type"]
            properties = entity["properties"].copy()
            properties["session_id"] = session_id
            properties["id"] = entity["id"]

            query = f"CREATE (n:{node_type} $properties)"
            await session.run(query, properties=properties)

    async def _create_edges(self, session, session_id: str, relations: list):
        """エッジを作成"""
        for relation in relations:
            rel_type = relation["type"]
            source_id = relation["source_id"]
            target_id = relation["target_id"]
            properties = relation.get("properties", {})

            query = f"""
            MATCH (a {{id: $source_id, session_id: $session_id}})
            MATCH (b {{id: $target_id, session_id: $session_id}})
            CREATE (a)-[r:{rel_type} $properties]->(b)
            """

            await session.run(
                query,
                source_id=source_id,
                target_id=target_id,
                session_id=session_id,
                properties=properties,
            )

    async def close(self):
        """ドライバーをクローズ"""
        await self.driver.close()
```

---

### 5. 問題検出モジュール（problem_detector.py）

#### 責務
- Cypherクエリで問題を検出
- 検出結果の構造化
- 処理時間の測定

#### 主要機能

```python
import time

class ProblemDetector:
    """問題検出器（Cypherクエリ使用）"""

    def __init__(self, config: Config):
        self.config = config
        self.driver = AsyncGraphDatabase.driver(
            self.config.memgraph.url,
            auth=(
                self.config.memgraph.username,
                self.config.memgraph.password,
            ),
        )

    async def detect_all(self, session_id: str) -> dict:
        """
        すべての問題を検出

        Returns:
            {
                "missing_items": [...],
                "contradictions": [...],
                "elapsed_time": 0.5,
            }
        """
        start_time = time.time()

        async with self.driver.session(database=self.config.memgraph.database) as session:
            # ヌケモレ検出
            missing = await self._detect_missing_items(session, session_id)

            # 矛盾検出
            contradictions = await self._detect_contradictions(session, session_id)

        elapsed_time = time.time() - start_time

        return {
            "missing_items": missing,
            "contradictions": contradictions,
            "elapsed_time": elapsed_time,
        }

    async def _detect_missing_items(self, session, session_id: str) -> list:
        """ヌケモレを検出"""
        results = []

        # 1. 利用されない機能
        unused_functions = await self._query(
            session,
            session_id,
            """
            MATCH (f:Function {session_id: $session_id})
            WHERE NOT EXISTS {
                MATCH (a:Actor)-[:USES]->(f)
            }
            RETURN f.name AS function_name
            """,
        )
        for record in unused_functions:
            results.append({
                "type": "unused_function",
                "item": record["function_name"],
                "severity": "medium",
                "description": f"機能「{record['function_name']}」が誰にも利用されていません",
            })

        # 2. セキュリティ要件の漏れ
        missing_security = await self._query(
            session,
            session_id,
            """
            MATCH (d:Data {session_id: $session_id})
            WHERE (d.sensitivity = 'confidential' OR d.name CONTAINS '個人情報')
            AND NOT EXISTS {
                MATCH (r:Requirement {type: 'Security'})-[:APPLIES_TO]->(d)
            }
            RETURN d.name AS data_name
            """,
        )
        for record in missing_security:
            results.append({
                "type": "missing_security_requirement",
                "item": record["data_name"],
                "severity": "high",
                "description": f"機密データ「{record['data_name']}」にセキュリティ要件が適用されていません",
            })

        # 3. 孤立データ
        orphan_data = await self._query(
            session,
            session_id,
            """
            MATCH (d:Data {session_id: $session_id})
            WHERE NOT EXISTS {
                MATCH (f:Function)-[:MANIPULATES]->(d)
            }
            RETURN d.name AS data_name
            """,
        )
        for record in orphan_data:
            results.append({
                "type": "orphan_data",
                "item": record["data_name"],
                "severity": "medium",
                "description": f"データ「{record['data_name']}」がどの機能からも操作されていません",
            })

        return results

    async def _detect_contradictions(self, session, session_id: str) -> list:
        """矛盾を検出"""
        results = []

        # 1. 循環依存
        circular_deps = await self._query(
            session,
            session_id,
            """
            MATCH path = (f:Function {session_id: $session_id})-[:DEPENDS_ON*]->(f)
            RETURN f.name AS function_name,
                   [n IN nodes(path) | n.name] AS cycle_path
            LIMIT 10
            """,
        )
        for record in circular_deps:
            results.append({
                "type": "circular_dependency",
                "items": record["cycle_path"],
                "severity": "high",
                "description": f"循環依存が検出されました: {' → '.join(record['cycle_path'])}",
            })

        # 2. 権限の競合
        permission_conflicts = await self._query(
            session,
            session_id,
            """
            MATCH (a:Actor {session_id: $session_id})-[r1:AUTHORIZES {permission: 'Allow'}]->(f:Function),
                  (a)-[r2:AUTHORIZES {permission: 'Deny'}]->(f)
            RETURN a.name AS actor_name, f.name AS function_name
            """,
        )
        for record in permission_conflicts:
            results.append({
                "type": "permission_conflict",
                "items": [record["actor_name"], record["function_name"]],
                "severity": "high",
                "description": f"Actor「{record['actor_name']}」がFunction「{record['function_name']}」に対してAllowとDenyの両方を持っています",
            })

        return results

    async def _query(self, session, session_id: str, query: str) -> list:
        """Cypherクエリを実行"""
        result = await session.run(query, session_id=session_id)
        records = await result.data()
        return records

    async def close(self):
        """ドライバーをクローズ"""
        await self.driver.close()
```

---

## 実行フロー

### シーケンス図

```
[ユーザー]
    ↓
[graphrag_poc.py]
    ↓
[1] 要件定義書読み込み
    ↓
[2] EntityExtractor.extract()
    ↓ (LLM API呼び出し)
[OpenAI/vLLM API]
    ↓ (JSON返却)
[EntityExtractor] → バリデーション → entities, relations
    ↓
[3] GraphBuilder.build_graph()
    ↓ (Cypher CREATE)
[Memgraph]
    ↓
[4] ProblemDetector.detect_all()
    ↓ (Cypher MATCH)
[Memgraph] → missing_items, contradictions
    ↓
[5] レポート生成・出力
    ↓
[output/*.json]
```

---

## 入出力仕様

### 入力

#### 1. 要件定義書（Markdown）

```markdown
# システム概要
書籍予約システム

## 対象ユーザー
- 一般ユーザー: 書籍の検索・予約が可能
- 管理者: ユーザー管理が可能

## 機能要件

### ログイン機能
ユーザーはメールアドレスとパスワードでログインできる。
ユーザー情報を参照してログイン認証を行う。

## 非機能要件
ユーザー情報は暗号化して保存すること。
```

### 出力

#### 1. extracted_entities.json

```json
{
  "entities": [
    {
      "type": "Actor",
      "id": "ACTOR-001",
      "properties": {
        "name": "一般ユーザー"
      }
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
  "validation_errors": [],
  "elapsed_time": 1.23
}
```

#### 2. detection_results.json

```json
{
  "missing_items": [
    {
      "type": "unused_function",
      "item": "ユーザー管理機能",
      "severity": "medium",
      "description": "機能「ユーザー管理機能」が誰にも利用されていません"
    }
  ],
  "contradictions": [
    {
      "type": "circular_dependency",
      "items": ["機能A", "機能B", "機能A"],
      "severity": "high",
      "description": "循環依存が検出されました: 機能A → 機能B → 機能A"
    }
  ],
  "elapsed_time": 0.5
}
```

#### 3. performance_metrics.json

```json
{
  "extraction_time_sec": 1.23,
  "graph_build_time_sec": 0.15,
  "detection_time_sec": 0.5,
  "total_time_sec": 1.88,
  "entities_count": 8,
  "relations_count": 12,
  "problems_found": 3
}
```

---

## 環境設定

### 必要なパッケージ

```txt
# requirements-poc.txt
openai>=1.0.0
neo4j>=5.14.0
python-dotenv>=1.0.0
```

### 環境変数（.env.poc）

```env
# LLM設定
LLM_PROVIDER=openai  # または vllm
OPENAI_API_KEY=sk-...
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL=gpt-4

# vLLM設定（LLM_PROVIDER=vllm の場合）
VLLM_API_BASE=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct

# Memgraph設定
MEMGRAPH_URL=bolt://localhost:7687
MEMGRAPH_USER=
MEMGRAPH_PASSWORD=
```

### 実行コマンド

```bash
# 環境変数を読み込み
export $(cat .env.poc | xargs)

# スクリプト実行
cd backend/scripts
python graphrag_poc.py samples/sample_requirements_1.md

# 結果確認
cat output/detection_results.json
```

---

## 成功基準

### 機能面

- ✅ エンティティが正しく抽出される（精度80%以上）
- ✅ グラフがMemgraphに正しく保存される
- ✅ 問題が正しく検出される（False Positive < 20%）

### 性能面

- ✅ 1000行の要件定義書を5秒以内に処理
- ✅ 抽出時間 < 3秒
- ✅ 検出時間 < 1秒

### 品質面

- ✅ バリデーションエラー率 < 10%
- ✅ JSONパースエラーなし
- ✅ Memgraph接続エラーなし

---

## まとめ

このスクリプトにより、以下を検証できます：

1. **技術的実現性**: LLM + Memgraphで実際に動作するか
2. **検出精度**: 実用的なレベルで問題を検出できるか
3. **処理速度**: 実用的な速度で動作するか

検証結果を基に、本番システムへの統合を判断します。
