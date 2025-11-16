"""
要件定義書用 知識グラフスキーマ定義（IS/SHOULDレイヤーモデル）

【設計コンセプト】
グラフを「構造（IS）」と「制約（SHOULD）」の2つの概念的レイヤーに分離して1つのDBに格納:

■ ISレイヤー (構造グラフ: What it IS)
  - Function中心モデル: Actor, Requirement, Data, Hardware が Function とリンク
  - 目的: システムの「事実」の構造を記述し、ヌケモレ（孤立）を検出

■ SHOULDレイヤー (制約グラフ: What it SHOULD be)
  - Constraint中心モデル: Constraint がすべてのノードとリンク可能
  - 目的: システムが「守るべき」ルールを記述し、矛盾を検出

【ノード】
- Actor, Function, Data, Hardware, Requirement (ISレイヤー)
- Constraint (SHOULDレイヤー)

【関係性の原則】
1. Actor/Requirement は Function とのみ関係を持つ
2. Data/Hardware は Function とのみ関係を持つ
3. Function は Function と関係を持つ（依存関係）
4. Constraint はすべてのノードと関係を持つ

【検出可能な問題】
1. ヌケモレ: 孤立したノード（Functionと関係のないActor/Requirement/Data/Hardware）
2. 矛盾: Constraint同士の競合、IS vs SHOULD の競合
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


# ========== ノード（エンティティ）定義 ==========

class EntityType(BaseModel):
    """エンティティタイプの定義"""
    name: str = Field(..., description="エンティティタイプ名")
    description: str = Field(..., description="説明")
    required_properties: List[str] = Field(..., description="必須プロパティ")
    optional_properties: List[str] = Field(default_factory=list, description="オプショナルプロパティ")
    extraction_patterns: List[str] = Field(..., description="抽出パターン（日本語で記述）")


class RelationType(BaseModel):
    """リレーションタイプの定義"""
    name: str = Field(..., description="リレーションタイプ名")
    description: str = Field(..., description="説明")
    source_types: List[str] = Field(..., description="ソースエンティティタイプ")
    target_types: List[str] = Field(..., description="ターゲットエンティティタイプ")
    properties: List[str] = Field(default_factory=list, description="プロパティ")
    detection_patterns: List[str] = Field(..., description="検出パターン（日本語で記述）")


# ========== 要件定義用スキーマ ==========

ENTITY_TYPES = [
    EntityType(
        name="Actor",
        description="システムを利用する人、役割（ロール）、または外部システム",
        required_properties=["name"],
        optional_properties=["role", "description"],
        extraction_patterns=[
            "〜ユーザー",
            "〜管理者",
            "〜担当者",
            "〜システム",
            "対象ユーザー",
            "アクター",
            "利用者",
        ]
    ),
    EntityType(
        name="Function",
        description="システムが提供する具体的な機能やユースケース",
        required_properties=["name"],
        optional_properties=["description", "inputs", "outputs"],
        extraction_patterns=[
            "〜機能",
            "〜処理",
            "〜操作",
            "ユーザーは〜できる",
            "システムは〜する",
            "ユースケース",
        ]
    ),
    EntityType(
        name="Data",
        description="システムが扱う情報、DBテーブル、主要なデータエンティティ",
        required_properties=["name"],
        optional_properties=["attributes", "data_type", "sensitivity"],
        extraction_patterns=[
            "〜情報",
            "〜データ",
            "〜マスタ",
            "〜テーブル",
            "データベース",
            "エンティティ",
        ]
    ),
    EntityType(
        name="Requirement",
        description="やるべきこと - システムが実現すべき機能や振る舞いそのもの",
        required_properties=["name"],
        optional_properties=["description", "priority"],
        extraction_patterns=[
            "〜要件",
            "〜機能",
            "〜を提供する",
            "〜を行う",
            "〜できること",
            "実現すべき",
        ]
    ),
    EntityType(
        name="Constraint",
        description="守るべきこと - FunctionやHardwareに課せられる制約条件（非機能要件）",
        required_properties=["name", "category"],
        optional_properties=["description", "value", "priority"],
        extraction_patterns=[
            "〜しなければならない",
            "〜すること",
            "制約",
            "条件",
            "仕様",
            "以内",
            "以上",
            "準拠",
        ]
    ),
    EntityType(
        name="Hardware",
        description="物理的なデバイス、サーバー、インフラストラクチャ、IoTデバイス",
        required_properties=["name"],
        optional_properties=["description", "device_type", "kind"],
        extraction_patterns=[
            "〜サーバー",
            "〜デバイス",
            "〜リーダー",
            "PC",
            "スマートフォン",
            "ハードウェア",
            "インフラ",
        ]
    ),
]

RELATION_TYPES = [
    # ISレイヤー: Actor <-> Function
    RelationType(
        name="USES",
        description="アクターが機能を利用する (ISレイヤー)",
        source_types=["Actor"],
        target_types=["Function"],
        properties=[],
        detection_patterns=[
            "は〜できる",
            "が使用",
            "が利用",
            "でアクセス",
        ]
    ),
    RelationType(
        name="AUTHORIZES",
        description="アクターが機能に対する権限を持つ (ISレイヤー)",
        source_types=["Actor"],
        target_types=["Function"],
        properties=["permission"],  # "Allow", "Deny"
        detection_patterns=[
            "が可能",
            "ができない",
            "を許可",
            "を禁止",
            "の権限",
        ]
    ),

    # ISレイヤー: Function <-> Requirement
    RelationType(
        name="SATISFIES",
        description="機能が要件を満たす (ISレイヤー)",
        source_types=["Function"],
        target_types=["Requirement"],
        properties=[],
        detection_patterns=[
            "を満たす",
            "を実現する",
            "に対応する",
            "の要件",
        ]
    ),

    # ISレイヤー: Function <-> Data
    RelationType(
        name="MANIPULATES",
        description="機能がデータを操作する (ISレイヤー)",
        source_types=["Function"],
        target_types=["Data"],
        properties=["action"],  # "Read", "Write", "Delete"
        detection_patterns=[
            "を参照",
            "を読み込む",
            "を更新",
            "を作成",
            "を削除",
            "に保存",
            "から取得",
        ]
    ),

    # ISレイヤー: Function <-> Hardware
    RelationType(
        name="CONTROLS",
        description="機能がハードウェアを制御する (ISレイヤー)",
        source_types=["Function"],
        target_types=["Hardware"],
        properties=["control_type"],  # "Input", "Output", "InputOutput"
        detection_patterns=[
            "を制御",
            "を操作",
            "から読み取る",
            "に出力",
            "を駆動",
            "からセンシング",
        ]
    ),

    # ISレイヤー: Function <-> Function
    RelationType(
        name="DEPENDS_ON",
        description="機能が別の機能に依存する (ISレイヤー)",
        source_types=["Function"],
        target_types=["Function"],
        properties=[],
        detection_patterns=[
            "が前提",
            "に依存",
            "の後に",
            "が必要",
            "を前提とする",
        ]
    ),

    # SHOULDレイヤー: Constraint <-> Any
    RelationType(
        name="APPLIES_TO",
        description="制約がノードに適用される (SHOULDレイヤー)",
        source_types=["Constraint"],
        target_types=["Function", "Data", "Hardware", "Actor", "Requirement"],
        properties=["constraint_type"],  # オプション: "mandatory", "optional"
        detection_patterns=[
            "に適用",
            "に従う",
            "の制約",
            "を守る",
            "準拠",
            "しなければならない",
        ]
    ),
]


# ========== Requirement（要件）のサブタイプ ==========

class RequirementTypeEnum:
    """要件のタイプ（type プロパティの値）"""
    FUNCTIONAL = "Functional"              # 機能要件
    BUSINESS_RULE = "BusinessRule"         # ビジネスルール


# ========== Constraint（制約）のカテゴリー ==========

class ConstraintCategoryEnum:
    """制約のカテゴリー（category プロパティの値）"""
    TIMING = "Timing"                      # タイミング制約（周期、応答時間など）
    PERFORMANCE = "Performance"            # 性能制約（スループット、同時接続数など）
    SAFETY = "Safety"                      # 安全性制約（ASIL、ISO26262など）
    SECURITY = "Security"                  # セキュリティ制約（暗号化、認証など）
    AVAILABILITY = "Availability"          # 可用性制約（稼働率など）
    RELIABILITY = "Reliability"            # 信頼性制約（MTBF、故障率など）
    MAINTAINABILITY = "Maintainability"    # 保守性制約（修正時間など）
    USABILITY = "Usability"                # ユーザビリティ制約（操作時間など）
    CAPACITY = "Capacity"                  # 容量制約（メモリ、ストレージなど）
    COMPATIBILITY = "Compatibility"        # 互換性制約（プロトコル、規格など）
    ENVIRONMENTAL = "Environmental"        # 環境制約（温度、湿度など）
    REGULATORY = "Regulatory"              # 規制制約（法規制、標準規格など）


# ========== MANIPULATES の action プロパティ ==========

class ManipulateActionEnum:
    """データ操作の種類"""
    READ = "Read"
    WRITE = "Write"
    DELETE = "Delete"
    READ_WRITE = "ReadWrite"


# ========== CONTROLS の control_type プロパティ ==========

class ControlTypeEnum:
    """ハードウェア制御の種類"""
    INPUT = "Input"           # センサーなど入力系
    OUTPUT = "Output"         # アクチュエーターなど出力系
    INPUT_OUTPUT = "InputOutput"  # 双方向制御


# ========== AUTHORIZES の permission プロパティ ==========

class PermissionEnum:
    """権限の種類"""
    ALLOW = "Allow"
    DENY = "Deny"


# ========== プロンプトテンプレート用の説明文生成 ==========

def get_entity_types_description() -> str:
    """エンティティタイプの説明をプロンプト用に整形"""
    lines = []
    for et in ENTITY_TYPES:
        lines.append(f"### {et.name}")
        lines.append(f"- **説明**: {et.description}")
        lines.append(f"- **必須プロパティ**: {', '.join(et.required_properties)}")
        if et.optional_properties:
            lines.append(f"- **オプショナルプロパティ**: {', '.join(et.optional_properties)}")
        lines.append(f"- **抽出パターン**: {', '.join(et.extraction_patterns[:5])}")
        lines.append("")
    return "\n".join(lines)


def get_relation_types_description() -> str:
    """リレーションタイプの説明をプロンプト用に整形"""
    lines = []
    for rt in RELATION_TYPES:
        lines.append(f"### {rt.name}")
        lines.append(f"- **説明**: {rt.description}")
        lines.append(f"- **方向**: ({' | '.join(rt.source_types)}) → ({' | '.join(rt.target_types)})")
        if rt.properties:
            lines.append(f"- **プロパティ**: {', '.join(rt.properties)}")
        lines.append(f"- **検出パターン**: {', '.join(rt.detection_patterns[:5])}")
        lines.append("")
    return "\n".join(lines)


# ========== 検出クエリのテンプレート ==========

DETECTION_QUERIES = {
    # ========== ヌケモレ検出クエリ（ISレイヤー） ==========

    # 1. Function と Function の孤立検出
    "isolated_functions": """
        MATCH (f:Function)
        WHERE NOT EXISTS {
            MATCH (f)-[:DEPENDS_ON]->(:Function)
            UNION
            MATCH (f)<-[:DEPENDS_ON]-(:Function)
            UNION
            MATCH (a:Actor)-[:USES]->(f)
        }
        RETURN f.name AS function_name,
               f.description AS description,
               '孤立したFunction' AS issue_type
    """,

    # 2. Actor と Function の関係チェック
    "unused_actors": """
        MATCH (a:Actor)
        WHERE NOT EXISTS {
            MATCH (a)-[:USES]->(:Function)
        }
        RETURN a.name AS actor_name,
               a.description AS description,
               'Functionと関係を持たないActor' AS issue_type
    """,

    # 3. Requirement と Function の関係チェック
    "unsatisfied_requirements": """
        MATCH (r:Requirement)
        WHERE NOT EXISTS {
            MATCH (f:Function)-[:SATISFIES]->(r)
        }
        RETURN r.name AS requirement_name,
               r.description AS description,
               'Functionによって満たされていないRequirement' AS issue_type
    """,

    # 4. Data と Function の関係チェック
    "orphan_data": """
        MATCH (d:Data)
        WHERE NOT EXISTS {
            MATCH (f:Function)-[:MANIPULATES]->(d)
        }
        RETURN d.name AS data_name,
               d.description AS description,
               'Functionと関係を持たないData' AS issue_type
    """,

    # 5. Hardware と Function の関係チェック
    "orphan_hardware": """
        MATCH (h:Hardware)
        WHERE NOT EXISTS {
            MATCH (f:Function)-[:CONTROLS]->(h)
        }
        RETURN h.name AS hardware_name,
               h.description AS description,
               'Functionと関係を持たないHardware' AS issue_type
    """,

    # 6. Constraint の孤立検出
    "isolated_constraints": """
        MATCH (c:Constraint)
        WHERE NOT EXISTS {
            MATCH (c)-[:APPLIES_TO]->()
        }
        RETURN c.name AS constraint_name,
               c.category AS category,
               '適用対象のないConstraint' AS issue_type
    """,

    # ========== 矛盾検出クエリ（ISレイヤー + SHOULDレイヤー） ==========

    # 7. 循環依存（ISレイヤー内部）
    "circular_dependencies": """
        MATCH path = (f1:Function)-[:DEPENDS_ON*]->(f1)
        RETURN f1.name AS function_name,
               [n IN nodes(path) | n.name] AS cycle_path,
               'Function間の循環依存' AS issue_type
    """,

    # 8. 権限の競合（ISレイヤー内部）
    "permission_conflicts": """
        MATCH (a:Actor)-[r1:AUTHORIZES {permission: 'Allow'}]->(f:Function),
              (a)-[r2:AUTHORIZES {permission: 'Deny'}]->(f)
        RETURN a.name AS actor_name,
               f.name AS function_name,
               'Allow と Deny の競合' AS issue_type
    """,

    # 9. データアクセスの競合（ISレイヤー内部）
    "data_access_conflicts": """
        MATCH (f1:Function)-[m1:MANIPULATES {action: 'Write'}]->(d:Data),
              (f2:Function)-[m2:MANIPULATES {action: 'Write'}]->(d)
        WHERE f1.name <> f2.name
        AND NOT EXISTS {
            MATCH (f1)-[:DEPENDS_ON]->(f2)
            UNION
            MATCH (f2)-[:DEPENDS_ON]->(f1)
        }
        RETURN d.name AS data_name,
               f1.name AS function1,
               f2.name AS function2,
               '依存関係なしの同時Write' AS issue_type
    """,

    # 10. Constraint同士の競合候補（SHOULDレイヤー内部）- LLM判定用
    "constraint_conflict_candidates": """
        MATCH (c1:Constraint)-[:APPLIES_TO]->(target_node),
              (c2:Constraint)-[:APPLIES_TO]->(target_node)
        WHERE id(c1) < id(c2)
        RETURN c1.name AS constraint1_name,
               c1.description AS constraint1_description,
               c2.name AS constraint2_name,
               c2.description AS constraint2_description,
               target_node.name AS target_name,
               labels(target_node)[0] AS target_type,
               '同一対象への複数Constraint（LLM判定必要）' AS issue_type
    """,

    # 11. セキュリティ制約の漏れ（SHOULDレイヤー）
    "missing_security_constraints": """
        MATCH (d:Data)
        WHERE d.name CONTAINS '個人情報'
           OR d.name CONTAINS '決済情報'
           OR d.sensitivity = 'confidential'
        AND NOT EXISTS {
            MATCH (c:Constraint {category: 'Security'})-[:APPLIES_TO]->(d)
        }
        RETURN d.name AS data_name,
               d.sensitivity AS sensitivity,
               'セキュリティConstraintが未適用' AS issue_type
    """,

    # 12. IS vs SHOULD 矛盾候補 - LLM判定用
    "is_vs_should_conflict_candidates": """
        MATCH path = (a:Actor)-[:USES*1..5]->(f:Function)-[:MANIPULATES]->(d:Data)
        MATCH (c:Constraint {permission: 'Deny'})
        WHERE (c)-[:APPLIES_TO]->(a) AND (c)-[:APPLIES_TO]->(d)
        RETURN [n IN nodes(path) | n.name] AS access_path,
               c.name AS constraint_name,
               c.description AS constraint_description,
               '構造パスと禁止ルールの矛盾可能性（LLM判定必要）' AS issue_type
    """,
}


# ========== スキーマ定義のサマリー ==========

SCHEMA_SUMMARY = f"""
# 要件定義書用 知識グラフスキーマ（IS/SHOULDレイヤーモデル）

## ノード（エンティティ）: {len(ENTITY_TYPES)}種類
{', '.join([et.name for et in ENTITY_TYPES])}

## エッジ（リレーション）: {len(RELATION_TYPES)}種類
{', '.join([rt.name for rt in RELATION_TYPES])}

## スキーマ設計コンセプト

### ISレイヤー（構造グラフ: What it IS）
Function中心モデル。システムの「事実」の構造を記述。

**関係性の原則:**
1. Actor/Requirement は Function とのみ関係を持つ
   - (Actor) -[:USES]-> (Function)
   - (Function) -[:SATISFIES]-> (Requirement)
2. Data/Hardware は Function とのみ関係を持つ
   - (Function) -[:MANIPULATES]-> (Data)
   - (Function) -[:CONTROLS]-> (Hardware)
3. Function は Function と関係を持つ（依存関係）
   - (Function) -[:DEPENDS_ON]-> (Function)

### SHOULDレイヤー（制約グラフ: What it SHOULD be）
Constraint中心モデル。システムが「守るべき」ルールを記述。

**関係性の原則:**
- Constraint はすべてのノードと関係を持つ
  - (Constraint) -[:APPLIES_TO]-> (Function/Data/Hardware/Actor/Requirement)
- カテゴリー: Timing, Safety, Security, Performance, など

## 検出可能な問題

### ヌケモレ（ISレイヤー）
1. 孤立したFunction（他のFunctionやActorと無関係）
2. Functionと関係を持たないActor
3. Functionによって満たされていないRequirement
4. Functionと関係を持たないData
5. Functionと関係を持たないHardware
6. 適用対象のないConstraint

### 矛盾（ISレイヤー + SHOULDレイヤー）
1. ISレイヤー内部:
   - Function間の循環依存
   - 権限の競合（Allow と Deny）
   - 依存関係なしの同時Write
2. SHOULDレイヤー内部:
   - 同一対象への矛盾するConstraint（LLM判定）
3. IS vs SHOULD:
   - 構造パスと禁止ルールの矛盾（LLM判定）
"""
