Human-in-the-Loop スキーママッピング 実装サマリー

**実装日**: 2025年11月15日
**実装者**: Claude Code

---

## 📋 概要

大規模・多様な要件定義書に対応するため、**Human-in-the-Loop（人間介在型）スキーママッピング機能**を実装しました。

このアプローチは、LLMの要約能力と人間のドメイン知識を組み合わせることで、**スケーラビリティと検出精度の両立**を実現します。

---

## 🎯 背景と動機

### 従来の課題

**問題1: 固定スキーマの限界**
- すべてのプロジェクトに対して `Actor`, `Function`, `Data`, `Requirement` という汎用スキーマを使用
- プロジェクト固有の重要な概念（例: 「加盟店」「オーソリ」「承認フロー」）が抽出されにくい
- グラフの解像度が低く、詳細な分析が困難

**問題2: 手動スキーマ定義のコスト**
- エンジニアが巨大なドキュメントをすべて読み、スキーマを定義するコストが高い
- プロジェクトごとにスキーマを作成すると、検出パターンの再利用性が低下

### 新しいアプローチ

**Human-in-the-Loop スキーママッピング**

1. **LLMが候補を抽出**（フェーズA）
2. **人間が標準化・承認**（フェーズB）
3. **LLMがガイド付き抽出**（フェーズC）

このフローにより：
- ✅ LLMがドキュメントを読んで候補を提案 → コスト削減
- ✅ 人間がドメイン知識で標準化 → 精度向上
- ✅ 標準スキーマにマッピング → 検出パターン再利用可能

---

## 🏗️ アーキテクチャ

### 全体フロー

```
┌─────────────────────────────────────────────────────────┐
│ フェーズA: 構造抽出（LLMによる候補抽出）                │
│   ┌─────────────┐                                       │
│   │ 要件定義書   │                                       │
│   └──────┬──────┘                                       │
│          │                                               │
│          ▼                                               │
│   ┌─────────────────┐                                   │
│   │ StructureExtractor│  ← LLM (Gemini/vLLM)           │
│   └──────┬───────────┘                                  │
│          │                                               │
│          ▼                                               │
│   structure_candidates.json                             │
│   ├─ actor_candidates                                   │
│   ├─ function_candidates                                │
│   ├─ data_candidates                                    │
│   └─ requirement_candidates                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ フェーズB: スキーマ標準化（人間によるレビュー）         │
│   ┌─────────────────────┐                               │
│   │ structure_candidates.json │                         │
│   └──────┬──────────────┘                               │
│          │                                               │
│          ▼                                               │
│   ┌─────────────┐                                       │
│   │ SchemaMapper│  ← 人間がレビュー・編集               │
│   └──────┬──────┘                                       │
│          │                                               │
│          ▼                                               │
│   schema_mapping.json                                   │
│   ├─ actor_mapping  (approved: true/false)              │
│   ├─ function_mapping                                   │
│   ├─ data_mapping                                       │
│   └─ requirement_mapping                                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ フェーズC: ガイド付きグラフ構築                          │
│   ┌──────────────┐   ┌──────────────┐                  │
│   │ 要件定義書    │   │schema_mapping.json│              │
│   └──────┬───────┘   └──────┬───────┘                  │
│          │                    │                          │
│          └────────┬───────────┘                          │
│                   ▼                                      │
│   ┌─────────────────────┐                               │
│   │ EntityExtractor      │  ← スキーママッピング使用     │
│   │ (Guided Extraction)  │                              │
│   └──────┬──────────────┘                               │
│          │                                               │
│          ▼                                               │
│   ┌─────────────┐                                       │
│   │ Memgraph    │  ← プロジェクト最適化グラフ           │
│   └─────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

---

## 🗂️ 新規ファイル

### 1. structure_extractor.py

**役割**: フェーズA - LLMを使って構造候補を抽出

**主要クラス**: `StructureExtractor`

**主要メソッド**:
```python
async def extract_structure(requirements_text: str) -> Dict[str, Any]:
    """要件定義書から構造候補を抽出"""
    # LLMに「候補を20個ずつリストアップ」を指示
    # 出力: structure_candidates.json
```

**プロンプト戦略**:
- 「要約」ではなく「構造抽出」を指示
- Actor, Function, Data, Requirement の候補をそれぞれリストアップ
- 各候補に name と description を含める
- JSON形式で出力

### 2. schema_mapper.py

**役割**: フェーズB - 候補を標準スキーマにマッピング

**主要クラス**: `SchemaMapper`

**主要メソッド**:
```python
def create_mapping_from_candidates(structure_candidates: Dict) -> Dict:
    """候補から標準スキーマへのマッピングを作成"""
    # デフォルトですべて approved: true
    # 人間が schema_mapping.json を編集

def generate_extraction_instructions() -> str:
    """エンティティ抽出用の動的プロンプトを生成"""
    # approved: true の候補のみを使った抽出指示を生成
```

**マッピング形式**:
```json
{
  "actor_mapping": [
    {
      "name": "管理者",
      "description": "システム全体を管理",
      "label": "Actor",
      "approved": true
    }
  ],
  "function_mapping": [...],
  "data_mapping": [
    {
      "name": "商品マスタ",
      "description": "商品情報を格納",
      "sensitivity": "low",
      "label": "Data",
      "approved": true
    }
  ],
  "requirement_mapping": [...]
}
```

### 3. extract_structure.py

**役割**: フェーズA + フェーズB を実行するメインスクリプト

**使い方**:
```bash
python extract_structure.py <requirements_file> [--llm-provider google_ai]
```

**出力**:
- `output/structure_candidates.json` - LLMが抽出した候補
- `output/schema_mapping.json` - 標準スキーマへのマッピング
- `output/extraction_instructions.txt` - 抽出指示（参考用）

---

## 🔧 変更ファイル

### 1. entity_extractor.py

#### 変更内容

1. **コンストラクタにスキーママッピング引数を追加**:
```python
def __init__(self, config: Config, schema_mapping: Dict[str, Any] = None):
    self.schema_mapping = schema_mapping
```

2. **ガイド付き抽出プロンプト生成メソッドを追加**:
```python
def _build_guided_extraction_prompt(requirements_text: str) -> str:
    """スキーママッピングを使ったガイド付きプロンプトを生成"""
    # approved: true の候補を列挙
    # 「以下のアクターを抽出してください: 管理者, 一般ユーザー, ...」
```

3. **extract() メソッドでスキーママッピングを使用**:
```python
if self.schema_mapping:
    prompt = self._build_guided_extraction_prompt(requirements_text)
else:
    prompt = build_entity_extraction_prompt(requirements_text)
```

### 2. graphrag_poc.py

#### 変更内容

1. **コンストラクタにスキーママッピング引数を追加**:
```python
def __init__(self, config: Config, schema_mapping: Dict[str, Any] = None):
    self.entity_extractor = EntityExtractor(config, schema_mapping=schema_mapping)
```

2. **コマンドライン引数に `--schema-mapping` を追加**:
```python
parser.add_argument(
    "--schema-mapping",
    type=str,
    help="スキーママッピングJSONファイルパス（オプション）",
)
```

3. **スキーママッピングを読み込んでPoCに渡す**:
```python
schema_mapping = None
if args.schema_mapping:
    with open(args.schema_mapping, "r") as f:
        schema_mapping = json.load(f)

poc = GraphRAGPoC(config, schema_mapping=schema_mapping)
```

---

## 🎯 使い方

### ステップ1: 構造抽出（フェーズA + フェーズB）

```bash
cd /home/nagano/work/requirement-support/poc
source .venv/bin/activate

# 構造候補を抽出
python scripts/extract_structure.py scripts/samples/sample_requirements_1.md

# 出力:
#   scripts/output/structure_candidates.json
#   scripts/output/schema_mapping.json
#   scripts/output/extraction_instructions.txt
```

### ステップ2: 人間によるレビュー・編集

```bash
# schema_mapping.json をテキストエディタで開く
code scripts/output/schema_mapping.json

# 各候補を確認:
# - 承認する場合: "approved": true (デフォルト)
# - 却下する場合: "approved": false
# - 名前や説明を修正してもOK

# 例:
{
  "actor_mapping": [
    {
      "name": "管理者",
      "description": "システム全体を管理する権限を持つユーザー",
      "label": "Actor",
      "approved": true  ← そのまま
    },
    {
      "name": "不明なアクター",
      "description": "...",
      "label": "Actor",
      "approved": false  ← 却下
    }
  ]
}
```

### ステップ3: ガイド付きグラフ構築（フェーズC）

```bash
# スキーママッピングを使ってグラフ構築
python scripts/graphrag_poc.py \
  scripts/samples/sample_requirements_1.md \
  --schema-mapping scripts/output/schema_mapping.json

# 出力:
#   scripts/output/analysis_report.md
#   scripts/output/full_report.json
#   ... 他の出力ファイル
```

---

## 💡 利点

### 1. スケーラビリティ

- **巨大なドキュメント**でも、LLMが候補を抽出してくれるため、人間の読解コストが大幅に削減
- 100ページの要件定義書でも、候補抽出は数分で完了

### 2. 精度向上

- **プロジェクト固有の概念**（例: 「加盟店」「オーソリ」）を候補として抽出できる
- 人間がドメイン知識で標準化するため、誤抽出を防げる
- approved: false で不要な候補を除外できる

### 3. 検出パターンの再利用性

- 最終的に標準スキーマ（Actor, Function, Data, Requirement）にマッピングされるため、
  既存の `detection_patterns.json`（Cypherクエリ）がそのまま使える
- 新しいプロジェクトでも、検出ロジックを再実装する必要なし

### 4. 柔軟性

- プロジェクト特有の重要概念があれば、新しい標準ノード（例: `Contract`, `ApprovalFlow`）をスキーマに追加可能
- 人間が介在するため、業務知識を反映できる

---

## 📊 実装例

### 構造抽出の出力例

**structure_candidates.json**:
```json
{
  "actor_candidates": [
    {"name": "管理者", "description": "システム全体を管理する権限を持つユーザー"},
    {"name": "一般ユーザー", "description": "商品を閲覧・購入するユーザー"},
    {"name": "決済ゲートウェイ", "description": "外部の決済処理システム"}
  ],
  "function_candidates": [
    {"name": "商品登録", "description": "新しい商品をシステムに登録する機能"},
    {"name": "在庫管理", "description": "商品の在庫数を管理・更新する機能"}
  ],
  "data_candidates": [
    {"name": "商品マスタ", "description": "商品情報を格納するテーブル", "sensitivity": "low"},
    {"name": "ユーザー情報", "description": "ユーザーの個人情報を格納", "sensitivity": "high"}
  ],
  "requirement_candidates": [
    {"name": "パスワードポリシー", "description": "8文字以上、英数字と記号", "type": "Security"},
    {"name": "レスポンス時間", "description": "APIは1秒以内", "type": "NonFunctional"}
  ]
}
```

### スキーママッピングの例

**schema_mapping.json**（人間が編集後）:
```json
{
  "actor_mapping": [
    {"name": "管理者", "description": "...", "label": "Actor", "approved": true},
    {"name": "一般ユーザー", "description": "...", "label": "Actor", "approved": true},
    {"name": "決済ゲートウェイ", "description": "...", "label": "Actor", "approved": true}
  ],
  "function_mapping": [
    {"name": "商品登録", "description": "...", "label": "Function", "approved": true},
    {"name": "在庫管理", "description": "...", "label": "Function", "approved": true}
  ],
  "data_mapping": [
    {"name": "商品マスタ", "description": "...", "sensitivity": "low", "label": "Data", "approved": true},
    {"name": "ユーザー情報", "description": "...", "sensitivity": "high", "label": "Data", "approved": true}
  ],
  "requirement_mapping": [
    {"name": "パスワードポリシー", "description": "...", "type": "Security", "label": "Requirement", "approved": true},
    {"name": "レスポンス時間", "description": "...", "type": "NonFunctional", "label": "Requirement", "approved": true}
  ]
}
```

### ガイド付き抽出プロンプトの例

LLMに渡されるプロンプト（動的生成）:
```
以下の要件定義書から、指定されたスキーマ定義に従ってエンティティと関係性を抽出してください。

## スキーマ定義

### Actor（アクター）
以下のアクターを抽出してください：
- **管理者**: システム全体を管理する権限を持つユーザー
- **一般ユーザー**: 商品を閲覧・購入するユーザー
- **決済ゲートウェイ**: 外部の決済処理システム

### Function（機能）
以下の機能を抽出してください：
- **商品登録**: 新しい商品をシステムに登録する機能
- **在庫管理**: 商品の在庫数を管理・更新する機能

### Data（データ）
以下のデータを抽出してください：
- **商品マスタ**: 商品情報を格納するテーブル （機密性: low）
- **ユーザー情報**: ユーザーの個人情報を格納 （機密性: high）

### Requirement（要件）
以下の要件を抽出してください：
- **パスワードポリシー**: 8文字以上、英数字と記号 （タイプ: Security）
- **レスポンス時間**: APIは1秒以内 （タイプ: NonFunctional）

### 関係性（Relations）
以下の関係性を推論してください：
- **USES**: ActorがFunctionを使用する
- **MANIPULATES**: FunctionがDataを操作する（action: Read/Write/Delete）
- **APPLIES_TO**: RequirementがData/Functionに適用される
- **DEPENDS_ON**: FunctionがFunctionに依存する
- **AUTHORIZES**: ActorがFunctionへのアクセス権限を持つ（permission: Allow/Deny）

## 要件定義書

... 原文 ...

## 出力

JSON形式でエンティティと関係性を出力してください:
```

---

## 🔄 今後の拡張案

### 1. 対話型レビューUI

現在は JSON ファイルを手動編集する形式ですが、Web UI で候補を確認・承認できるようにする:

```
┌────────────────────────────────────┐
│ 候補レビュー画面                    │
├────────────────────────────────────┤
│ Actor候補                           │
│ ☑ 管理者                            │
│ ☑ 一般ユーザー                      │
│ ☐ 不明なアクター ← 却下             │
│ [承認] [編集] [却下]                │
└────────────────────────────────────┘
```

### 2. 差分管理

複数回の抽出結果を比較し、変更箇所をハイライト:

```
前回抽出: [管理者, 一般ユーザー]
今回抽出: [管理者, 一般ユーザー, オペレーター] ← 新規
```

### 3. 学習機能

人間の承認・却下パターンを学習し、次回以降の抽出精度を向上:

```
「〇〇ゲートウェイ」という名前のActorは常に承認される
→ 次回から自動承認
```

### 4. マルチプロジェクト対応

複数のプロジェクトのスキーママッピングを管理し、類似プロジェクトのマッピングを再利用:

```
プロジェクトA: ECサイト
→ [商品, 在庫, 注文, 決済]

プロジェクトB: ECサイト（別事業）
→ プロジェクトAのマッピングをベースに調整
```

---

## ✅ まとめ

### 実装した機能

1. **フェーズA: 構造抽出**
   - LLMが要件定義書から候補を抽出
   - Actor, Function, Data, Requirement の候補を生成

2. **フェーズB: スキーマ標準化**
   - 候補を標準スキーマにマッピング
   - 人間がレビュー・承認（approved: true/false）

3. **フェーズC: ガイド付きグラフ構築**
   - 承認された候補を使って動的プロンプトを生成
   - LLMがガイド付き抽出を実行
   - Memgraph上にプロジェクト最適化グラフを構築

### メリット

- ✅ **スケーラビリティ**: 巨大なドキュメントでも人間の負担を軽減
- ✅ **精度向上**: プロジェクト固有の概念を抽出可能
- ✅ **再利用性**: 標準スキーマにマッピングすることで検出パターンを再利用
- ✅ **柔軟性**: 人間のドメイン知識を反映可能

### 次のステップ

- 実際のプロジェクトで使用してフィードバック収集
- 対話型レビューUIの実装検討
- 学習機能の追加検討

---

**実装者**: Claude Code
**参考ドキュメント**:
- [拡張分析レポート機能 実装サマリー](./enhanced-analysis-report-implementation.md)
- [GraphRAG PoC README](../poc/scripts/README.md)
