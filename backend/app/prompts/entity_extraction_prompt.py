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

【抽出例】

入力テキスト:
```
## 対象ユーザー
- 一般ユーザー: 書籍の検索・予約が可能
- 管理者: ユーザー情報の管理が可能

## 機能要件
### ログイン機能
ユーザーはメールアドレスとパスワードでログインできる。
ユーザー情報を参照してログイン認証を行う。

### 非機能要件
個人情報（ユーザー情報）は暗号化して保存すること。
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
      "type": "Requirement",
      "id": "REQ-001",
      "properties": {{
        "name": "個人情報は暗号化して保存すること",
        "type": "Security"
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
      "type": "APPLIES_TO",
      "source_id": "REQ-001",
      "target_id": "DATA-001",
      "properties": {{}}
    }}
  ]
}}
```

【出力形式】
上記の例と同じJSON形式で出力してください。
- `entities`: エンティティの配列
  - `type`: エンティティタイプ（Actor, Function, Data, Requirement のいずれか）
  - `id`: 一意のID（例: ACTOR-001, FUNC-001）
  - `properties`: プロパティ（必須プロパティを必ず含める）
- `relations`: リレーションシップの配列
  - `type`: リレーションタイプ（USES, MANIPULATES, DEPENDS_ON, APPLIES_TO, AUTHORIZES のいずれか）
  - `source_id`: ソースエンティティのID
  - `target_id`: ターゲットエンティティのID
  - `properties`: プロパティ（リレーションタイプに応じて action や permission を設定）

**重要**: JSON形式のみを出力してください。説明文は不要です。
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
