"""
要件定義書用 知識グラフスキーマ定義

推奨スキーマ:
- 4つのノード: Actor, Function, Data, Requirement
- 5つのエッジ: USES, MANIPULATES, DEPENDS_ON, APPLIES_TO, AUTHORIZES

このスキーマにより以下を検出可能:
1. ヌケモレ: 利用されない機能、セキュリティ要件の漏れ、未定義データ
2. 矛盾: 権限の競合、循環依存、データアクセスの矛盾
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
        description="機能的要件、非機能要件、ビジネスルール、制約条件",
        required_properties=["name", "type"],
        optional_properties=["description", "priority"],
        extraction_patterns=[
            "〜要件",
            "〜しなければならない",
            "〜すること",
            "制約",
            "ルール",
            "条件",
            "仕様",
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
    RelationType(
        name="USES",
        description="アクターが機能を利用する",
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
        name="MANIPULATES",
        description="機能がデータを操作する（Read/Write/Delete）",
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
    RelationType(
        name="DEPENDS_ON",
        description="機能が別の機能に依存する",
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
    RelationType(
        name="APPLIES_TO",
        description="要件が機能またはデータに適用される",
        source_types=["Requirement"],
        target_types=["Function", "Data"],
        properties=[],
        detection_patterns=[
            "に適用",
            "を満たす",
            "に従う",
            "の制約",
        ]
    ),
    RelationType(
        name="AUTHORIZES",
        description="アクターが機能に対する権限を持つ",
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
]


# ========== Requirement（要件）のサブタイプ ==========

class RequirementTypeEnum:
    """要件のタイプ（type プロパティの値）"""
    FUNCTIONAL = "Functional"              # 機能要件
    PERFORMANCE = "Performance"            # 性能要件
    SECURITY = "Security"                  # セキュリティ要件
    AVAILABILITY = "Availability"          # 可用性要件
    MAINTAINABILITY = "Maintainability"    # 保守性要件
    USABILITY = "Usability"                # ユーザビリティ要件
    BUSINESS_RULE = "BusinessRule"         # ビジネスルール
    CONSTRAINT = "Constraint"              # 制約条件


# ========== MANIPULATES の action プロパティ ==========

class ManipulateActionEnum:
    """データ操作の種類"""
    READ = "Read"
    WRITE = "Write"
    DELETE = "Delete"
    READ_WRITE = "ReadWrite"


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
    # ヌケモレ検出クエリ
    "unused_functions": """
        MATCH (f:Function)
        WHERE NOT EXISTS {
            MATCH (a:Actor)-[:USES]->(f)
        }
        RETURN f.name AS function_name, f.description AS description
    """,

    "missing_security_requirements": """
        MATCH (d:Data)
        WHERE d.name CONTAINS '個人情報' OR d.name CONTAINS '決済情報' OR d.sensitivity = 'confidential'
        AND NOT EXISTS {
            MATCH (r:Requirement {type: 'Security'})-[:APPLIES_TO]->(d)
        }
        RETURN d.name AS data_name, d.sensitivity AS sensitivity
    """,

    "orphan_data": """
        MATCH (d:Data)
        WHERE NOT EXISTS {
            MATCH (f:Function)-[:MANIPULATES]->(d)
        }
        RETURN d.name AS data_name
    """,

    # 矛盾検出クエリ
    "circular_dependencies": """
        MATCH path = (f1:Function)-[:DEPENDS_ON*]->(f1)
        RETURN f1.name AS function_name,
               [n IN nodes(path) | n.name] AS cycle_path
    """,

    "permission_conflicts": """
        MATCH (a:Actor)-[r1:AUTHORIZES {permission: 'Allow'}]->(f:Function),
              (a)-[r2:AUTHORIZES {permission: 'Deny'}]->(f)
        RETURN a.name AS actor_name,
               f.name AS function_name,
               'Permission conflict' AS conflict_type
    """,

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
               'Concurrent write without dependency' AS issue
    """,
}


# ========== スキーマ定義のサマリー ==========

SCHEMA_SUMMARY = f"""
# 要件定義書用 知識グラフスキーマ

## ノード（エンティティ）: {len(ENTITY_TYPES)}種類
{', '.join([et.name for et in ENTITY_TYPES])}

## エッジ（リレーション）: {len(RELATION_TYPES)}種類
{', '.join([rt.name for rt in RELATION_TYPES])}

## 検出可能な問題
### ヌケモレ
- 利用されない機能（誰も USES していない Function）
- セキュリティ要件の漏れ（個人情報 Data に APPLIES_TO されていない Security Requirement）
- 孤立データ（どの Function からも MANIPULATES されていない Data）

### 矛盾
- 循環依存（DEPENDS_ON のループ）
- 権限の競合（同一 Actor が同一 Function に Allow と Deny）
- データアクセスの矛盾（依存関係なしに複数 Function が同一 Data を Write）
"""
