# 要件定義書支援AIシステム 要件定義書

## 1. プロジェクト概要

### 1.1 プロジェクト名
要件定義書支援AIシステム (Requirements Definition Support AI)

### 1.2 目的
要件定義作業の効率化と品質向上を支援するAIシステムを構築する。
打ち合わせの記録から要件定義書を自動生成し、対話形式で要件を洗い出し、最終的に漏れや矛盾のない要件定義書を完成させる。

### 1.3 対象ユーザー
- システムエンジニア
- プロジェクトマネージャー
- ビジネスアナリスト
- 要件定義作業に携わる全ての関係者

## 2. システムの目的と期待効果

### 2.1 目的
- 要件定義作業の工数削減
- 要件の漏れ・矛盾の早期発見
- 要件定義の品質向上
- 要件定義プロセスの標準化

### 2.2 期待効果
- 要件定義作業時間の50%削減
- 要件の漏れや矛盾による手戻りの削減
- 要件定義書の品質の均一化

## 3. 機能要件

### 3.1 要件定義のブレークダウン機能

#### 3.1.1 機能概要
打ち合わせの記録や議事録から要件定義書のたたき台を自動生成し、対話形式で要件を深掘りする機能。

#### 3.1.2 入力
- 打ち合わせの記録（テキスト形式）
- 議事録（マークダウン、テキスト、またはその他のテキスト形式）
- 既存の要件定義書（部分的なもの）

#### 3.1.3 処理フロー
1. **初期分析**: 入力されたテキストを解析し、以下の要素を抽出
   - システムの目的
   - 主要な機能
   - ステークホルダー
   - 制約条件
   - 非機能要件のヒント

2. **たたき台生成**: 抽出した情報から要件定義書のたたき台を生成
   - 機能一覧
   - 画面遷移図（テキストベース）
   - データ項目
   - 業務フロー

3. **質問生成**: 要件を深掘りするための質問を自動生成
   - 不明瞭な要件に対する明確化の質問
   - 考慮漏れの可能性がある項目についての質問
   - 非機能要件に関する質問
   - エッジケースや例外処理に関する質問

4. **対話的な要件追加**: ユーザーの回答を受けて要件定義書を更新
   - 回答内容を要件定義書に反映
   - 新たな質問を生成
   - 要件の整合性チェック

5. **繰り返し**: ユーザーが満足するまで質問→回答→更新を繰り返す

#### 3.1.4 出力
- 要件定義書（マークダウン形式）
- 質問リスト
- 要件カバレッジレポート

#### 3.1.5 具体的な質問例
- 「〇〇機能において、エラーが発生した場合の挙動はどうしますか？」
- 「ユーザー認証は必要ですか？必要な場合、認証方式は？」
- 「データの保存期間や容量制限はありますか？」
- 「同時アクセス数の想定はどれくらいですか？」
- 「外部システムとの連携は必要ですか？」

### 3.2 要件定義書のレビュー機能

#### 3.2.1 機能概要
完成した要件定義書、または作成途中の要件定義書を分析し、漏れや矛盾を指摘する機能。

#### 3.2.2 入力
- 要件定義書（マークダウン形式）

#### 3.2.3 チェック項目

##### 3.2.3.1 必須項目の確認
- システム概要
- 目的・背景
- 対象ユーザー
- 機能要件
- 非機能要件
- 制約条件
- 前提条件

##### 3.2.3.2 整合性チェック
- 機能間の矛盾
- データの整合性
- 画面遷移の整合性
- ユーザー権限の整合性

##### 3.2.3.3 漏れチェック
- エラーハンドリングの記載漏れ
- セキュリティ要件の漏れ
- パフォーマンス要件の漏れ
- バックアップ・リカバリの漏れ
- ログ・監査要件の漏れ
- テスト要件の漏れ

##### 3.2.3.4 品質チェック
- 曖昧な表現の検出
- 定量化されていない非機能要件
- 用語の統一性
- 実現可能性の検証

#### 3.2.4 出力
- レビュー結果レポート
  - 重大度別の指摘事項（High/Medium/Low）
  - 指摘箇所（セクション、行番号）
  - 改善提案
  - チェックリスト（項目の充足度）

#### 3.2.5 指摘の具体例
- **High**: 「認証機能が定義されていますが、パスワードポリシー（複雑さ、有効期限など）が記載されていません」
- **Medium**: 「ユーザー登録機能で、メールアドレスの重複チェックが明記されていません」
- **Low**: 「'適切に処理する'という曖昧な表現があります。具体的な処理内容を明記してください」

## 4. 技術要件

### 4.1 バックエンド

#### 4.1.1 言語・フレームワーク
- Python 3.10以上
- FastAPI（推奨）またはFlask
- 非同期処理サポート

#### 4.1.2 LLMエンジン
- vLLM
- モデル: Qwen3-Coder
- OpenAI互換APIでアクセス
- APIエンドポイント経由での接続

#### 4.1.3 主要ライブラリ
- `openai` or `httpx`: vLLM APIクライアント
- `pydantic`: データバリデーション
- `python-multipart`: ファイルアップロード
- `markdown`: マークダウン処理
- `uvicorn`: ASGIサーバー

### 4.2 フロントエンド

#### 4.2.1 言語・フレームワーク
- Next.js 14以上（App Router）
- TypeScript
- React 18以上

#### 4.2.2 主要ライブラリ
- `react-markdown`: マークダウンレンダリング
- `tailwindcss`: スタイリング
- `shadcn/ui`: UIコンポーネント（推奨）
- `zustand` or `jotai`: 状態管理
- `react-hook-form`: フォーム管理
- `axios` or `fetch`: API通信

### 4.3 データストレージ
- ファイルシステムベース（初期実装）
  - 要件定義書: マークダウンファイルとして保存
  - セッション情報: JSONファイルとして保存
- 将来的にはデータベース導入も検討（PostgreSQL, MongoDB等）

## 5. システム構成

### 5.1 アーキテクチャ概要
```
[フロントエンド (Next.js)]
        ↓ HTTP/REST API
[バックエンド (FastAPI)]
        ↓ HTTP API
[vLLM Server (Qwen3-Coder)]
```

### 5.2 ディレクトリ構成（案）
```
requirement-support/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── breakdown.py
│   │   │   └── review.py
│   │   ├── services/
│   │   │   ├── llm_service.py
│   │   │   ├── breakdown_service.py
│   │   │   └── review_service.py
│   │   ├── models/
│   │   │   └── schemas.py
│   │   └── utils/
│   │       └── markdown_parser.py
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx
│   │   │   ├── breakdown/
│   │   │   │   └── page.tsx
│   │   │   └── review/
│   │   │       └── page.tsx
│   │   ├── components/
│   │   │   ├── MarkdownEditor.tsx
│   │   │   ├── QuestionList.tsx
│   │   │   └── ReviewReport.tsx
│   │   └── lib/
│   │       └── api.ts
│   ├── package.json
│   └── README.md
├── data/
│   ├── requirements/
│   └── sessions/
└── README.md
```

## 6. API仕様（概要）

### 6.1 ブレークダウン機能API

#### 6.1.1 POST /api/breakdown/initialize
初期テキストから要件定義書のたたき台を生成

**リクエスト**:
```json
{
  "input_text": "打ち合わせの記録...",
  "session_id": "optional-session-id"
}
```

**レスポンス**:
```json
{
  "session_id": "generated-session-id",
  "draft_requirements": "# 要件定義書\n...",
  "questions": [
    {
      "id": "q1",
      "category": "functional",
      "question": "...",
      "priority": "high"
    }
  ]
}
```

#### 6.1.2 POST /api/breakdown/answer
質問への回答を受けて要件定義書を更新

**リクエスト**:
```json
{
  "session_id": "session-id",
  "question_id": "q1",
  "answer": "ユーザーの回答..."
}
```

**レスポンス**:
```json
{
  "updated_requirements": "# 要件定義書\n...",
  "new_questions": [...],
  "completion_rate": 75
}
```

#### 6.1.3 GET /api/breakdown/status/{session_id}
セッションの状態を取得

**レスポンス**:
```json
{
  "session_id": "session-id",
  "requirements": "...",
  "remaining_questions": [...],
  "completion_rate": 80
}
```

### 6.2 レビュー機能API

#### 6.2.1 POST /api/review
要件定義書をレビュー

**リクエスト**:
```json
{
  "requirements_text": "# 要件定義書\n..."
}
```

**レスポンス**:
```json
{
  "review_id": "review-id",
  "issues": [
    {
      "severity": "high",
      "category": "missing",
      "section": "非機能要件",
      "line": 145,
      "description": "パスワードポリシーが記載されていません",
      "suggestion": "パスワードの最小文字数、複雑さ要件、有効期限を明記してください"
    }
  ],
  "completeness_score": 75,
  "consistency_score": 90,
  "quality_score": 80,
  "summary": "全体的には良好ですが、セキュリティ要件の記載を追加することを推奨します"
}
```

## 7. 画面仕様（概要）

### 7.1 トップページ
- 機能選択
  - 要件定義のブレークダウン
  - 要件定義書のレビュー

### 7.2 ブレークダウン画面

#### 7.2.1 初期入力画面
- テキストエリア: 打ち合わせの記録を入力
- ファイルアップロード: テキストファイルをアップロード
- 実行ボタン

#### 7.2.2 対話画面
- 左パネル: 要件定義書プレビュー（マークダウンレンダリング）
- 右パネル: 質問リスト
  - 各質問に対する回答入力欄
  - 優先度表示（High/Medium/Low）
  - カテゴリ表示（機能要件/非機能要件/その他）
- 進捗バー: 要件の充足度
- エクスポートボタン: 要件定義書をダウンロード

### 7.3 レビュー画面

#### 7.3.1 入力画面
- テキストエリア: 要件定義書を入力
- ファイルアップロード: マークダウンファイルをアップロード
- レビュー実行ボタン

#### 7.3.2 レビュー結果画面
- スコア表示
  - 完全性スコア
  - 整合性スコア
  - 品質スコア
- 指摘事項リスト
  - 重大度別にフィルタリング
  - カテゴリ別にフィルタリング
  - 各指摘事項の詳細と改善提案
- 元の要件定義書と指摘箇所のハイライト表示
- 改善版のエクスポート（オプション）

## 8. 非機能要件

### 8.1 パフォーマンス
- 初期分析: 30秒以内
- 質問生成: 10秒以内
- レビュー実行: 60秒以内（要件定義書のサイズによる）

### 8.2 可用性
- 稼働率: 99%以上（開発環境では不問）

### 8.3 セキュリティ
- 入力データのサニタイズ
- CORS設定の適切な管理
- APIレート制限（DoS対策）

### 8.4 保守性
- コードの可読性
- 適切なログ出力
- エラーハンドリング
- ユニットテストの実装

### 8.5 拡張性
- 新しいLLMモデルへの切り替えが容易
- 新しいチェック項目の追加が容易
- マルチテナント対応の余地

## 9. 制約条件

### 9.1 技術的制約
- vLLMサーバーは別途構築・運用されている前提
- Qwen3-Coderモデルが利用可能であること
- vLLM APIエンドポイントにアクセス可能であること

### 9.2 運用制約
- 初期フェーズではローカル環境での動作を想定
- インターネット接続は不要（vLLMサーバーがローカルの場合）

## 10. 今後の拡張案

### 10.1 機能拡張
- 要件定義書のテンプレート機能
- 複数人での共同編集
- **Git連携による自動バージョン管理（優先度: 高）**
- 要件のトレーサビリティ管理
- 既存システムの要件定義書からの学習
- **GraphRAG + Neo4jによる関係性グラフベースの高度なレビュー機能（優先度: 高）**

### 10.2 技術拡張
- Neo4jグラフデータベース統合
- データベース導入（PostgreSQL, MongoDB等）
- ユーザー認証・認可
- リアルタイム更新（WebSocket）
- 要件定義書の比較・差分表示
- Excel/Word形式での出力

## 11. 開発フェーズ

### Phase 1: MVP開発（初期実装）
- バックエンドAPI基本実装
- vLLM連携実装
- フロントエンド基本UI
- ブレークダウン機能の基本実装
- レビュー機能の基本実装

### Phase 2: 機能拡張
- 質問生成ロジックの改善
- レビューチェック項目の拡充
- UI/UXの改善
- エクスポート機能の強化
- **Git連携による自動バージョン管理**
  - 要件定義書更新時の自動コミット
  - バージョン履歴の表示
  - 差分表示機能
- **GraphRAG + Neo4j統合実装**
  - Neo4jデータベースセットアップ
  - 要件定義書からの知識グラフ構築
  - グラフベースの関係性分析
  - グラフ可視化UI

### Phase 3: 本番運用準備
- パフォーマンスチューニング
- セキュリティ強化
- ドキュメント整備
- デプロイメント自動化

## 12. 成功基準

- システムが正常に動作し、要件定義書のたたき台が生成できる
- 質問生成機能が適切に動作する
- レビュー機能が漏れ・矛盾を検出できる
- ユーザーが直感的に操作できる
- 要件定義作業の効率化が実感できる

## 13. GraphRAG + Neo4j統合計画（Phase 2拡張）

### 13.1 目的と背景

#### 13.1.1 課題
現在のレビュー機能は、LLMによるテキストベースの分析に依存しており、以下の課題があります：
- 要件間の関係性を体系的に把握できない
- 依存関係の漏れを論理的に検証できない
- 矛盾の検出が表層的になりがち
- 影響範囲の分析が不十分

#### 13.1.2 解決策
GraphRAG（Graph Retrieval-Augmented Generation）とNeo4jを活用し、要件定義書から知識グラフを構築することで、論理的かつ構造的なレビューを実現します。

#### 13.1.3 期待効果
- 要件間の依存関係を可視化
- 矛盾や循環依存を自動検出
- 影響範囲分析の精度向上
- 漏れの論理的な検証
- トレーサビリティの確保

### 13.2 アーキテクチャ設計

#### 13.2.1 システム構成
```
[フロントエンド (Next.js)]
        ↓ HTTP/REST API
[バックエンド (FastAPI)]
        ↓                ↓
[vLLM/OpenRouter]    [Neo4j Database]
        ↓                ↓
  テキスト生成      知識グラフ管理
        ↓                ↓
        └────→ GraphRAG ←────┘
```

#### 13.2.2 データフロー
1. **グラフ構築フェーズ**
   - 要件定義書を入力
   - LLMで要素を抽出（機能、データ、制約、ユーザー、etc.）
   - Neo4jにノードとリレーションシップを作成

2. **分析フェーズ**
   - グラフクエリで関係性を分析
   - Cypherクエリで矛盾や漏れを検出
   - グラフアルゴリズムで影響範囲を計算

3. **レビューフェーズ**
   - 分析結果をコンテキストとしてLLMに渡す
   - LLMが自然言語でレビューレポートを生成

### 13.3 グラフモデル設計

#### 13.3.1 ノードタイプ
- **Requirement**: 要件項目
  - プロパティ: id, title, description, type, priority, status
- **Function**: 機能
  - プロパティ: id, name, description, category
- **Data**: データエンティティ
  - プロパティ: id, name, type, attributes
- **User**: ユーザー/アクター
  - プロパティ: id, name, role, description
- **Constraint**: 制約条件
  - プロパティ: id, description, type
- **NonFunctional**: 非機能要件
  - プロパティ: id, category, description, metric, target

#### 13.3.2 リレーションシップタイプ
- **DEPENDS_ON**: 依存関係
  - プロパティ: type, description
- **CONFLICTS_WITH**: 矛盾関係
  - プロパティ: reason
- **REQUIRES**: 要求関係
  - プロパティ: mandatory
- **USES**: 使用関係
  - プロパティ: access_type
- **IMPLEMENTS**: 実装関係
- **VALIDATES**: 検証関係
- **PART_OF**: 包含関係

#### 13.3.3 グラフモデル例
```
(User:ユーザー)-[:USES]->(Function:ログイン機能)
                              ↓ [:REQUIRES]
                        (Data:ユーザー情報)
                              ↓ [:DEPENDS_ON]
                  (NonFunctional:暗号化要件)
```

### 13.4 GraphRAG実装詳細

#### 13.4.1 知識グラフ構築プロセス
```python
# 1. 要件定義書をセクションごとに分割
sections = parse_requirements(requirements_text)

# 2. LLMで各セクションからエンティティとリレーションを抽出
for section in sections:
    entities = extract_entities_with_llm(section)
    relationships = extract_relationships_with_llm(section, entities)

    # 3. Neo4jにノードとリレーションシップを作成
    for entity in entities:
        create_node(neo4j_driver, entity)

    for rel in relationships:
        create_relationship(neo4j_driver, rel)
```

#### 13.4.2 グラフベース分析クエリ例

**依存関係の循環検出**:
```cypher
MATCH (r1:Requirement)-[:DEPENDS_ON*]->(r2:Requirement)
WHERE r1 = r2
RETURN r1, collect(distinct r2) as cycle
```

**孤立要件の検出**:
```cypher
MATCH (r:Requirement)
WHERE NOT (r)-[]-()
RETURN r
```

**機能とデータの整合性チェック**:
```cypher
MATCH (f:Function)-[:USES]->(d:Data)
WHERE NOT EXISTS {
  MATCH (d)-[:VALIDATES]->(c:Constraint)
}
RETURN f, d
```

**影響範囲分析**:
```cypher
MATCH path = (r:Requirement)-[:DEPENDS_ON*1..5]->(dependent)
WHERE r.id = $requirement_id
RETURN path, dependent
```

### 13.5 API拡張設計

#### 13.5.1 新規エンドポイント
- `POST /api/graph/build` - 知識グラフ構築
- `GET /api/graph/analyze/{session_id}` - グラフ分析実行
- `GET /api/graph/visualize/{session_id}` - グラフ可視化データ取得
- `POST /api/review/enhanced` - GraphRAG強化レビュー

#### 13.5.2 GraphRAG強化レビューAPI
**リクエスト**:
```json
{
  "requirements_text": "# 要件定義書\n...",
  "analysis_type": "full",  // full, dependencies, conflicts, coverage
  "include_graph": true
}
```

**レスポンス**:
```json
{
  "review_id": "review-id",
  "graph_analysis": {
    "nodes_count": 45,
    "relationships_count": 78,
    "circular_dependencies": [],
    "isolated_requirements": [],
    "missing_constraints": [...]
  },
  "issues": [...],
  "graph_data": {
    "nodes": [...],
    "edges": [...]
  },
  "recommendations": [...]
}
```

### 13.6 技術スタック

#### 13.6.1 バックエンド追加ライブラリ
- `neo4j`: Neo4j Pythonドライバー
- `llama-index`: GraphRAG実装サポート
- `networkx`: グラフアルゴリズム
- `python-louvain`: コミュニティ検出

#### 13.6.2 フロントエンド追加ライブラリ
- `vis-network` or `cytoscape.js`: グラフ可視化
- `d3.js`: 高度な可視化（オプション）
- `react-force-graph`: React向けグラフコンポーネント

### 13.7 実装ステップ（Phase 2）

#### Step 1: Neo4j環境構築
- Dockerを使ったNeo4jセットアップ
- データベーススキーマ定義
- 接続確認

#### Step 2: グラフ構築サービス実装
- エンティティ抽出ロジック
- リレーションシップ抽出ロジック
- Neo4jへのデータ投入

#### Step 3: グラフ分析サービス実装
- Cypherクエリ実装
- 分析アルゴリズム実装
- レポート生成

#### Step 4: フロントエンド統合
- グラフ可視化コンポーネント
- 分析結果表示UI
- インタラクティブなグラフ操作

#### Step 5: テストと最適化
- グラフクエリのパフォーマンステスト
- 大規模要件定義書での検証
- UI/UXの改善

### 13.8 期待される成果物

1. **GraphRAG強化レビューエンジン**
   - 論理的な矛盾検出精度の向上
   - 依存関係の可視化
   - 影響範囲の自動計算

2. **インタラクティブグラフUI**
   - 要件間の関係を視覚的に把握
   - ノードをクリックして詳細表示
   - フィルタリングとズーム機能

3. **高度な分析レポート**
   - グラフ統計情報
   - コミュニティ検出結果
   - 重要度分析（PageRankなど）

### 13.9 運用上の考慮事項

#### 13.9.1 Neo4jのデプロイ
- Docker Compose での構成
- データバックアップ戦略
- スケーリング計画

#### 13.9.2 パフォーマンス
- インデックス戦略
- クエリ最適化
- キャッシング

#### 13.9.3 データ管理
- グラフのバージョン管理
- 定期的なクリーンアップ
- データエクスポート機能

## 14. Git連携によるバージョン管理（Phase 2拡張）

### 14.1 目的

要件定義書の変更履歴を自動的に記録し、いつでも過去のバージョンに戻れるようにする。
AIが要件定義書を更新するたびに、Gitで自動的にコミットすることで、変更の追跡とトレーサビリティを実現する。

### 14.2 機能概要

#### 14.2.1 自動コミット機能
- AIが要件定義書を更新するたびに自動的にGitコミット
- コミットメッセージには変更内容の要約を自動生成
- ユーザーの回答内容もコミットメッセージに含める

#### 14.2.2 バージョン履歴表示
- 要件定義書の変更履歴を時系列で表示
- 各バージョンの差分を確認
- 特定のバージョンに戻す機能

#### 14.2.3 ブランチ戦略
- シンプルに1つのブランチ（mainまたはmaster）のみを使用
- コミット履歴で変更を追跡

### 14.3 実装詳細

#### 14.3.1 Gitリポジトリ初期化

要件定義書保存ディレクトリをGitリポジトリとして初期化：
```bash
cd data/requirements
git init
git config user.name "Requirements AI"
git config user.email "ai@requirement-support.local"
```

#### 14.3.2 自動コミットフロー

```python
# 要件定義書更新後
async def save_and_commit_requirements(
    session_id: str,
    requirements: str,
    commit_message: str
):
    # 1. ファイルを保存
    file_path = f"data/requirements/{session_id}.md"
    with open(file_path, "w") as f:
        f.write(requirements)

    # 2. Gitに追加
    subprocess.run(["git", "add", file_path], cwd="data/requirements")

    # 3. コミット
    subprocess.run(
        ["git", "commit", "-m", commit_message],
        cwd="data/requirements"
    )
```

#### 14.3.3 コミットメッセージ生成

```python
def generate_commit_message(question: str, answer: str, changes: str) -> str:
    """
    コミットメッセージを生成

    例:
    Update requirements: Add authentication details

    Question: ユーザー認証は必要ですか？
    Answer: はい、メールアドレスとパスワードでログインします

    Changes:
    - Added user authentication requirements
    - Specified login method (email + password)
    """
    return f"""Update requirements: {extract_summary(changes)}

Question: {question}
Answer: {answer}

Changes:
{format_changes(changes)}
"""
```

#### 14.3.4 バージョン履歴取得

```python
def get_version_history(session_id: str) -> List[Dict]:
    """
    バージョン履歴を取得

    Returns:
        [
            {
                "commit_hash": "abc123",
                "timestamp": "2025-11-10 10:30:00",
                "message": "Update requirements: Add authentication details",
                "author": "Requirements AI"
            }
        ]
    """
    result = subprocess.run(
        [
            "git", "log",
            "--format=%H|%aI|%s|%an",
            "--", f"{session_id}.md"
        ],
        cwd="data/requirements",
        capture_output=True,
        text=True
    )

    versions = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        hash, timestamp, message, author = line.split("|")
        versions.append({
            "commit_hash": hash,
            "timestamp": timestamp,
            "message": message,
            "author": author
        })

    return versions
```

#### 14.3.5 差分表示

```python
def get_diff(session_id: str, commit_hash: str) -> str:
    """
    特定のコミットの差分を取得
    """
    result = subprocess.run(
        [
            "git", "show",
            f"{commit_hash}:{session_id}.md"
        ],
        cwd="data/requirements",
        capture_output=True,
        text=True
    )

    return result.stdout
```

### 14.4 API拡張

#### 14.4.1 新規エンドポイント

- `GET /api/version/history/{session_id}` - バージョン履歴取得
- `GET /api/version/diff/{session_id}/{commit_hash}` - 差分表示
- `POST /api/version/revert/{session_id}` - 特定バージョンに戻す

#### 14.4.2 バージョン履歴API

**リクエスト**: `GET /api/version/history/{session_id}`

**レスポンス**:
```json
{
  "session_id": "session-123",
  "versions": [
    {
      "commit_hash": "abc123def456",
      "timestamp": "2025-11-10T10:30:00Z",
      "message": "Update requirements: Add authentication details",
      "author": "Requirements AI",
      "short_hash": "abc123d"
    },
    {
      "commit_hash": "def789ghi012",
      "timestamp": "2025-11-10T10:25:00Z",
      "message": "Initial requirements draft",
      "author": "Requirements AI",
      "short_hash": "def789g"
    }
  ]
}
```

#### 14.4.3 差分表示API

**リクエスト**: `GET /api/version/diff/{session_id}?from={hash1}&to={hash2}`

**レスポンス**:
```json
{
  "session_id": "session-123",
  "from_commit": "abc123d",
  "to_commit": "def789g",
  "diff": "--- a/session-123.md\n+++ b/session-123.md\n@@ -10,0 +11,5 @@\n+## 認証機能\n+- メールアドレスとパスワードでログイン\n+- パスワードは8文字以上"
}
```

### 14.5 UI実装

#### 14.5.1 バージョン履歴パネル

ブレークダウン画面に「履歴」タブを追加：
```
┌────────────────────────────────────────┐
│ 要件定義書  │  AIチャット  │  履歴     │
├────────────────────────────────────────┤
│                                        │
│  ⏱️  2025-11-10 10:30                  │
│  Update requirements: Add auth details │
│  [詳細を見る] [このバージョンに戻す]     │
│                                        │
│  ⏱️  2025-11-10 10:25                  │
│  Initial requirements draft            │
│  [詳細を見る] [このバージョンに戻す]     │
│                                        │
└────────────────────────────────────────┘
```

#### 14.5.2 差分表示モーダル

バージョンをクリックすると差分を表示：
```
┌──────────────────────────────────────────┐
│  バージョン比較                           │
│  abc123d (2025-11-10 10:30)              │
│  ← → def789g (2025-11-10 10:25)         │
├──────────────────────────────────────────┤
│                                          │
│  + ## 認証機能                           │
│  + - メールアドレスとパスワードでログイン  │
│  + - パスワードは8文字以上                │
│                                          │
└──────────────────────────────────────────┘
```

### 14.6 技術スタック

#### 14.6.1 バックエンド追加ライブラリ
- `gitpython`: PythonからGitを操作（オプション）
- または標準の`subprocess`モジュールを使用

#### 14.6.2 フロントエンド追加ライブラリ
- `react-diff-viewer`: 差分表示コンポーネント

### 14.7 実装ステップ

1. **Gitリポジトリ初期化**
   - data/requirementsディレクトリをGitリポジトリ化
   - .gitignoreの設定

2. **バックエンド実装**
   - バージョン管理サービス実装
   - 自動コミット機能
   - 履歴取得API
   - 差分取得API

3. **フロントエンド実装**
   - 履歴表示コンポーネント
   - 差分表示モーダル
   - バージョン復元機能

4. **テストと検証**
   - コミット機能のテスト
   - 履歴表示のテスト
   - 差分表示のテスト

### 14.8 運用上の考慮事項

#### 14.8.1 データバックアップ
- Gitリポジトリ全体の定期バックアップ
- リモートリポジトリへのプッシュ（オプション）

#### 14.8.2 容量管理
- 古いセッションの定期的なアーカイブ
- Git履歴の圧縮（git gc）

#### 14.8.3 セキュリティ
- 要件定義書に機密情報が含まれる場合の暗号化
- アクセス制御

---

**文書バージョン**: 1.2
**作成日**: 2025-11-10
**最終更新日**: 2025-11-10
**更新内容**:
- GraphRAG + Neo4j統合計画を追加
- Git連携によるバージョン管理計画を追加
