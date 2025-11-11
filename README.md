# 要件定義書支援AIシステム

要件定義作業を支援するAIシステムです。打ち合わせの記録から要件定義書を自動生成し、対話形式で要件を洗い出し、漏れや矛盾をチェックします。

## 📚 ドキュメント

- **[使い方ガイド](docs/USAGE.md)** ← まずはこちらをお読みください！
- [要件定義書](requirements.md) - プロジェクトの要件
- [アーキテクチャ仕様](docs/architecture.md) - 技術仕様
- [GraphRAG実装ガイド](docs/graphrag-architecture.md) - Phase 2拡張

## 機能

### 1. 要件定義のブレークダウン機能
- 打ち合わせの記録から要件定義書のたたき台を自動生成
- AIが質問を生成し、対話形式で要件を深掘り
- ユーザーの回答に基づいて要件定義書を自動更新

### 2. 要件定義書のレビュー機能
- 要件定義書の漏れ・矛盾を自動検出
- 重大度別の指摘事項を提供
- 改善提案を自動生成

## 技術スタック

- **バックエンド**: Python + FastAPI
- **フロントエンド**: Next.js + TypeScript
- **LLM**:
  - Google AI Studio (Gemini 2.0 Flash) - 無料枠推奨
  - OpenRouter - 開発・テスト用
  - vLLM (Qwen3-Coder) - プロダクション用

## ディレクトリ構成

```
requirement-support/
├── backend/           # Pythonバックエンド
│   ├── app/
│   │   ├── main.py
│   │   ├── api/       # APIエンドポイント
│   │   ├── services/  # ビジネスロジック
│   │   ├── models/    # データモデル
│   │   └── utils/     # ユーティリティ
│   └── requirements.txt
├── frontend/          # Next.jsフロントエンド
│   ├── src/
│   │   ├── app/       # Next.js App Router
│   │   ├── components/
│   │   └── lib/
│   └── package.json
├── data/              # データ保存用
│   ├── requirements/  # 生成された要件定義書
│   └── sessions/      # セッション情報
└── requirements.md    # プロジェクトの要件定義書
```

## 🚀 クイックスタート

### 🐳 Docker Composeで起動（推奨）

最も簡単な方法です：

```bash
# 1. 環境変数を設定
cp .env.example .env
# .envを編集してOpenRouter APIキーを設定

# 2. 起動（これだけ！）
docker-compose up

# または、バックグラウンドで起動
docker-compose up -d
```

起動後、以下にアクセス：
- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8001
- **API仕様書**: http://localhost:8001/docs

### 💻 手動セットアップ

Dockerを使わない場合：

```bash
# 1. バックエンドセットアップ
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# .envを編集してAPIキーを設定

# 2. フロントエンドセットアップ
cd ../frontend
npm install
cp .env.example .env.local

# 3. 起動
# ターミナル1: バックエンド
cd backend && uvicorn app.main:app --reload --port 8001

# ターミナル2: フロントエンド
cd frontend && npm run dev

# 4. ブラウザで http://localhost:3000 を開く
```

詳しい手順は **[使い方ガイド](docs/USAGE.md)** を参照してください。

## セットアップ

### 前提条件

#### Docker使用の場合（推奨）
- Docker
- Docker Compose
- **OpenRouter APIキー**（テスト用）または **vLLMサーバー**（本番用）

#### 手動セットアップの場合
- Python 3.10以上
- Node.js 18以上
- **OpenRouter APIキー**（テスト用）または **vLLMサーバー**（本番用）

### Docker Composeでのセットアップ（推奨）

```bash
# 1. 環境変数を設定
cp .env.example .env
# .envを編集してAPIキーを設定

# 2. 起動
docker-compose up

# バックグラウンドで起動する場合
docker-compose up -d

# ログを確認
docker-compose logs -f

# 停止
docker-compose down

# コンテナを再ビルド
docker-compose up --build
```

環境変数の設定（`.env`ファイル）:

**テスト・開発環境（OpenRouter）**:
```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-api-key-here
OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct
```

**本番環境（vLLM）**:
```env
LLM_PROVIDER=vllm
VLLM_API_BASE=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
```

### 手動セットアップ

<details>
<summary>Dockerを使わずに手動でセットアップする場合</summary>

#### バックエンドのセットアップ

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# .envを編集してAPIキーを設定
```

バックエンドの起動:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

#### フロントエンドのセットアップ

```bash
cd frontend
npm install
cp .env.example .env.local
# .env.localを編集（必要に応じて）
```

フロントエンドの起動:
```bash
npm run dev
```

</details>

## 使い方

詳しい使い方は **[使い方ガイド](docs/USAGE.md)** を参照してください。

### 基本的な流れ

1. フロントエンド（http://localhost:3000）にアクセス
2. 「要件定義のブレークダウン」または「要件定義書のレビュー」を選択
3. テキストを入力
4. AIの指示に従って要件定義を進める

### UI構成（ブレークダウン機能）

- **左パネル**: 要件定義書のリアルタイムプレビュー
- **右パネル**: AIとのチャットインターフェース
- 質問に答えると、左側の要件定義書が自動更新されます

## API仕様

詳細は`requirements.md`の「API仕様（概要）」セクションを参照してください。

### 主なエンドポイント

- `POST /api/breakdown/initialize` - 要件定義書のたたき台を生成
- `POST /api/breakdown/answer` - 質問への回答を処理
- `GET /api/breakdown/status/{session_id}` - セッション状態を取得
- `POST /api/review` - 要件定義書をレビュー

## 開発

### Docker環境での開発

```bash
# 開発モードで起動（ホットリロード有効）
docker-compose up

# コンテナ内でコマンドを実行
docker-compose exec backend pytest
docker-compose exec frontend npm run lint

# コンテナのシェルに入る
docker-compose exec backend bash
docker-compose exec frontend sh
```

### VS Code Dev Container

VS Codeで開発する場合、Dev Containerを使用できます：

1. VS Codeで「Dev Containers」拡張機能をインストール
2. `F1` → "Dev Containers: Reopen in Container"
3. コンテナ内で開発（Python/Node.js環境完備）

### テスト

#### Docker環境

```bash
# バックエンドのテスト
docker-compose exec backend pytest

# フロントエンドのテスト
docker-compose exec frontend npm run test
```

#### ローカル環境

```bash
# バックエンド
cd backend
pytest

# フロントエンド
cd frontend
npm run test
```

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。
