# GraphRAG PoC スクリプト

GraphRAG（Memgraph + LLM）を使った要件定義レビュー機能の実現性を検証するためのスタンドアロンスクリプトです。

## 📋 概要

このスクリプトは以下を検証します：

1. ✅ **エンティティ抽出の精度** - LLMがスキーマに従ってエンティティを抽出できるか
2. ✅ **グラフ構築の正確性** - 抽出されたエンティティをMemgraphに正しく保存できるか
3. ✅ **問題検出の有効性** - Cypherクエリで実際にヌケモレ・矛盾を検出できるか
4. ✅ **処理時間の測定** - 実用的な速度で動作するか

## 🏗️ アーキテクチャ

```
graphrag_poc.py           # メインオーケストレーター
├── config.py            # 設定管理（LLM、Memgraph接続）
├── entity_extractor.py  # LLMベースのエンティティ抽出
├── graph_builder.py     # Memgraphへのグラフ構築
└── problem_detector.py  # Cypherクエリベースの問題検出
```

## 🚀 セットアップ

### 1. 依存パッケージのインストール

```bash
pip install openai neo4j pydantic
```

### 2. Memgraphの起動

```bash
# Dockerで起動
docker run -d -p 7687:7687 --name memgraph memgraph/memgraph-platform

# または既存のMemgraphインスタンスを使用
```

### 3. 環境変数の設定

`.env` ファイルを作成するか、環境変数を設定します：

```bash
# LLMプロバイダー設定（google_ai、openrouter、openai、vllm のいずれか）
export LLM_PROVIDER=google_ai

# Google AI Studio使用の場合（推奨）
export GOOGLE_AI_API_KEY=your-api-key
export GOOGLE_AI_MODEL=gemini-1.5-flash  # または gemini-1.5-pro, gemini-2.0-flash-exp

# OpenRouter使用の場合
export OPENROUTER_API_KEY=your-api-key
export OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct

# OpenAI使用の場合
export OPENAI_API_KEY=your-api-key
export OPENAI_MODEL=gpt-4

# vLLM使用の場合
export VLLM_API_BASE=http://localhost:8000/v1
export VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct

# Memgraph設定
export MEMGRAPH_HOST=localhost
export MEMGRAPH_PORT=7687
export MEMGRAPH_USERNAME=  # 空の場合は認証なし
export MEMGRAPH_PASSWORD=
```

#### Google AI Studio APIキーの取得方法

1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセス
2. 「Get API key」をクリック
3. APIキーをコピーして `GOOGLE_AI_API_KEY` に設定

## 📖 使い方

### 基本的な実行

```bash
cd backend/scripts
python3 graphrag_poc.py samples/sample_requirements_1.md
```

### LLMプロバイダーを指定して実行

```bash
# Google AI Studio（Gemini）を使用（推奨）
export GOOGLE_AI_API_KEY=your-key
python3 graphrag_poc.py samples/sample_requirements_1.md --llm-provider google_ai

# OpenRouterを使用
python3 graphrag_poc.py samples/sample_requirements_1.md --llm-provider openrouter

# OpenAIを使用
python3 graphrag_poc.py samples/sample_requirements_1.md --llm-provider openai

# vLLMを使用
python3 graphrag_poc.py samples/sample_requirements_1.md --llm-provider vllm
```

### サンプル要件定義書

3つのサンプル要件定義書が用意されています：

1. **sample_requirements_1.md** - 正常系（図書館管理システム）
2. **sample_requirements_2.md** - ヌケモレあり（ECサイト）
3. **sample_requirements_3.md** - 矛盾あり（プロジェクト管理システム）

### すべてのサンプルで実行

```bash
# 正常系
python3 graphrag_poc.py samples/sample_requirements_1.md

# ヌケモレあり
python3 graphrag_poc.py samples/sample_requirements_2.md

# 矛盾あり
python3 graphrag_poc.py samples/sample_requirements_3.md
```

## 📊 出力

### コンソール出力

実行中のログと最終的なサマリーが表示されます：

```
================================================================================
GraphRAG PoC Started
================================================================================

[Step 1] Loading requirements from: samples/sample_requirements_1.md
Loaded 1543 characters

[Step 2] Extracting entities and relations...
Extraction completed in 3.45s
  - Entities: 15
  - Relations: 23
  - Validation errors: 0

[Step 3] Building graph in Memgraph...
Graph built in 0.12s
  - Nodes created: 15
  - Edges created: 23

[Step 4] Detecting problems...
Problem detection completed in 0.08s

[Step 5] Generating report...

Total time: 3.65s

================================================================================
RESULTS SUMMARY
================================================================================
Total Issues Found: 2
  - Missing Items: 1
  - Contradictions: 1

Processing Time: 3.65s
  - Extraction: 3.45s
  - Graph Building: 0.12s
  - Problem Detection: 0.08s
================================================================================
```

### ファイル出力

`output/` ディレクトリに以下のファイルが生成されます：

- `extracted_entities.json` - 抽出されたエンティティの統計
- `detection_results.json` - 検出された問題の詳細
- `performance_metrics.json` - パフォーマンス測定結果
- `full_report.json` - 統合レポート

#### detection_results.json の例

```json
{
  "missing_items": {
    "summary": {
      "unused_functions": 1,
      "missing_security_requirements": 1,
      "orphan_data": 0
    },
    "details": {
      "unused_functions": [
        {
          "function_name": "通知メール送信機能",
          "description": null,
          "entity_id": "FUNC-008"
        }
      ],
      "missing_security_requirements": [
        {
          "data_name": "決済情報",
          "sensitivity": "confidential",
          "entity_id": "DATA-004"
        }
      ],
      "orphan_data": []
    }
  },
  "contradictions": {
    "summary": {
      "circular_dependencies": 1,
      "permission_conflicts": 1,
      "data_access_conflicts": 0
    },
    "details": {
      "circular_dependencies": [
        {
          "function_name": "タスク作成機能",
          "cycle_path": ["タスク作成機能", "進捗サマリー更新機能", "タスク作成機能"],
          "entity_id": "FUNC-003"
        }
      ],
      "permission_conflicts": [
        {
          "actor_name": "メンバー",
          "function_name": "タスク作成機能",
          "actor_id": "ACTOR-001",
          "function_id": "FUNC-003",
          "conflict_type": "Permission conflict"
        }
      ],
      "data_access_conflicts": []
    }
  }
}
```

## 🎯 検出可能な問題

### ヌケモレ検出

1. **利用されない機能** - どのActorからもUSESされていないFunction
2. **セキュリティ要件の漏れ** - 機密データにセキュリティ要件が適用されていない
3. **孤立データ** - どのFunctionからもMANIPULATESされていないData

### 矛盾検出

1. **循環依存** - DEPENDS_ONのループ（実装順序が決められない）
2. **権限の競合** - 同一ActorがAllowとDenyの両方を持つ
3. **データアクセスの矛盾** - 依存関係なしに複数FunctionがWriteする

## 🔧 カスタマイズ

### エンティティスキーマの変更

`backend/app/schemas/knowledge_graph_schema.py` を編集してエンティティタイプやリレーションタイプを追加・変更できます。

### 検出クエリの追加

`problem_detector.py` に新しい検出メソッドを追加できます：

```python
async def _detect_custom_issue(self, session_id: str) -> List[Dict]:
    """カスタム問題を検出"""
    async with self.driver.session() as session:
        query = """
            // Your custom Cypher query
            MATCH (n {session_id: $session_id})
            WHERE ...
            RETURN ...
        """
        result = await session.run(query, session_id=session_id)
        return [record.data() async for record in result]
```

### プロンプトのチューニング

`backend/app/prompts/entity_extraction_prompt.py` のプロンプトテンプレートを編集して抽出精度を向上できます。

## 📈 成功基準

### 機能面
- ✅ エンティティ抽出精度 80%以上
- ✅ 問題検出の正確性（既知の問題を検出できる）

### 性能面
- ✅ 1000行の要件定義書を5秒以内で処理
- ✅ グラフ構築が1秒以内

### 品質面
- ✅ バリデーションエラー率 10%以下

## 🐛 トラブルシューティング

### Memgraphに接続できない

```bash
# Memgraphが起動しているか確認
docker ps | grep memgraph

# ポートが開いているか確認
nc -zv localhost 7687
```

### LLM APIエラー

```bash
# APIキーが正しいか確認
echo $OPENROUTER_API_KEY

# ネットワーク接続を確認
curl https://openrouter.ai/api/v1/models
```

### JSON parse error

LLMがJSON形式以外を出力している場合があります。以下を試してください：

- `config.py` の `extraction_temperature` を下げる（0.1-0.2）
- プロンプトに「JSON形式のみ」を強調
- より高性能なモデルを使用

## 📚 関連ドキュメント

- [GraphRAG 詳細設計書（Memgraph版）](../../docs/graphrag-detailed-design-memgraph.md)
- [エンティティスキーマ実装サマリー](../../docs/entity-schema-implementation-summary.md)
- [エンティティスキーマ設計ガイド](../../docs/entity-schema-design-guide.md)

## 🎓 次のステップ

1. サンプル要件定義書で検証を実行
2. 抽出精度と検出精度を評価
3. 必要に応じてスキーマとプロンプトをチューニング
4. 本番システムへの統合を検討
