# Google AI Studio (Gemini API) 統合ガイド

## 📋 概要

GraphRAG PoCスクリプトに**Google AI Studio（Gemini API）**のサポートを追加しました。

**更新日**: 2025年11月15日
**環境変数**: `GOOGLE_AI_API_KEY`, `GOOGLE_AI_MODEL`
**プロバイダー名**: `google_ai`

---

## 🎯 変更内容

### 1. 対応LLMプロバイダー

以前：
- OpenRouter
- OpenAI
- vLLM

**追加後**：
- ✅ **Google AI Studio (Gemini)** ← 新規追加（プロバイダー名: `google_ai`）
- OpenRouter
- OpenAI
- vLLM

### 2. デフォルトプロバイダーの変更

- **変更前**: `openrouter`
- **変更後**: `google_ai`

---

## 🔧 変更したファイル

### 1. config.py

#### 追加された設定

```python
class LLMProvider(str, Enum):
    OPENAI = "openai"
    GOOGLE_AI = "google_ai"  # ← 新規追加
    VLLM = "vllm"
    OPENROUTER = "openrouter"
```

```python
# Google AI Studio設定
google_ai_api_key: str = Field(
    default="",
    description="Google AI Studio APIキー"
)
google_ai_model: str = Field(
    default="gemini-1.5-flash",
    description="Geminiモデル名（gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp）"
)
```

#### 環境変数

- `GOOGLE_AI_API_KEY`: Google AI Studio APIキー
- `GOOGLE_AI_MODEL`: 使用するGeminiモデル（デフォルト: `gemini-1.5-flash`）

---

### 2. entity_extractor.py

#### LLMクライアントの初期化

Google AI Studioの場合とOpenAI互換APIの場合で分岐：

```python
# プロバイダーに応じてクライアントを初期化
if llm_config.get("provider") == "google_ai":
    import google.generativeai as genai
    genai.configure(api_key=llm_config["api_key"])
    self.google_model = genai.GenerativeModel(self.model)
    self.client = None
else:
    # OpenAI互換API（OpenAI、OpenRouter、vLLM）
    from openai import AsyncOpenAI
    self.client = AsyncOpenAI(
        api_key=llm_config["api_key"],
        base_url=llm_config.get("base_url"),
    )
    self.google_model = None
```

#### API呼び出し

```python
async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
    if self.google_model:
        # Google AI Studio (Gemini) API
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"

        import asyncio
        response = await asyncio.to_thread(
            self.google_model.generate_content,
            combined_prompt,
            generation_config={
                "temperature": self.config.extraction_temperature,
            }
        )

        return response.text
    else:
        # OpenAI互換API
        ...
```

**重要な実装ポイント**:
- Gemini APIは現在同期APIのため、`asyncio.to_thread()` で非同期ラッパー化
- system_promptとuser_promptを結合して1つのプロンプトとして送信
- temperatureは `generation_config` で設定

---

### 3. graphrag_poc.py

#### コマンドライン引数

```python
parser.add_argument(
    "--llm-provider",
    type=str,
    choices=["openai", "google_ai", "openrouter", "vllm"],
    default="google_ai",  # デフォルトをgoogle_aiに変更
    help="LLMプロバイダー（デフォルト: google_ai）",
)
```

---

### 4. requirements.txt

#### 追加された依存パッケージ

```
google-generativeai>=0.3.0
```

---

### 5. verify_setup.py

#### 依存パッケージチェック

```python
required = ["openai", "google.generativeai", "neo4j", "pydantic"]
```

#### 環境変数チェック

```python
elif llm_provider == "google_ai":
    api_key = os.getenv("GOOGLE_AI_API_KEY")
    if api_key:
        print(f"   ✅ GOOGLE_AI_API_KEY is set")
        model = os.getenv("GOOGLE_AI_MODEL", "gemini-1.5-flash")
        print(f"   ✅ GOOGLE_AI_MODEL: {model}")
        return True
    else:
        print(f"   ❌ GOOGLE_AI_API_KEY not set")
        print(f"   Get your API key from: https://aistudio.google.com/app/apikey")
        return False
```

---

### 6. README.md

#### セットアップ手順の更新

Google AI Studioの設定方法と使用例を追加：

```bash
# Google AI Studio使用の場合（推奨）
export GOOGLE_AI_API_KEY=your-api-key
export GOOGLE_AI_MODEL=gemini-1.5-flash
```

#### APIキー取得方法

1. [Google AI Studio](https://aistudio.google.com/app/apikey) にアクセス
2. 「Get API key」をクリック
3. APIキーをコピーして `GOOGLE_AI_API_KEY` に設定

---

## 🚀 使い方

### 1. セットアップ

```bash
# 依存パッケージをインストール
pip install google-generativeai

# 環境変数を設定
export LLM_PROVIDER=google_ai
export GOOGLE_AI_API_KEY=your-api-key
export GOOGLE_AI_MODEL=gemini-1.5-flash  # オプショナル
```

### 2. 実行

```bash
cd backend/scripts

# デフォルト（google_ai）で実行
python3 graphrag_poc.py samples/sample_requirements_1.md

# 明示的に指定
python3 graphrag_poc.py samples/sample_requirements_1.md --llm-provider google_ai
```

### 3. セットアップ検証

```bash
python3 verify_setup.py
```

**期待される出力**:
```
🔐 Checking environment variables...
   LLM Provider: google_ai
   ✅ GOOGLE_AI_API_KEY is set
   ✅ GOOGLE_AI_MODEL: gemini-1.5-flash
```

---

## 📊 利用可能なGeminiモデル

| モデル名 | 説明 | 推奨用途 |
|---------|------|---------|
| `gemini-1.5-flash` | 高速・軽量モデル | 開発・テスト、大量処理 |
| `gemini-1.5-pro` | 高性能モデル | 本番環境、高精度要求 |
| `gemini-2.0-flash-exp` | 実験的な最新モデル | 最新機能の試用 |

### モデルの切り替え

```bash
# 高速モデル（デフォルト）
export GOOGLE_AI_MODEL=gemini-1.5-flash

# 高性能モデル
export GOOGLE_AI_MODEL=gemini-1.5-pro

# 実験モデル
export GOOGLE_AI_MODEL=gemini-2.0-flash-exp
```

---

## 💰 料金比較

### Google AI Studio（Gemini）

| モデル | 入力 | 出力 | 無料枠 |
|-------|------|------|--------|
| gemini-1.5-flash | $0.075/1M tokens | $0.30/1M tokens | あり（制限あり） |
| gemini-1.5-pro | $1.25/1M tokens | $5.00/1M tokens | あり（制限あり） |

### OpenRouter（参考）

| モデル | 入力 | 出力 |
|-------|------|------|
| qwen-2.5-coder-32b | $0.18/1M tokens | $0.18/1M tokens |

### OpenAI（参考）

| モデル | 入力 | 出力 |
|-------|------|------|
| gpt-4 | $30/1M tokens | $60/1M tokens |
| gpt-3.5-turbo | $0.50/1M tokens | $1.50/1M tokens |

**推奨**: 開発・テストでは **gemini-1.5-flash** が高速かつコスト効率が良い

---

## 🔍 トラブルシューティング

### 1. `google.generativeai` が見つからない

```bash
pip install google-generativeai
```

### 2. APIキーエラー

```
Error: API key not valid. Please pass a valid API key.
```

**解決方法**:
1. [Google AI Studio](https://aistudio.google.com/app/apikey) で新しいAPIキーを作成
2. 環境変数を正しく設定:
   ```bash
   export GOOGLE_AI_API_KEY=your-actual-api-key
   echo $GOOGLE_AI_API_KEY  # 確認
   ```

### 3. レート制限エラー

```
Error: Resource has been exhausted (e.g. check quota).
```

**解決方法**:
- 無料枠の制限に達している可能性があります
- [Google Cloud Console](https://console.cloud.google.com/) で quota を確認
- 課金アカウントにアップグレード

### 4. モデルが見つからない

```
Error: Model not found
```

**解決方法**:
- モデル名のスペルを確認
- 利用可能なモデル一覧: `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash-exp`

---

## 🎯 推奨設定

### 開発・テスト環境

```bash
export LLM_PROVIDER=google_ai
export GOOGLE_AI_API_KEY=your-key
export GOOGLE_AI_MODEL=gemini-1.5-flash
```

**理由**:
- 高速（レスポンス時間 1-3秒）
- 低コスト
- 無料枠で十分テスト可能

### 本番環境

```bash
export LLM_PROVIDER=google_ai
export GOOGLE_AI_API_KEY=your-key
export GOOGLE_AI_MODEL=gemini-1.5-pro
```

**理由**:
- 高精度
- より複雑な要件定義書に対応
- 安定性

---

## 📈 パフォーマンス比較（想定値）

| プロバイダー | モデル | 抽出時間（1000行） | コスト（1000行） |
|------------|--------|------------------|----------------|
| **Google** | gemini-1.5-flash | 2-3秒 | $0.001 |
| **Google** | gemini-1.5-pro | 3-5秒 | $0.01 |
| OpenRouter | qwen-2.5-coder | 3-5秒 | $0.002 |
| OpenAI | gpt-4 | 5-8秒 | $0.05 |

---

## ✅ まとめ

### 変更内容

1. ✅ Google AI Studio (Gemini API) のサポート追加
2. ✅ デフォルトプロバイダーを `google` に変更
3. ✅ `google-generativeai` パッケージを追加
4. ✅ セットアップ検証スクリプトを更新
5. ✅ ドキュメントを更新

### メリット

- 🚀 **高速**: gemini-1.5-flash は非常に高速
- 💰 **低コスト**: 無料枠あり、有料でも安価
- 🎯 **高精度**: 最新のGeminiモデル
- 🔧 **簡単**: APIキー取得が簡単

### 使い方

```bash
# セットアップ
export GOOGLE_AI_API_KEY=your-key

# 実行
python3 graphrag_poc.py samples/sample_requirements_1.md
```

---

**実装者**: Claude Code
**実装日**: 2025年11月15日
**バージョン**: 1.1.0 (Google AI Studio対応)
