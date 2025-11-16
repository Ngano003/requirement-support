# GraphRAG 知識グラフスキーマ仕様書（IS/SHOULDレイヤーモデル）

## 目次

1. [概要](#概要)
2. [設計コンセプト](#設計コンセプト)
3. [ノード（エンティティ）定義](#ノード定義)
4. [エッジ（リレーション）定義](#エッジ定義)
5. [検出クエリ仕様](#検出クエリ仕様)
6. [実装ガイド](#実装ガイド)
7. [使用例](#使用例)

---

## 概要

本仕様書は、要件定義書からナレッジグラフを構築し、ヌケモレ（specification gaps）と矛盾（contradictions）を自動検出するためのグラフスキーマ定義を提供します。

### 目的

- 要件定義書の品質向上
- 仕様漏れの早期発見
- 論理的矛盾の自動検出
- 要件間の依存関係の可視化

### 技術スタック

| コンポーネント | 技術 | 用途 |
|--------------|------|------|
| グラフDB | Memgraph (Neo4j互換) | ナレッジグラフの永続化・検索 |
| LLM | vLLM / Google AI / OpenRouter | エンティティ抽出・**矛盾の論理判定** |
| オーケストレーター | LlamaIndex | LLMとグラフDBの連携 |
| クエリ言語 | Cypher | **矛盾候補ペアの抽出** |

### 検出アプローチ

**ヌケモレ（Gaps）検出**: Cypherクエリで確定的に検出
- 例: 孤立Function、未充足Requirement、孤立Hardware

**矛盾（Contradictions）検出**: Cypherで候補抽出 → LLMで論理判定
- Cypherの役割: 矛盾の**可能性がある**ペアや構造パスを抽出
- LLMの役割: 抽出された候補が本当に矛盾しているか**論理的に判定**
- 理由: 自然言語で記述された制約の意味的矛盾は、グラフパターンマッチングだけでは判定不可能

---

## 設計コンセプト

### IS/SHOULDレイヤーモデル

グラフを「構造（IS）」と「制約（SHOULD）」の2つの概念的レイヤーに分離して1つのデータベースに格納します。

#### ISレイヤー（構造グラフ: What it IS）

**目的**: システムの「事実」の構造を記述し、ヌケモレ（孤立）を検出

**モデル**: Function中心モデル
- Actor, Requirement, Data, Hardware が Function とリンク
- Function同士が DEPENDS_ON でリンク

**検出可能な問題**:
- 孤立したFunction（他のFunctionやActorと無関係）
- Functionと関係を持たないActor/Requirement/Data/Hardware

#### SHOULDレイヤー（制約グラフ: What it SHOULD be）

**目的**: システムが「守るべき」ルールを記述し、矛盾を検出

**モデル**: Constraint中心モデル
- Constraint がすべてのノード（Function/Data/Hardware/Actor/Requirement）とリンク可能

**検出可能な問題**:
- 同一対象への矛盾するConstraint（LLM判定）
- セキュリティ制約の漏れ
- IS vs SHOULD の矛盾（構造パスと禁止ルールの競合）

### 関係性の原則

```
ISレイヤー:
1. Actor/Requirement は Function とのみ関係を持つ
2. Data/Hardware は Function とのみ関係を持つ
3. Function は Function と関係を持つ（依存関係）

SHOULDレイヤー:
4. Constraint はすべてのノードと関係を持つ
```

---

## ノード定義

### 🟢 Actor（アクター）

**定義**: システムを利用する人、役割（ロール）、または外部システム

**レイヤー**: ISレイヤー

**必須プロパティ**:
- `name` (string): アクター名

**オプショナルプロパティ**:
- `role` (string): 役割
- `description` (string): 説明

**抽出パターン**:
- 〜ユーザー
- 〜管理者
- 〜担当者
- 〜システム
- 対象ユーザー
- アクター
- 利用者

**例**:
```json
{
  "id": "ACTOR-001",
  "type": "Actor",
  "properties": {
    "name": "一般ユーザー",
    "role": "図書館利用者",
    "description": "書籍の検索・予約が可能"
  }
}
```

---

### 🟡 Function（機能）

**定義**: システムが提供する具体的な機能やユースケース、制御ロジック

**レイヤー**: ISレイヤー（**ハブ**として機能）

**必須プロパティ**:
- `name` (string): 機能名

**オプショナルプロパティ**:
- `description` (string): 説明
- `inputs` (array): 入力
- `outputs` (array): 出力

**抽出パターン**:
- 〜機能
- 〜処理
- 〜操作
- ユーザーは〜できる
- システムは〜する
- ユースケース

**例**:
```json
{
  "id": "FUNC-001",
  "type": "Function",
  "properties": {
    "name": "書籍検索機能",
    "description": "タイトル、著者、ISBN、カテゴリーで書籍を検索",
    "inputs": ["検索キーワード"],
    "outputs": ["検索結果リスト"]
  }
}
```

---

### ⚪️ Data（データ）

**定義**: システムが扱う情報、DBテーブル、主要なデータエンティティ

**レイヤー**: ISレイヤー

**必須プロパティ**:
- `name` (string): データ名

**オプショナルプロパティ**:
- `attributes` (array): 属性
- `data_type` (string): データ型
- `sensitivity` (enum): 機密性レベル（'low', 'medium', 'high', 'confidential'）

**抽出パターン**:
- 〜情報
- 〜データ
- 〜マスタ
- 〜テーブル
- データベース
- エンティティ

**例**:
```json
{
  "id": "DATA-001",
  "type": "Data",
  "properties": {
    "name": "ユーザー情報",
    "attributes": ["ユーザーID", "氏名", "メールアドレス"],
    "sensitivity": "high"
  }
}
```

---

### 🟠 Hardware（ハードウェア）

**定義**: 物理的なデバイス、サーバー、インフラストラクチャ、IoTデバイス

**レイヤー**: ISレイヤー

**必須プロパティ**:
- `name` (string): ハードウェア名

**オプショナルプロパティ**:
- `description` (string): 説明
- `device_type` (string): デバイス種別
- `kind` (string): 詳細分類

**抽出パターン**:
- 〜サーバー
- 〜デバイス
- 〜リーダー
- PC
- スマートフォン
- ハードウェア
- インフラ

**例**:
```json
{
  "id": "HW-001",
  "type": "Hardware",
  "properties": {
    "name": "Webサーバー",
    "device_type": "Server",
    "description": "アプリケーションを実行し、リクエストを処理"
  }
}
```

---

### 🟢 Requirement（やるべきこと）

**定義**: システムが実現すべき機能や振る舞いそのもの

**レイヤー**: ISレイヤー

**必須プロパティ**:
- `name` (string): 要件名

**オプショナルプロパティ**:
- `description` (string): 説明
- `priority` (enum): 優先度（'high', 'medium', 'low'）
- `type` (enum): 要件タイプ（'Functional', 'BusinessRule'）

**抽出パターン**:
- 〜要件
- 〜機能
- 〜を提供する
- 〜を行う
- 〜できること
- 実現すべき

**例**:
```json
{
  "id": "REQ-001",
  "type": "Requirement",
  "properties": {
    "name": "ログイン認証要件",
    "description": "ユーザー情報を参照してログイン認証を行うこと",
    "type": "Functional"
  }
}
```

---

### 🔵 Constraint（守るべきこと）

**定義**: FunctionやHardwareに課せられる制約条件（非機能要件）

**レイヤー**: SHOULDレイヤー（**中心**として機能）

**必須プロパティ**:
- `name` (string): 制約名
- `category` (enum): カテゴリー（下記参照）

**オプショナルプロパティ**:
- `description` (string): 説明
- `value` (string): 制約値
- `priority` (enum): 優先度

**カテゴリー**:
- `Timing`: タイミング制約（周期、応答時間など）
- `Performance`: 性能制約（スループット、同時接続数など）
- `Safety`: 安全性制約（ASIL、ISO26262など）
- `Security`: セキュリティ制約（暗号化、認証など）
- `Availability`: 可用性制約（稼働率など）
- `Reliability`: 信頼性制約（MTBF、故障率など）
- `Maintainability`: 保守性制約（修正時間など）
- `Usability`: ユーザビリティ制約（操作時間など）
- `Capacity`: 容量制約（メモリ、ストレージなど）
- `Compatibility`: 互換性制約（プロトコル、規格など）
- `Environmental`: 環境制約（温度、湿度など）
- `Regulatory`: 規制制約（法規制、標準規格など）

**抽出パターン**:
- 〜しなければならない
- 〜すること
- 制約
- 条件
- 仕様
- 以内
- 以上
- 準拠

**例**:
```json
{
  "id": "CONST-001",
  "type": "Constraint",
  "properties": {
    "name": "書籍検索応答時間制約",
    "category": "Performance",
    "description": "書籍検索は、1秒以内に結果を返すこと",
    "value": "1秒以内"
  }
}
```

---

## エッジ定義

### ISレイヤー: Actor <-> Function

#### USES（使用）

**定義**: アクターが機能を利用する

**方向**: `(Actor) -[:USES]-> (Function)`

**プロパティ**: なし

**検出パターン**:
- は〜できる
- が使用
- が利用
- でアクセス

**例**:
```json
{
  "type": "USES",
  "source_id": "ACTOR-001",
  "target_id": "FUNC-001",
  "properties": {}
}
```

---

#### AUTHORIZES（権限付与）

**定義**: アクターが機能に対する権限を持つ

**方向**: `(Actor) -[:AUTHORIZES]-> (Function)`

**プロパティ**:
- `permission` (enum): 'Allow' または 'Deny'

**検出パターン**:
- が可能
- ができない
- を許可
- を禁止
- の権限

**例**:
```json
{
  "type": "AUTHORIZES",
  "source_id": "ACTOR-001",
  "target_id": "FUNC-002",
  "properties": {
    "permission": "Allow"
  }
}
```

---

### ISレイヤー: Function <-> Requirement

#### SATISFIES（満たす）

**定義**: 機能が要件を満たす

**方向**: `(Function) -[:SATISFIES]-> (Requirement)`

**プロパティ**: なし

**検出パターン**:
- を満たす
- を実現する
- に対応する
- の要件

**例**:
```json
{
  "type": "SATISFIES",
  "source_id": "FUNC-001",
  "target_id": "REQ-001",
  "properties": {}
}
```

---

### ISレイヤー: Function <-> Data

#### MANIPULATES（操作）

**定義**: 機能がデータを操作する

**方向**: `(Function) -[:MANIPULATES]-> (Data)`

**プロパティ**:
- `action` (enum): 'Read', 'Write', 'Delete', 'ReadWrite'

**検出パターン**:
- を参照
- を読み込む
- を更新
- を作成
- を削除
- に保存
- から取得

**例**:
```json
{
  "type": "MANIPULATES",
  "source_id": "FUNC-001",
  "target_id": "DATA-001",
  "properties": {
    "action": "Read"
  }
}
```

---

### ISレイヤー: Function <-> Hardware

#### CONTROLS（制御）

**定義**: 機能がハードウェアを制御する

**方向**: `(Function) -[:CONTROLS]-> (Hardware)`

**プロパティ**:
- `control_type` (enum): 'Input', 'Output', 'InputOutput'

**検出パターン**:
- を制御
- を操作
- から読み取る
- に出力
- を駆動
- からセンシング

**例**:
```json
{
  "type": "CONTROLS",
  "source_id": "FUNC-003",
  "target_id": "HW-001",
  "properties": {
    "control_type": "Output"
  }
}
```

---

### ISレイヤー: Function <-> Function

#### DEPENDS_ON（依存）

**定義**: 機能が別の機能に依存する

**方向**: `(Function) -[:DEPENDS_ON]-> (Function)`

**プロパティ**: なし

**検出パターン**:
- が前提
- に依存
- の後に
- が必要
- を前提とする

**例**:
```json
{
  "type": "DEPENDS_ON",
  "source_id": "FUNC-002",
  "target_id": "FUNC-001",
  "properties": {}
}
```

---

### SHOULDレイヤー: Constraint <-> Any

#### APPLIES_TO（適用）

**定義**: 制約がノードに適用される

**方向**: `(Constraint) -[:APPLIES_TO]-> (Function|Data|Hardware|Actor|Requirement)`

**プロパティ**:
- `constraint_type` (enum, optional): 'mandatory', 'optional'

**検出パターン**:
- に適用
- に従う
- の制約
- を守る
- 準拠
- しなければならない

**例**:
```json
{
  "type": "APPLIES_TO",
  "source_id": "CONST-001",
  "target_id": "FUNC-001",
  "properties": {
    "constraint_type": "mandatory"
  }
}
```

---

## 検出クエリ仕様

### 検出クエリの分類

| クエリID | 検出対象 | 検出方法 | LLM判定 |
|---------|---------|---------|---------|
| 1-7 | ヌケモレ（ISレイヤー + SHOULDレイヤー） | Cypher確定検出 | ❌ 不要 |
| 8 | 循環依存 | Cypher確定検出 | ❌ 不要 |
| 9 | 権限競合 | Cypher候補抽出 | ✅ 必要 |
| 10 | データ書き込み競合 | Cypher候補抽出 | ✅ 必要 |
| 11 | Constraint競合 | Cypher候補抽出 | ✅ 必要 |
| 12-A | Actor→Hardware矛盾 | Cypher候補抽出 | ✅ 必要 |
| 12-B | Actor→Data矛盾 | Cypher候補抽出 | ✅ 必要 |

---

### ヌケモレ検出クエリ（ISレイヤー）

#### 1. 孤立したFunction

**目的**: 他のFunctionやActorと無関係なFunctionを検出

**Cypherクエリ**:
```cypher
MATCH (f:Function {session_id: $session_id})
OPTIONAL MATCH (f)-[:DEPENDS_ON]->(:Function {session_id: $session_id})
OPTIONAL MATCH (f)<-[:DEPENDS_ON]-(:Function {session_id: $session_id})
OPTIONAL MATCH (a:Actor {session_id: $session_id})-[:USES]->(f)
WITH f, count(DISTINCT a) AS actor_count
WHERE actor_count = 0
RETURN f.name AS function_name,
       f.description AS description,
       '孤立したFunction' AS issue_type
```

---

#### 2. Functionと関係を持たないActor

**目的**: どのFunctionも使用しないActorを検出

**Cypherクエリ**:
```cypher
MATCH (a:Actor {session_id: $session_id})
OPTIONAL MATCH (a)-[:USES]->(:Function {session_id: $session_id})
WITH a, count(*) AS uses_count
WHERE uses_count = 0
RETURN a.name AS actor_name,
       'Functionと関係を持たないActor' AS issue_type
```

---

#### 3. Functionによって満たされていないRequirement

**目的**: どのFunctionからもSATISFIESされていないRequirementを検出

**Cypherクエリ**:
```cypher
MATCH (r:Requirement {session_id: $session_id})
OPTIONAL MATCH (f:Function {session_id: $session_id})-[:SATISFIES]->(r)
WITH r, count(f) AS satisfies_count
WHERE satisfies_count = 0
RETURN r.name AS requirement_name,
       'Functionによって満たされていないRequirement' AS issue_type
```

---

#### 4. Functionと関係を持たないData

**目的**: どのFunctionからもMANIPULATESされていないDataを検出

**Cypherクエリ**:
```cypher
MATCH (d:Data {session_id: $session_id})
OPTIONAL MATCH (f:Function {session_id: $session_id})-[:MANIPULATES]->(d)
WITH d, count(f) AS manipulates_count
WHERE manipulates_count = 0
RETURN d.name AS data_name,
       'Functionと関係を持たないData' AS issue_type
```

---

#### 5. Functionと関係を持たないHardware

**目的**: どのFunctionからもCONTROLSされていないHardwareを検出

**Cypherクエリ**:
```cypher
MATCH (h:Hardware {session_id: $session_id})
OPTIONAL MATCH (f:Function {session_id: $session_id})-[:CONTROLS]->(h)
WITH h, count(f) AS controls_count
WHERE controls_count = 0
RETURN h.name AS hardware_name,
       'Functionと関係を持たないHardware' AS issue_type
```

---

### ヌケモレ検出クエリ（SHOULDレイヤー）

#### 6. 適用対象のないConstraint

**目的**: どのノードにもAPPLIES_TOされていないConstraintを検出

**Cypherクエリ**:
```cypher
MATCH (c:Constraint {session_id: $session_id})
OPTIONAL MATCH (c)-[:APPLIES_TO]->()
WITH c, count(*) AS applies_count
WHERE applies_count = 0
RETURN c.name AS constraint_name,
       c.category AS category,
       '適用対象のないConstraint' AS issue_type
```

---

### 矛盾検出クエリ（ISレイヤー内部）

#### 8. Function間の循環依存

**目的**: DEPENDS_ONのループを検出（確定的検出）

**Cypherクエリ**:
```cypher
MATCH path = (f1:Function {session_id: $session_id})-[:DEPENDS_ON*]->(f1)
RETURN f1.name AS function_name,
       [n IN nodes(path) | n.name] AS cycle_path,
       'Function間の循環依存' AS issue_type
```

**説明**: 循環依存は論理的に確定できるため、LLM判定不要。

---

#### 9. 権限の競合候補（LLM判定用）

**目的**: 同一ActorとFunctionにAllow と Deny が設定されている候補を抽出し、LLMで矛盾判定

**Cypherクエリ**:
```cypher
MATCH (a:Actor {session_id: $session_id})-[r1:AUTHORIZES]->(f:Function {session_id: $session_id}),
      (a)-[r2:AUTHORIZES]->(f)
WHERE r1.permission <> r2.permission
  AND id(r1) < id(r2)
RETURN a.name AS actor_name,
       a.entity_id AS actor_id,
       f.name AS function_name,
       f.entity_id AS function_id,
       f.description AS function_description,
       r1.permission AS permission1,
       r2.permission AS permission2,
       '権限競合候補（LLM判定必要）' AS issue_type
```

**LLM判定プロンプト**:
```
以下の権限設定は論理的に矛盾していますか？

アクター: {actor_name}
機能: {function_name} - {function_description}
権限1: {permission1}
権限2: {permission2}

【出力形式】
必ず以下のJSON形式で回答してください：
```json
{
  "answer": "YES" または "NO" または "UNCLEAR",
  "reasoning": "矛盾の有無とその理由を説明",
  "recommended_action": "推奨される対処方法"
}
```
```

---

#### 10. データ同時書き込み競合候補（LLM判定用）

**目的**: 依存関係なしに複数FunctionがWriteするデータを抽出し、LLMでトランザクション競合の可能性を判定

**Cypherクエリ**:
```cypher
MATCH (f1:Function {session_id: $session_id})-[m1:MANIPULATES]->(d:Data {session_id: $session_id}),
      (f2:Function {session_id: $session_id})-[m2:MANIPULATES]->(d)
WHERE f1.name < f2.name
  AND (m1.action CONTAINS 'Write' OR m1.action = 'Write')
  AND (m2.action CONTAINS 'Write' OR m2.action = 'Write')

OPTIONAL MATCH (f1)-[r_f1_f2:DEPENDS_ON]->(f2)
OPTIONAL MATCH (f2)-[r_f2_f1:DEPENDS_ON]->(f1)

WITH f1, f2, d, r_f1_f2, r_f2_f1, m1, m2
WHERE r_f1_f2 IS NULL AND r_f2_f1 IS NULL

RETURN d.name AS data_name,
       d.entity_id AS data_id,
       d.description AS data_description,
       f1.name AS function1,
       f1.entity_id AS function1_id,
       f1.description AS function1_description,
       f2.name AS function2,
       f2.entity_id AS function2_id,
       f2.description AS function2_description,
       m1.action AS function1_action,
       m2.action AS function2_action,
       'データ同時書き込み候補（LLM判定必要）' AS issue_type
```

**LLM判定プロンプト**:
```
以下の2つの機能が同じデータに対して書き込みを行いますが、依存関係がありません。トランザクション競合の問題はありますか？

データ: {data_name} - {data_description}

機能1: {function1} - {function1_description}
  操作: {function1_action}

機能2: {function2} - {function2_description}
  操作: {function2_action}

【出力形式】
必ず以下のJSON形式で回答してください：
```json
{
  "answer": "YES" または "NO" または "UNCLEAR",
  "reasoning": "矛盾の有無とその理由を説明",
  "recommended_action": "推奨される対処方法"
}
```
```

---

### 矛盾検出クエリ（SHOULDレイヤー内部 - LLM判定用）

#### 11. Constraint同士の競合候補

**目的**: 同一対象に複数のConstraintが適用されているペアを抽出（LLMで論理的矛盾を判定）

**Cypherクエリ**:
```cypher
MATCH (c1:Constraint {session_id: $session_id})-[:APPLIES_TO]->(target_node),
      (c2:Constraint {session_id: $session_id})-[:APPLIES_TO]->(target_node)
WHERE id(c1) < id(c2)
RETURN c1.name AS constraint1_name,
       c1.description AS constraint1_description,
       c2.name AS constraint2_name,
       c2.description AS constraint2_description,
       target_node.name AS target_name,
       labels(target_node)[0] AS target_type,
       '同一対象への複数Constraint（LLM判定必要）' AS issue_type
```

**LLM判定プロンプト**:
```
以下の2つの制約は、論理的に両立し得ない矛盾を含んでいますか？

制約1: "{constraint1_description}"
制約2: "{constraint2_description}"

対象: {target_name} ({target_type})

回答 (YES/NO):
```

---

### 矛盾検出クエリ（IS vs SHOULD - LLM判定用）

#### 12-A. Actor→Hardware間接制御と排他制約の矛盾候補

**目的**: ActorがFunctionを経由してHardwareを間接制御できるパスがあるが、Constraintで特定Actorのみに制限されている場合の矛盾を検出

**Cypherクエリ**:
```cypher
// ActorがFunctionを経由してHardwareを制御するパスを検索
MATCH path = (a:Actor {session_id: $session_id})-[:USES]->(f:Function {session_id: $session_id})-[:CONTROLS]->(h:Hardware {session_id: $session_id})

// そのHardwareに適用されている制約を取得
MATCH (c:Constraint {session_id: $session_id})-[:APPLIES_TO]->(h)
WHERE c.description CONTAINS 'のみ' OR c.description CONTAINS 'only'

// 制約が特定Actorにも適用されているか確認
OPTIONAL MATCH (c)-[:APPLIES_TO]->(allowed_actor:Actor {session_id: $session_id})

RETURN a.name AS accessing_actor,
       a.entity_id AS accessing_actor_id,
       f.name AS function_name,
       f.entity_id AS function_id,
       f.description AS function_description,
       h.name AS hardware_name,
       h.entity_id AS hardware_id,
       h.description AS hardware_description,
       c.name AS constraint_name,
       c.entity_id AS constraint_id,
       c.description AS constraint_description,
       c.category AS constraint_category,
       collect(DISTINCT allowed_actor.name) AS allowed_actors,
       [n IN nodes(path) | n.name] AS access_path,
       'Actor-Hardware間接制御と排他制約の矛盾候補（LLM判定必要）' AS issue_type
```

**LLM判定プロンプト**:
```
以下の構造パスと制約を分析し、論理的な矛盾があるか判定してください。

【構造（IS）】
アクセスパス: {accessing_actor} → {function_name} → {hardware_name}
- {accessing_actor}が{function_name}を使用し、その機能が{hardware_name}を制御します

【制約（SHOULD）】
制約: {constraint_name} ({constraint_category})
内容: "{constraint_description}"
許可されているアクター: {allowed_actors}

【質問】
{accessing_actor}は{hardware_name}を間接的に制御できますが、制約"{constraint_description}"と矛盾していますか？

【出力形式】
必ず以下のJSON形式で回答してください：
```json
{
  "answer": "YES" または "NO" または "UNCLEAR",
  "reasoning": "矛盾の有無とその理由を説明",
  "recommended_action": "推奨される対処方法"
}
```
```

---

#### 12-B. Actor→Data間接アクセスと排他制約の矛盾候補

**目的**: ActorがFunctionを経由してDataを間接操作できるパスがあるが、Constraintで特定Actorのみに制限されている場合の矛盾を検出

**Cypherクエリ**:
```cypher
// ActorがFunctionを経由してDataを操作するパスを検索
MATCH path = (a:Actor {session_id: $session_id})-[:USES]->(f:Function {session_id: $session_id})-[:MANIPULATES]->(d:Data {session_id: $session_id})

// そのDataに適用されている制約を取得
MATCH (c:Constraint {session_id: $session_id})-[:APPLIES_TO]->(d)
WHERE c.description CONTAINS 'のみ' OR c.description CONTAINS 'only'

// 制約が特定Actorにも適用されているか確認
OPTIONAL MATCH (c)-[:APPLIES_TO]->(allowed_actor:Actor {session_id: $session_id})

RETURN a.name AS accessing_actor,
       a.entity_id AS accessing_actor_id,
       f.name AS function_name,
       f.entity_id AS function_id,
       f.description AS function_description,
       d.name AS data_name,
       d.entity_id AS data_id,
       d.description AS data_description,
       d.sensitivity AS data_sensitivity,
       c.name AS constraint_name,
       c.entity_id AS constraint_id,
       c.description AS constraint_description,
       c.category AS constraint_category,
       collect(DISTINCT allowed_actor.name) AS allowed_actors,
       [n IN nodes(path) | n.name] AS access_path,
       'Actor-Data間接アクセスと排他制約の矛盾候補（LLM判定必要）' AS issue_type
```

**LLM判定プロンプト**:
```
以下の構造パスと制約を分析し、論理的な矛盾があるか判定してください。

【構造（IS）】
アクセスパス: {accessing_actor} → {function_name} → {data_name}
- {accessing_actor}が{function_name}を使用し、その機能が{data_name}を操作します

【制約（SHOULD）】
制約: {constraint_name} ({constraint_category})
内容: "{constraint_description}"
許可されているアクター: {allowed_actors}
データ機密性: {data_sensitivity}

【質問】
{accessing_actor}は{data_name}を間接的に操作できますが、制約"{constraint_description}"と矛盾していますか？

【出力形式】
必ず以下のJSON形式で回答してください：
```json
{
  "answer": "YES" または "NO" または "UNCLEAR",
  "reasoning": "矛盾の有無とその理由を説明",
  "recommended_action": "推奨される対処方法"
}
```
```

---

## 実装ガイド

### 1. エンティティ抽出フロー

```
要件定義書（テキスト）
  ↓
[LLM] 構造候補抽出
  ↓
[人間] スキーママッピング承認
  ↓
[LLM] ガイド付きエンティティ抽出
  ↓
バリデーション
  ↓
Memgraphに保存
```

### 2. 問題検出フロー

```
Memgraph
  ↓
[Cypher] ヌケモレ検出クエリ実行
  ↓
結果リスト
  ↓
[Cypher] 矛盾検出クエリ実行
  ↓
矛盾候補リスト
  ↓
[LLM] 論理的矛盾判定
  ↓
最終検出結果
```

### 3. コンポーネント構成

| モジュール | ファイル | 役割 |
|-----------|---------|------|
| スキーマ定義 | `knowledge_graph_schema.py` | ノード・エッジ・検出クエリ定義 |
| 構造抽出 | `structure_extractor.py` | 候補抽出 |
| スキーママッピング | `schema_mapper.py` | 候補→標準スキーマ変換 |
| エンティティ抽出 | `entity_extractor.py` | LLMによる抽出 |
| グラフ構築 | `graph_builder.py` | Memgraph保存 |
| 問題検出 | `problem_detector.py` | Cypherクエリ実行 |
| 矛盾判定 | `contradiction_detector.py` | LLM判定 |

---

## 使用例

### 例1: 図書館管理システム

#### 入力（要件定義書の抜粋）

```
【機能要件】
- 一般ユーザーは書籍検索機能を使用できる
- 書籍検索機能は書籍マスタから情報を取得する
- 司書は貸出機能を使用できる
- 貸出機能は貸出履歴テーブルに記録する

【非機能要件】
- ユーザー情報は暗号化して保存すること
- 書籍検索は1秒以内に結果を返すこと
```

#### 抽出されるグラフ

**ノード**:
- Actor: 一般ユーザー、司書
- Function: 書籍検索機能、貸出機能
- Data: 書籍マスタ、貸出履歴テーブル、ユーザー情報
- Requirement: （明示的な要件がないため未抽出）
- Constraint: ユーザー情報暗号化制約、書籍検索応答時間制約

**エッジ**:
- (一般ユーザー) -[:USES]-> (書籍検索機能)
- (司書) -[:USES]-> (貸出機能)
- (書籍検索機能) -[:MANIPULATES {action: "Read"}]-> (書籍マスタ)
- (貸出機能) -[:MANIPULATES {action: "Write"}]-> (貸出履歴テーブル)
- (ユーザー情報暗号化制約) -[:APPLIES_TO]-> (ユーザー情報)
- (書籍検索応答時間制約) -[:APPLIES_TO]-> (書籍検索機能)

#### 検出される問題

**ヌケモレ**:
1. **Functionと関係を持たないData**: ユーザー情報（どのFunctionもMANIPULATESしていない）
2. **適用対象のないConstraint**: なし

**推奨アクション**:
- ユーザー情報を操作するFunction（ログイン機能など）の追加を検討

---

### 例2: 組込み車載コントローラー

#### 入力（要件定義書の抜粋）

```
【機能要件】
REQ-MC-001: 3相ACモーターのベクトル制御を行う
REQ-BMS-010: バッテリーのセルバランシング機能を提供する

【ハードウェア】
- メインECU
- バッテリー温度センサー
- メインリレー

【非機能要件】
CONST-PERF-001: ベクトル制御は1ms周期で実行すること
CONST-FS-001: ASIL-Dに準拠すること
```

#### 抽出されるグラフ

**ノード**:
- Requirement: REQ-MC-001, REQ-BMS-010
- Function: ベクトル制御タスク、セルバランシング制御
- Hardware: メインECU、バッテリー温度センサー、メインリレー
- Constraint: CONST-PERF-001 (Timing), CONST-FS-001 (Safety)

**エッジ**:
- (ベクトル制御タスク) -[:SATISFIES]-> (REQ-MC-001)
- (セルバランシング制御) -[:SATISFIES]-> (REQ-BMS-010)
- (ベクトル制御タスク) -[:CONTROLS {control_type: "Output"}]-> (メインECU)
- (セルバランシング制御) -[:CONTROLS {control_type: "Input"}]-> (バッテリー温度センサー)
- (CONST-PERF-001) -[:APPLIES_TO]-> (ベクトル制御タスク)
- (CONST-FS-001) -[:APPLIES_TO]-> (ベクトル制御タスク)
- (CONST-FS-001) -[:APPLIES_TO]-> (セルバランシング制御)

#### 検出される問題

**ヌケモレ**:
1. **Functionと関係を持たないHardware**: メインリレー（どのFunctionもCONTROLSしていない）

**推奨アクション**:
- メインリレーを制御するFunction（緊急停止機能など）の追加を検討

---

## 補足

### Memgraph vs Neo4j

本スキーマはMemgraphを想定していますが、Neo4jでも動作します。ただし、以下の点に注意してください：

- **EXISTS構文**: Memgraphでは`OPTIONAL MATCH + count()`を使用
- **リスト内包表記**: Memgraphでは`nodes(path)`を返しPython側で処理

### LLM判定の閾値

LLMによる矛盾判定は以下の閾値を推奨します：

- **Constraint競合**: 信頼度 > 0.8 で矛盾と判定
- **IS vs SHOULD矛盾**: 信頼度 > 0.9 で矛盾と判定

---

## 改訂履歴

| バージョン | 日付 | 変更内容 |
|-----------|------|----------|
| 1.0 | 2025-01-16 | IS/SHOULDレイヤーモデル初版作成 |

---

**文書作成者**: Claude (Anthropic)
**レビュー**: 要
