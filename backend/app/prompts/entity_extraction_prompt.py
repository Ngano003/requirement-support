"""
エンティティ抽出用プロンプトテンプレート

LlamaIndexまたはLLMに渡すプロンプトを生成します。
knowledge_graph_schema.py で定義されたスキーマに基づいてエンティティとリレーションを抽出します。
"""

from app.schemas.knowledge_graph_schema import (
    ENTITY_TYPES,
    RELATION_TYPES,
    RequirementTypeEnum,
    ManipulateActionEnum,
    PermissionEnum,
    get_entity_types_description,
    get_relation_types_description,
)


ENTITY_EXTRACTION_SYSTEM_PROMPT = """あなたは要件定義書から構造化された知識グラフを構築する専門家です。

以下のルールに従って、エンティティとリレーションシップを抽出してください：

1. **正確性**: テキストに明示的に記述されている情報のみを抽出する
2. **一貫性**: 同じ概念は同じエンティティとして扱う（例: "ユーザー" と "利用者" は同一）
3. **完全性**: 関連するエンティティとリレーションシップを漏れなく抽出する
4. **構造化**: 必ず指定されたJSON形式で出力する
"""


ENTITY_EXTRACTION_PROMPT_TEMPLATE = """
以下の要件定義書から、知識グラフを構築するためのエンティティとリレーションシップを抽出してください。

【要件定義書】
```
{requirements_text}
```

【抽出するエンティティタイプ】
{entity_types_description}

【抽出するリレーションタイプ】
{relation_types_description}

【重要な抽出ルール】

## 1. Requirement（要件）の抽出
要件の `type` プロパティには以下のいずれかを設定してください：
- **Functional**: 機能要件（「〜機能を提供する」）
- **Security**: セキュリティ要件（「暗号化する」「認証する」）
- **Performance**: 性能要件（「応答時間は〜秒以内」）
- **Availability**: 可用性要件（「稼働率99.9%」）
- **Maintainability**: 保守性要件（「ログを出力する」）
- **BusinessRule**: ビジネスルール（「〜の場合のみ許可」）
- **Constraint**: 制約条件（「〜でなければならない」）

## 2. MANIPULATES リレーションの action プロパティ
データ操作のリレーションには必ず `action` を設定してください：
- **Read**: データを参照・読み込む
- **Write**: データを作成・更新する
- **Delete**: データを削除する
- **ReadWrite**: 読み込みと書き込みの両方

## 3. AUTHORIZES リレーションの permission プロパティ
権限のリレーションには必ず `permission` を設定してください：
- **Allow**: 許可
- **Deny**: 禁止

【抽出ルール: Constraint（制約条件）について】

**Constraint（守るべきこと）は、必ず独立したエンティティとして抽出してください。**

Constraintの特徴:
- 「〜しなければならない」「〜すること」「〜以内」「〜以上」などの表現
- 機能やハードウェア、データに課せられる制約
- 必須プロパティ: `name`, `category`
- `category`の値は以下のいずれか:
  - **Performance**: 性能（応答時間、スループットなど）
  - **Timing**: タイミング（周期、実行タイミングなど）
  - **Safety**: 安全性（ASIL、ISO26262など）
  - **Security**: セキュリティ（暗号化、認証など）
  - **Availability**: 可用性（稼働率など）
  - **Reliability**: 信頼性（MTBF、故障率など）
  - **Maintainability**: 保守性（修正時間など）
  - **Usability**: ユーザビリティ（操作時間など）
  - **Capacity**: 容量（メモリ、ストレージなど）
  - **Compatibility**: 互換性（プロトコル、規格など）
  - **Environmental**: 環境（温度、湿度など）
  - **Regulatory**: 規制（法規制、標準規格など）

【抽出例1: 基本的な機能とデータ】

入力テキスト:
```
## 対象ユーザー
- 一般ユーザー: 書籍の検索・予約が可能
- 管理者: ユーザー情報の管理が可能

## 機能要件
### ログイン機能
ユーザーはメールアドレスとパスワードでログインできる。
ユーザー情報を参照してログイン認証を行う。
```

出力:
```json
{{
  "entities": [
    {{
      "type": "Actor",
      "id": "ACTOR-001",
      "properties": {{
        "name": "一般ユーザー",
        "role": "user"
      }}
    }},
    {{
      "type": "Actor",
      "id": "ACTOR-002",
      "properties": {{
        "name": "管理者",
        "role": "admin"
      }}
    }},
    {{
      "type": "Function",
      "id": "FUNC-001",
      "properties": {{
        "name": "ログイン機能",
        "description": "メールアドレスとパスワードでログイン"
      }}
    }},
    {{
      "type": "Function",
      "id": "FUNC-002",
      "properties": {{
        "name": "書籍検索機能"
      }}
    }},
    {{
      "type": "Function",
      "id": "FUNC-003",
      "properties": {{
        "name": "ユーザー情報管理機能"
      }}
    }},
    {{
      "type": "Data",
      "id": "DATA-001",
      "properties": {{
        "name": "ユーザー情報",
        "sensitivity": "confidential"
      }}
    }},
    {{
      "type": "Data",
      "id": "DATA-002",
      "properties": {{
        "name": "書籍情報"
      }}
    }}
  ],
  "relations": [
    {{
      "type": "USES",
      "source_id": "ACTOR-001",
      "target_id": "FUNC-001",
      "properties": {{}}
    }},
    {{
      "type": "USES",
      "source_id": "ACTOR-001",
      "target_id": "FUNC-002",
      "properties": {{}}
    }},
    {{
      "type": "AUTHORIZES",
      "source_id": "ACTOR-001",
      "target_id": "FUNC-002",
      "properties": {{
        "permission": "Allow"
      }}
    }},
    {{
      "type": "USES",
      "source_id": "ACTOR-002",
      "target_id": "FUNC-003",
      "properties": {{}}
    }},
    {{
      "type": "AUTHORIZES",
      "source_id": "ACTOR-002",
      "target_id": "FUNC-003",
      "properties": {{
        "permission": "Allow"
      }}
    }},
    {{
      "type": "MANIPULATES",
      "source_id": "FUNC-001",
      "target_id": "DATA-001",
      "properties": {{
        "action": "Read"
      }}
    }},
    {{
      "type": "MANIPULATES",
      "source_id": "FUNC-003",
      "target_id": "DATA-001",
      "properties": {{
        "action": "ReadWrite"
      }}
    }},
    {{
      "type": "MANIPULATES",
      "source_id": "FUNC-002",
      "target_id": "DATA-002",
      "properties": {{
        "action": "Read"
      }}
    }}
  ]
}}
```

【抽出例2: 制約条件（Constraint）の抽出】

入力テキスト:
```
## 機能要件
### 暗証番号解錠機能
ユーザーがキーパッドで暗証番号を入力し、認証に成功すればドアロックモーターを作動させて解錠する。

## 非機能要件
### 性能要件
- 暗証番号入力後、解錠完了までの応答時間は3秒以内であること
- システムは同時に最大100件の解錠リクエストを処理できること

### セキュリティ要件
- 認証キーDBは暗号化して保存すること
- 連続3回認証失敗時は、5分間ロックアウトすること

### 安全性要件
- ドアロックモーターの制御はISO26262に準拠すること
- 停電時も手動解錠が可能であること

### 環境要件
- 動作温度範囲は-10℃〜50℃であること
```

出力:
```json
{{
  "entities": [
    {{
      "type": "Function",
      "id": "FUNC-001",
      "properties": {{
        "name": "暗証番号解錠機能",
        "description": "ユーザーがキーパッドで暗証番号を入力し、認証に成功すればドアロックモーターを作動させて解錠する"
      }}
    }},
    {{
      "type": "Hardware",
      "id": "HW-001",
      "properties": {{
        "name": "キーパッド",
        "device_type": "Input"
      }}
    }},
    {{
      "type": "Hardware",
      "id": "HW-002",
      "properties": {{
        "name": "ドアロックモーター",
        "device_type": "Actuator"
      }}
    }},
    {{
      "type": "Data",
      "id": "DATA-001",
      "properties": {{
        "name": "認証キーDB",
        "sensitivity": "confidential"
      }}
    }},
    {{
      "type": "Constraint",
      "id": "CONST-001",
      "properties": {{
        "name": "解錠応答時間制約",
        "description": "暗証番号入力後、解錠完了までの応答時間は3秒以内",
        "category": "Performance",
        "value": "3秒以内"
      }}
    }},
    {{
      "type": "Constraint",
      "id": "CONST-002",
      "properties": {{
        "name": "同時処理数制約",
        "description": "同時に最大100件の解錠リクエストを処理",
        "category": "Performance",
        "value": "最大100件"
      }}
    }},
    {{
      "type": "Constraint",
      "id": "CONST-003",
      "properties": {{
        "name": "認証キーDB暗号化",
        "description": "認証キーDBは暗号化して保存",
        "category": "Security"
      }}
    }},
    {{
      "type": "Constraint",
      "id": "CONST-004",
      "properties": {{
        "name": "ロックアウト制約",
        "description": "連続3回認証失敗時は5分間ロックアウト",
        "category": "Security",
        "value": "3回失敗で5分間"
      }}
    }},
    {{
      "type": "Constraint",
      "id": "CONST-005",
      "properties": {{
        "name": "ISO26262準拠",
        "description": "ドアロックモーターの制御はISO26262に準拠",
        "category": "Safety"
      }}
    }},
    {{
      "type": "Constraint",
      "id": "CONST-006",
      "properties": {{
        "name": "停電時手動解錠",
        "description": "停電時も手動解錠が可能",
        "category": "Safety"
      }}
    }},
    {{
      "type": "Constraint",
      "id": "CONST-007",
      "properties": {{
        "name": "動作温度範囲",
        "description": "動作温度範囲は-10℃〜50℃",
        "category": "Environmental",
        "value": "-10℃〜50℃"
      }}
    }}
  ],
  "relations": [
    {{
      "type": "CONTROLS",
      "source_id": "FUNC-001",
      "target_id": "HW-001",
      "properties": {{
        "control_type": "Input"
      }}
    }},
    {{
      "type": "CONTROLS",
      "source_id": "FUNC-001",
      "target_id": "HW-002",
      "properties": {{
        "control_type": "Output"
      }}
    }},
    {{
      "type": "MANIPULATES",
      "source_id": "FUNC-001",
      "target_id": "DATA-001",
      "properties": {{
        "action": "Read"
      }}
    }},
    {{
      "type": "APPLIES_TO",
      "source_id": "CONST-001",
      "target_id": "FUNC-001",
      "properties": {{}}
    }},
    {{
      "type": "APPLIES_TO",
      "source_id": "CONST-002",
      "target_id": "FUNC-001",
      "properties": {{}}
    }},
    {{
      "type": "APPLIES_TO",
      "source_id": "CONST-003",
      "target_id": "DATA-001",
      "properties": {{}}
    }},
    {{
      "type": "APPLIES_TO",
      "source_id": "CONST-004",
      "target_id": "FUNC-001",
      "properties": {{}}
    }},
    {{
      "type": "APPLIES_TO",
      "source_id": "CONST-005",
      "target_id": "HW-002",
      "properties": {{}}
    }},
    {{
      "type": "APPLIES_TO",
      "source_id": "CONST-006",
      "target_id": "HW-002",
      "properties": {{}}
    }},
    {{
      "type": "APPLIES_TO",
      "source_id": "CONST-007",
      "target_id": "HW-002",
      "properties": {{}}
    }}
  ]
}}
```

**重要なポイント:**
- Constraintは独立したエンティティとして抽出
- 各Constraintには適切な`category`を設定（Performance, Security, Safety, Environmentalなど）
- `value`プロパティに具体的な数値や条件を記載（オプション）
- APPLIES_TOリレーションで適用対象（Function/Data/Hardware）を明確化

【出力形式】
上記の例と同じJSON形式で出力してください。
- `entities`: エンティティの配列
  - `type`: エンティティタイプ（Actor, Function, Data, Requirement, Constraint, Hardware のいずれか）
  - `id`: 一意のID（例: ACTOR-001, FUNC-001, CONST-001）
  - `properties`: プロパティ（必須プロパティを必ず含める）
    - **Constraintの場合**: `name`, `category`（必須）, `description`, `value`（オプション）
- `relations`: リレーションシップの配列
  - `type`: リレーションタイプ（USES, MANIPULATES, DEPENDS_ON, APPLIES_TO, AUTHORIZES, CONTROLS のいずれか）
  - `source_id`: ソースエンティティのID
  - `target_id`: ターゲットエンティティのID
  - `properties`: プロパティ（リレーションタイプに応じて action, permission, control_type を設定）

**重要**:
- JSON形式のみを出力してください。説明文は不要です。
- 制約条件（Constraint）は漏れなく抽出してください。特に「〜しなければならない」「〜以内」「〜すること」などの表現に注意。
"""


def build_entity_extraction_prompt(requirements_text: str) -> str:
    """
    エンティティ抽出用のプロンプトを構築

    Args:
        requirements_text: 要件定義書のテキスト

    Returns:
        LLMに渡すプロンプト
    """
    return ENTITY_EXTRACTION_PROMPT_TEMPLATE.format(
        requirements_text=requirements_text,
        entity_types_description=get_entity_types_description(),
        relation_types_description=get_relation_types_description(),
    )


# ========== リレーション推論プロンプト（オプショナル） ==========

RELATION_INFERENCE_PROMPT_TEMPLATE = """
以下のエンティティリストを見て、明示的には抽出されていないが推論可能なリレーションシップを追加してください。

【既存のエンティティ】
```json
{entities_json}
```

【既存のリレーションシップ】
```json
{relations_json}
```

【推論ルール】
1. **DEPENDS_ON の推論**: Function A が Data X を Write し、Function B が Data X を Read する場合、B は A に依存する可能性がある
2. **AUTHORIZES の推論**: Actor が Function を USES している場合、暗黙的に Allow の AUTHORIZES がある
3. **APPLIES_TO の推論**: Security 要件がある場合、個人情報や決済情報には自動的に適用されるべき

【出力形式】
追加すべきリレーションシップのみをJSON配列で出力してください：
```json
{{
  "inferred_relations": [
    {{
      "type": "DEPENDS_ON",
      "source_id": "FUNC-002",
      "target_id": "FUNC-001",
      "properties": {{
        "reason": "FUNC-002 reads data written by FUNC-001"
      }}
    }}
  ]
}}
```
"""


def build_relation_inference_prompt(entities: list, relations: list) -> str:
    """
    リレーション推論用のプロンプトを構築（オプショナル）

    Args:
        entities: 既存のエンティティリスト
        relations: 既存のリレーションシップリスト

    Returns:
        LLMに渡すプロンプト
    """
    import json

    return RELATION_INFERENCE_PROMPT_TEMPLATE.format(
        entities_json=json.dumps(entities, ensure_ascii=False, indent=2),
        relations_json=json.dumps(relations, ensure_ascii=False, indent=2),
    )
