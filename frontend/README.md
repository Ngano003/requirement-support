# フロントエンド - 要件定義書支援AIシステム

Next.js + TypeScriptベースのフロントエンド

## セットアップ

### 1. 依存パッケージのインストール

```bash
npm install
```

### 2. 環境変数の設定

`.env.local.example`をコピーして`.env.local`を作成：

```bash
cp .env.local.example .env.local
```

`.env.local`ファイルを編集：

```env
NEXT_PUBLIC_API_URL=http://localhost:8001
```

### 3. 開発サーバーの起動

```bash
npm run dev
```

ブラウザで http://localhost:3000 にアクセス

## 機能

### ブレークダウン機能 (/breakdown)

- **左右2分割UI**
  - 左側: 要件定義書のリアルタイムプレビュー
  - 右側: AIとのチャットインターフェース
- 打ち合わせの記録から要件定義書を自動生成
- AIが質問を生成し、対話形式で要件を深掘り
- 回答に基づいて要件定義書をリアルタイム更新
- 完成した要件定義書をマークダウン形式でダウンロード

### レビュー機能 (/review)

- 要件定義書の漏れ・矛盾を自動検出
- 3つのスコア（完全性、整合性、品質）で評価
- 重大度別・カテゴリ別に指摘事項をフィルタリング
- 各指摘事項に対する具体的な改善提案

## ディレクトリ構成

```
frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx           # トップページ
│   │   ├── layout.tsx         # レイアウト
│   │   ├── globals.css        # グローバルCSS
│   │   ├── breakdown/
│   │   │   └── page.tsx       # ブレークダウンページ
│   │   └── review/
│   │       └── page.tsx       # レビューページ
│   ├── components/
│   │   ├── MarkdownViewer.tsx # マークダウンビューアー
│   │   └── ChatInterface.tsx  # チャットインターフェース
│   └── lib/
│       └── api.ts             # APIクライアント
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── README.md
```

## 技術スタック

- **フレームワーク**: Next.js 14 (App Router)
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS
- **状態管理**: React Hooks
- **マークダウン**: react-markdown
- **アイコン**: lucide-react

## ビルド

本番用ビルド：

```bash
npm run build
```

本番サーバー起動：

```bash
npm start
```

## 開発

### コード整形

```bash
npm run lint
```

### 型チェック

TypeScriptの型チェックは自動的に行われます。

## トラブルシューティング

### APIに接続できない

1. バックエンドが起動しているか確認
2. `.env.local`のAPI URLが正しいか確認
3. CORS設定が適切か確認（バックエンド側）

### マークダウンが正しく表示されない

`react-markdown`はセキュリティのため一部のHTML要素を無効化しています。必要に応じて設定を調整してください。

### ポート3000が使用中

別のポートを使用：

```bash
npm run dev -- -p 3001
```
