# バックエンド - 要件定義書支援AIシステム

FastAPIベースのバックエンドAPI

## セットアップ

### 1. 仮想環境の作成と有効化

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env.example`をコピーして`.env`を作成：

```bash
cp .env.example .env
```

`.env`ファイルを編集：

```env
# テスト段階ではOpenRouterを使用
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-api-key-here
OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct

# 本番ではvLLMに切り替え
# LLM_PROVIDER=vllm
# VLLM_API_BASE=http://localhost:8000/v1
# VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
```

### 4. サーバーの起動

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## API仕様

### エンドポイント一覧

#### ブレークダウン機能

- `POST /api/breakdown/initialize` - 要件定義のブレークダウンを初期化
- `POST /api/breakdown/answer` - 質問への回答を処理
- `GET /api/breakdown/status/{session_id}` - セッション状態を取得

#### レビュー機能

- `POST /api/review` - 要件定義書をレビュー

### API仕様書

起動後、以下のURLでインタラクティブなAPI仕様書を確認できます：

- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## ディレクトリ構成

```
backend/
├── app/
│   ├── main.py              # FastAPIアプリケーション
│   ├── api/                 # APIエンドポイント
│   │   ├── breakdown.py     # ブレークダウン機能API
│   │   └── review.py        # レビュー機能API
│   ├── services/            # ビジネスロジック
│   │   ├── llm_service.py   # LLM通信サービス
│   │   ├── breakdown_service.py  # ブレークダウンサービス
│   │   └── review_service.py     # レビューサービス
│   ├── models/              # データモデル
│   │   └── schemas.py       # Pydanticスキーマ
│   └── utils/               # ユーティリティ
│       ├── config.py        # 設定管理
│       └── session_manager.py  # セッション管理
├── requirements.txt         # 依存パッケージ
├── .env.example            # 環境変数テンプレート
└── README.md               # このファイル
```

## 開発

### テストの実行

```bash
pytest
```

### コードフォーマット

```bash
black app/
isort app/
```

### 型チェック

```bash
mypy app/
```

## LLMプロバイダーの切り替え

環境変数`LLM_PROVIDER`で切り替え可能：

### OpenRouter（テスト段階）

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=your-api-key
OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct
```

### vLLM（本番環境）

```env
LLM_PROVIDER=vllm
VLLM_API_BASE=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
```

## トラブルシューティング

### ポート8001が使用中

別のポートを使用：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

### LLM接続エラー

- OpenRouter: APIキーが正しいか確認
- vLLM: vLLMサーバーが起動しているか確認

```bash
curl http://localhost:8000/v1/models
```
