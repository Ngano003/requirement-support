# 要件定義書支援AIシステム

要件定義作業を支援するAIシステムです。打ち合わせの記録から要件定義書を自動生成し、対話形式で要件を洗い出し、漏れや矛盾をチェックします。

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
- **LLM**: vLLM (Qwen3-Coder) - OpenAI互換API

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

## セットアップ

### 前提条件

- Python 3.10以上
- Node.js 18以上
- vLLMサーバー（Qwen3-Coderモデル）が動作していること

### バックエンドのセットアップ

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

環境変数の設定（`.env`ファイルを作成）:
```
VLLM_API_BASE=http://localhost:8000/v1
VLLM_API_KEY=your-api-key-if-needed
```

バックエンドの起動:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### フロントエンドのセットアップ

```bash
cd frontend
npm install
```

環境変数の設定（`.env.local`ファイルを作成）:
```
NEXT_PUBLIC_API_URL=http://localhost:8001
```

フロントエンドの起動:
```bash
npm run dev
```

## 使い方

1. フロントエンド（http://localhost:3000）にアクセス
2. 「要件定義のブレークダウン」または「要件定義書のレビュー」を選択
3. テキストを入力またはファイルをアップロード
4. AIの指示に従って要件定義を進める

## API仕様

詳細は`requirements.md`の「API仕様（概要）」セクションを参照してください。

### 主なエンドポイント

- `POST /api/breakdown/initialize` - 要件定義書のたたき台を生成
- `POST /api/breakdown/answer` - 質問への回答を処理
- `GET /api/breakdown/status/{session_id}` - セッション状態を取得
- `POST /api/review` - 要件定義書をレビュー

## 開発

### バックエンドのテスト

```bash
cd backend
pytest
```

### フロントエンドのテスト

```bash
cd frontend
npm run test
```

## ライセンス

MIT License

## 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容を議論してください。
