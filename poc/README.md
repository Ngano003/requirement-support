# GraphRAG PoC 実行環境

このディレクトリには、GraphRAG（Memgraph + Google AI Studio）を使った要件定義レビュー機能のPoC（Proof of Concept）スクリプトが含まれています。

## 📁 ディレクトリ構成

```
poc/
├── .venv/                    # Python仮想環境（uv管理）
├── .env                      # 環境変数設定（APIキーなど）
├── .env.example              # 環境変数のテンプレート
├── scripts/                  # PoCスクリプト
│   ├── graphrag_poc.py      # メインスクリプト
│   ├── config.py            # 設定管理
│   ├── entity_extractor.py  # エンティティ抽出
│   ├── graph_builder.py     # グラフ構築
│   ├── problem_detector.py  # 問題検出
│   ├── verify_setup.py      # セットアップ検証
│   ├── requirements.txt     # 依存パッケージ
│   ├── README.md            # スクリプトの詳細ガイド
│   ├── samples/             # サンプル要件定義書
│   │   ├── sample_requirements_1.md
│   │   ├── sample_requirements_2.md
│   │   └── sample_requirements_3.md
│   └── output/              # 実行結果の出力先
└── README.md                # このファイル
```

## 🚀 セットアップ

### 1. 仮想環境の確認

仮想環境は既に `.venv` ディレクトリに作成されています：

```bash
cd /home/nagano/work/requirement-support/poc
source .venv/bin/activate
```

### 2. 依存パッケージの確認

必要なパッケージは既にインストールされています：

- `openai>=1.0.0` - OpenAI互換LLM API
- `google-generativeai>=0.3.0` - Google AI Studio (Gemini)
- `neo4j>=5.0.0` - Memgraph接続用
- `pydantic>=2.0.0` - データバリデーション
- `python-dotenv>=1.0.0` - 環境変数管理

### 3. 環境変数の設定

`.env` ファイルを作成し、APIキーを設定します：

```bash
cp .env.example .env
```

`.env` ファイルを編集：

```bash
# 必須設定
LLM_PROVIDER=google_ai
GOOGLE_AI_API_KEY=your-actual-api-key-here
GOOGLE_AI_MODEL=gemini-1.5-flash

# Memgraph設定（デフォルト値で動作します）
MEMGRAPH_HOST=localhost
MEMGRAPH_PORT=7687
```

### 4. Google AI Studio APIキーの取得

1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセス
2. 「Get API key」をクリック
3. APIキーをコピーして `.env` の `GOOGLE_AI_API_KEY` に設定

### 5. Memgraphの起動

Dockerで起動：

```bash
docker run -d -p 7687:7687 --name memgraph memgraph/memgraph-platform
```

### 6. セットアップ検証

```bash
source .venv/bin/activate
python scripts/verify_setup.py
```

**期待される出力**：
```
✅ All checks passed! Ready to run GraphRAG PoC.
```

## 🎯 実行方法

### 基本的な実行

```bash
source .venv/bin/activate
cd scripts
python graphrag_poc.py samples/sample_requirements_1.md
```

### サンプルで試す

```bash
# 正常系（ヌケモレ・矛盾なし）
python graphrag_poc.py samples/sample_requirements_1.md

# ヌケモレあり（セキュリティ要件漏れなど）
python graphrag_poc.py samples/sample_requirements_2.md

# 矛盾あり（循環依存、権限競合など）
python graphrag_poc.py samples/sample_requirements_3.md
```

### 独自の要件定義書で実行

```bash
python graphrag_poc.py /path/to/your/requirements.md
```

## 📊 出力結果

実行結果は `scripts/output/` ディレクトリに保存されます：

- `extracted_entities.json` - 抽出されたエンティティ統計
- `detection_results.json` - 検出された問題の詳細
- `performance_metrics.json` - パフォーマンス測定結果
- `full_report.json` - 統合レポート

## 🔍 検出可能な問題

### ヌケモレ検出

1. **利用されない機能** - どのActorからもUSESされていないFunction
2. **セキュリティ要件の漏れ** - 機密データにセキュリティ要件が適用されていない
3. **孤立データ** - どのFunctionからもMANIPULATESされていないData

### 矛盾検出

1. **循環依存** - DEPENDS_ONのループ（実装順序が決められない）
2. **権限の競合** - 同一ActorがAllowとDenyの両方を持つ
3. **データアクセスの矛盾** - 依存関係なしに複数FunctionがWriteする

## 💡 トラブルシューティング

### Memgraphに接続できない

```bash
# Memgraphが起動しているか確認
docker ps | grep memgraph

# 起動していない場合
docker start memgraph

# 新規起動
docker run -d -p 7687:7687 --name memgraph memgraph/memgraph-platform
```

### APIキーエラー

```bash
# 環境変数が正しく設定されているか確認
source .venv/bin/activate
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('GOOGLE_AI_API_KEY'))"
```

### モジュールが見つからない

```bash
# backend/appディレクトリが存在するか確認
ls -la ../backend/app/

# 依存パッケージを再インストール
uv pip install -r scripts/requirements.txt
```

## 📚 詳細ガイド

- **スクリプトの詳細**: [scripts/README.md](scripts/README.md)
- **統合ガイド**: [../docs/google-ai-studio-integration.md](../docs/google-ai-studio-integration.md)
- **実装サマリー**: [../docs/graphrag-poc-implementation-summary.md](../docs/graphrag-poc-implementation-summary.md)

## ⚙️ 環境情報

- **Python**: 3.12.3
- **パッケージ管理**: uv
- **仮想環境**: .venv
- **LLMプロバイダー**: Google AI Studio (Gemini)
- **グラフDB**: Memgraph

## ✅ セットアップ完了

以下のコマンドで動作確認ができます：

```bash
# 仮想環境をアクティベート
source .venv/bin/activate

# セットアップ検証
python scripts/verify_setup.py

# サンプル実行
python scripts/graphrag_poc.py scripts/samples/sample_requirements_1.md
```

Happy testing! 🎉
