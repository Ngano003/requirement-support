# 使い方ガイド

要件定義書支援AIシステムの使い方をステップバイステップで説明します。

---

## 📖 目次

1. [クイックスタート](#1-クイックスタート)
2. [環境構築](#2-環境構築)
3. [システム起動](#3-システム起動)
4. [機能の使い方](#4-機能の使い方)
5. [Tips & FAQ](#5-tips--faq)

---

## 1. クイックスタート

### 必要なもの

- **Python 3.10以上**
- **Node.js 18以上**
- **OpenRouter APIキー**（テスト用）または **vLLMサーバー**（本番用）

### 5分でスタート

```bash
# 1. バックエンドをセットアップ
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# .envを編集してOpenRouter APIキーを設定

# 2. フロントエンドをセットアップ
cd ../frontend
npm install

# 3. 起動
# ターミナル1: バックエンド
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# ターミナル2: フロントエンド
cd frontend
npm run dev

# 4. ブラウザで http://localhost:3000 にアクセス
```

---

## 2. 環境構築

### 2.1 バックエンド（Python）のセットアップ

#### Step 1: 仮想環境を作成

```bash
cd backend
python -m venv venv
```

#### Step 2: 仮想環境を有効化

```bash
# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

#### Step 3: 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

#### Step 4: 環境変数を設定

```bash
cp .env.example .env
```

`.env`ファイルを編集：

**テスト・開発環境（OpenRouterを使用）**:
```env
# OpenRouterを使う場合（簡単に始められる）
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx  # ← あなたのAPIキー
OPENROUTER_MODEL=qwen/qwen-2.5-coder-32b-instruct

DATA_DIR=../data
MAX_TOKENS=4096
TEMPERATURE=0.7
```

**本番環境（vLLMを使用）**:
```env
# vLLMを使う場合（コスト削減）
LLM_PROVIDER=vllm
VLLM_API_BASE=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen2.5-Coder-32B-Instruct
VLLM_API_KEY=

DATA_DIR=../data
MAX_TOKENS=4096
TEMPERATURE=0.7
```

> 💡 **OpenRouter APIキーの取得方法**
> 1. https://openrouter.ai/ にアクセス
> 2. アカウントを作成
> 3. APIキーを生成
> 4. `.env`に貼り付け

### 2.2 フロントエンド（Next.js）のセットアップ

#### Step 1: 依存パッケージをインストール

```bash
cd frontend
npm install
```

#### Step 2: 環境変数を設定（オプション）

デフォルトでは`http://localhost:8001`を使用します。変更する場合：

```bash
cp .env.local.example .env.local
```

`.env.local`を編集：
```env
NEXT_PUBLIC_API_URL=http://localhost:8001
```

---

## 3. システム起動

### 3.1 バックエンドを起動

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

起動成功メッセージ：
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

> 💡 API仕様書を確認: http://localhost:8001/docs

### 3.2 フロントエンドを起動

**別のターミナルで**:

```bash
cd frontend
npm run dev
```

起動成功メッセージ：
```
  ▲ Next.js 14.2.0
  - Local:        http://localhost:3000
  - Network:      http://192.168.1.xxx:3000

 ✓ Ready in 2.3s
```

### 3.3 ブラウザでアクセス

http://localhost:3000 を開く

---

## 4. 機能の使い方

### 4.1 要件定義のブレークダウン機能

打ち合わせの記録から要件定義書を自動生成し、AIとの対話で要件を深掘りします。

#### Step 1: トップページで「要件定義のブレークダウン」を選択

![トップページ](イメージ)

#### Step 2: 打ち合わせの記録を入力

例：
```
【プロジェクト概要】
社内の業務管理システムを新規開発する。

【主な機能】
- ユーザー管理
- タスク管理
- レポート出力

【制約】
- 予算: 500万円
- 納期: 6ヶ月後
```

「要件定義を開始」ボタンをクリック

#### Step 3: AIが生成した要件定義書のたたき台を確認

画面が2分割されます：
- **左側**: 要件定義書のプレビュー（リアルタイム更新）
- **右側**: AIからの質問

![2分割UI](イメージ)

#### Step 4: AIの質問に回答する

AIが質問を生成します。例：

**質問1（優先度: HIGH）**:
> ユーザー認証は必要ですか？必要な場合、どのような認証方式を想定していますか？

**回答例**:
```
はい、ユーザー認証が必要です。
メールアドレスとパスワードでのログインを想定しています。
```

回答を入力して「送信」をクリック

#### Step 5: 要件定義書が自動更新される

左側のプレビューがリアルタイムで更新されます。
新しい質問が右側に表示されます。

#### Step 6: 繰り返し

すべての質問に回答するか、「十分」と判断したら終了

#### Step 7: ダウンロード

「ダウンロード」ボタンをクリックして、完成した要件定義書をマークダウンファイルとして保存

### 4.2 要件定義書のレビュー機能

完成した要件定義書を分析し、漏れ・矛盾を指摘します。

#### Step 1: トップページで「要件定義書のレビュー」を選択

#### Step 2: 要件定義書を入力

- テキストエリアに直接ペースト
- または、マークダウンファイルをアップロード（将来実装予定）

#### Step 3: 「レビュー開始」ボタンをクリック

AIが要件定義書を分析します（30〜60秒）

#### Step 4: レビュー結果を確認

**3つのスコア**:
- **完全性スコア**: 必須項目の充足度
- **整合性スコア**: 矛盾の有無
- **品質スコア**: 記述の明確さ

**指摘事項リスト**:

例：

| 重大度 | カテゴリ | セクション | 指摘内容 |
|-------|---------|-----------|---------|
| 🔴 High | 漏れ | 非機能要件 | パスワードポリシーが記載されていません |
| 🟡 Medium | 曖昧 | ユーザー登録 | メールアドレスの重複チェックが明記されていません |
| 🟢 Low | 品質 | データ保存 | "適切に処理する"という曖昧な表現があります |

各指摘事項には**改善提案**が含まれます。

#### Step 5: フィルタリング

- 重大度別にフィルタリング（High/Medium/Low）
- カテゴリ別にフィルタリング（漏れ/矛盾/曖昧/品質）

#### Step 6: 改善

指摘事項を参考に要件定義書を改善し、必要に応じて再レビュー

---

## 5. Tips & FAQ

### 💡 Tips

#### Tip 1: 質問はスキップできる？
現在のバージョンでは、質問に順番に答える必要があります。
答えたくない質問は「該当なし」や「不明」と入力してスキップできます。

#### Tip 2: LLMの切り替え
`.env`ファイルの`LLM_PROVIDER`を変更することで、OpenRouterとvLLMを切り替えられます。
変更後はバックエンドを再起動してください。

#### Tip 3: API仕様を確認したい
バックエンド起動後、http://localhost:8001/docs にアクセスすると、
インタラクティブなAPI仕様書（Swagger UI）が表示されます。

#### Tip 4: より詳細な質問が欲しい
`.env`の`TEMPERATURE`を上げると、AIがより創造的な質問を生成します。
- 保守的: `0.5`
- バランス: `0.7`（デフォルト）
- 創造的: `0.9`

#### Tip 5: セッションデータはどこに保存される？
- 要件定義書: `data/requirements/{session_id}.md`
- セッション情報: `data/sessions/{session_id}.json`

### ❓ FAQ

#### Q1: OpenRouter APIキーがない場合は？
A: 無料のvLLMを使用できます。ただし、vLLMサーバーを別途セットアップする必要があります。

#### Q2: エラー「Failed to connect to API」が出る
A: 以下を確認してください：
1. バックエンドが起動しているか（http://localhost:8001/health で確認）
2. `.env`のAPIキーが正しいか
3. OpenRouterの場合、クレジットがあるか

#### Q3: 要件定義書が日本語以外になる
A: 入力テキストを日本語で書いてください。AIは入力言語に合わせて出力します。

#### Q4: ブレークダウン中にページを閉じたら？
A: セッションデータは保存されているので、セッションIDがあれば復元できます（将来実装予定）。

#### Q5: Phase 2の機能（GraphRAG、Git連携）はいつ使える？
A: Phase 2は今後の拡張予定です。詳細は `requirements.md` のPhase 2セクションを参照してください。

#### Q6: 複数人で同時に使える？
A: はい、各ユーザーは独自のセッションを持つため、同時利用可能です。

#### Q7: 商用利用は可能？
A: MITライセンスなので可能ですが、使用するLLMのライセンスにも従ってください。

#### Q8: カスタマイズしたい
A: コードは完全にオープンです。`backend/app/services/`のプロンプトを編集することで、
AIの挙動をカスタマイズできます。

---

## 🎯 次のステップ

### 基本をマスターしたら

1. **プロンプトのカスタマイズ**
   - `backend/app/services/breakdown_service.py`
   - `backend/app/services/review_service.py`

2. **Phase 2機能の理解**
   - [docs/architecture.md](architecture.md) - Phase 2アーキテクチャ
   - [docs/graphrag-architecture.md](graphrag-architecture.md) - GraphRAG実装

3. **貢献する**
   - GitHubでissueを作成
   - Pull Requestを送る

---

## 📚 関連ドキュメント

- [README.md](../README.md) - プロジェクト概要
- [requirements.md](../requirements.md) - 要件定義書
- [docs/architecture.md](architecture.md) - アーキテクチャ仕様
- [backend/README.md](../backend/README.md) - バックエンド詳細
- [frontend/README.md](../frontend/README.md) - フロントエンド詳細

---

**文書バージョン**: 1.0
**作成日**: 2025-11-10
**最終更新日**: 2025-11-10
