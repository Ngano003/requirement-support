"""
スキーママッパー（フェーズB: スキーマの標準化）

LLMが抽出した候補を標準スキーマにマッピングする
人間がレビュー・承認するための対話型インターフェースを提供
"""

import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class SchemaMapper:
    """スキーママッピング管理"""

    # 標準スキーマ定義
    STANDARD_LABELS = {
        "Actor": "システムを利用する人、役割、外部システム",
        "Function": "システムが提供する機能やユースケース",
        "Data": "管理されるデータやエンティティ",
        "Requirement": "やるべきこと - システムが実現すべき機能や振る舞い",
        "Constraint": "守るべきこと - 非機能要件、制約条件",
        "Hardware": "ハードウェア、デバイス、インフラストラクチャ",
    }

    STANDARD_RELATIONS = {
        # ISレイヤー
        "USES": "ActorがFunctionを使用する (ISレイヤー)",
        "AUTHORIZES": "ActorがFunctionへのアクセス権限を持つ (ISレイヤー)",
        "SATISFIES": "FunctionがRequirementを満たす (ISレイヤー)",
        "MANIPULATES": "FunctionがDataを操作する（Read/Write/Delete）(ISレイヤー)",
        "CONTROLS": "FunctionがHardwareを制御する (ISレイヤー)",
        "DEPENDS_ON": "FunctionがFunctionに依存する (ISレイヤー)",
        # SHOULDレイヤー
        "APPLIES_TO": "Constraintがすべてのノードに適用される (SHOULDレイヤー)",
    }

    def __init__(self):
        self.mapping = {
            "actor_mapping": [],
            "function_mapping": [],
            "data_mapping": [],
            "requirement_mapping": [],
            "constraint_mapping": [],
            "hardware_mapping": [],
        }

    def create_mapping_from_candidates(
        self, structure_candidates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        候補から標準スキーマへのマッピングを作成

        Args:
            structure_candidates: 構造抽出器が生成した候補

        Returns:
            マッピング定義
        """
        logger.info("Creating schema mapping from candidates...")

        # Actor候補をマッピング
        for candidate in structure_candidates.get("actor_candidates", []):
            self.mapping["actor_mapping"].append(
                {
                    "name": candidate["name"],
                    "description": candidate.get("description", ""),
                    "label": "Actor",  # 標準ラベル
                    "approved": True,  # デフォルトで承認（人間がレビューで変更可能）
                }
            )

        # Function候補をマッピング
        for candidate in structure_candidates.get("function_candidates", []):
            self.mapping["function_mapping"].append(
                {
                    "name": candidate["name"],
                    "description": candidate.get("description", ""),
                    "label": "Function",
                    "approved": True,
                }
            )

        # Data候補をマッピング
        for candidate in structure_candidates.get("data_candidates", []):
            self.mapping["data_mapping"].append(
                {
                    "name": candidate["name"],
                    "description": candidate.get("description", ""),
                    "sensitivity": candidate.get("sensitivity", "low"),
                    "label": "Data",
                    "approved": True,
                }
            )

        # Requirement候補をマッピング（やるべきこと）
        for candidate in structure_candidates.get("requirement_candidates", []):
            candidate_type = candidate.get("type", "Functional")
            # Functional と BusinessRule のみを Requirement として扱う
            if candidate_type in ["Functional", "BusinessRule"]:
                self.mapping["requirement_mapping"].append(
                    {
                        "name": candidate["name"],
                        "description": candidate.get("description", ""),
                        "type": candidate_type,
                        "label": "Requirement",
                        "approved": True,
                    }
                )
            else:
                # その他は Constraint（守るべきこと）として分類
                self.mapping["constraint_mapping"].append(
                    {
                        "name": candidate["name"],
                        "description": candidate.get("description", ""),
                        "category": self._map_type_to_category(candidate_type),
                        "label": "Constraint",
                        "approved": True,
                    }
                )

        # Hardware候補をマッピング
        for candidate in structure_candidates.get("hardware_candidates", []):
            self.mapping["hardware_mapping"].append(
                {
                    "name": candidate["name"],
                    "description": candidate.get("description", ""),
                    "device_type": candidate.get("device_type", "Unknown"),
                    "label": "Hardware",
                    "approved": True,
                }
            )

        logger.info(
            f"Mapping created:\n"
            f"  - Actors: {len(self.mapping['actor_mapping'])}\n"
            f"  - Functions: {len(self.mapping['function_mapping'])}\n"
            f"  - Data: {len(self.mapping['data_mapping'])}\n"
            f"  - Requirements: {len(self.mapping['requirement_mapping'])}\n"
            f"  - Constraints: {len(self.mapping['constraint_mapping'])}\n"
            f"  - Hardware: {len(self.mapping['hardware_mapping'])}"
        )

        return self.mapping

    def _map_type_to_category(self, requirement_type: str) -> str:
        """
        旧Requirementのtypeを新Constraintのcategoryにマッピング

        Args:
            requirement_type: 旧Requirementのtype値

        Returns:
            Constraintのcategory値
        """
        type_to_category_map = {
            "Performance": "Performance",
            "Security": "Security",
            "Availability": "Availability",
            "Maintainability": "Maintainability",
            "Usability": "Usability",
            "Reliability": "Reliability",
            "Capacity": "Capacity",
            "Compatibility": "Compatibility",
            "Timing": "Timing",
            "Safety": "Safety",
            "Environmental": "Environmental",
            "Regulatory": "Regulatory",
            "NonFunctional": "Performance",  # デフォルトマッピング
            "Constraint": "Performance",  # デフォルトマッピング
        }
        return type_to_category_map.get(requirement_type, "Performance")

    def save_mapping(self, output_path: str):
        """
        マッピングをJSONファイルに保存

        Args:
            output_path: 出力先ファイルパス
        """
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.mapping, f, ensure_ascii=False, indent=2)
        logger.info(f"Schema mapping saved to: {output_path}")

    @staticmethod
    def load_mapping(input_path: str) -> Dict[str, Any]:
        """
        マッピングをJSONファイルから読み込み

        Args:
            input_path: 入力ファイルパス

        Returns:
            マッピング定義
        """
        with open(input_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_extraction_instructions(self) -> str:
        """
        エンティティ抽出用の動的プロンプトを生成

        Returns:
            LlamaIndex/LLMに渡す抽出指示
        """
        instructions = []

        instructions.append("# エンティティ抽出指示\n")
        instructions.append("以下のスキーマ定義に従い、要件定義書からエンティティと関係性を抽出してください。\n")

        # Actor抽出指示
        approved_actors = [
            item for item in self.mapping.get("actor_mapping", []) if item.get("approved", True)
        ]
        if approved_actors:
            instructions.append("\n## Actor（アクター）")
            instructions.append("以下のアクターを抽出してください：")
            for actor in approved_actors:
                instructions.append(f"- **{actor['name']}**: {actor.get('description', '')}")

        # Function抽出指示
        approved_functions = [
            item for item in self.mapping.get("function_mapping", []) if item.get("approved", True)
        ]
        if approved_functions:
            instructions.append("\n## Function（機能）")
            instructions.append("以下の機能を抽出してください：")
            for func in approved_functions:
                instructions.append(f"- **{func['name']}**: {func.get('description', '')}")

        # Data抽出指示
        approved_data = [
            item for item in self.mapping.get("data_mapping", []) if item.get("approved", True)
        ]
        if approved_data:
            instructions.append("\n## Data（データ）")
            instructions.append("以下のデータを抽出してください：")
            for data in approved_data:
                instructions.append(
                    f"- **{data['name']}**: {data.get('description', '')} "
                    f"（機密性: {data.get('sensitivity', 'low')}）"
                )

        # Requirement抽出指示（やるべきこと）
        approved_requirements = [
            item for item in self.mapping.get("requirement_mapping", []) if item.get("approved", True)
        ]
        if approved_requirements:
            instructions.append("\n## Requirement（やるべきこと）")
            instructions.append("以下の要件を抽出してください：")
            for req in approved_requirements:
                instructions.append(
                    f"- **{req['name']}**: {req.get('description', '')} "
                    f"（タイプ: {req.get('type', 'Functional')}）"
                )

        # Constraint抽出指示（守るべきこと）
        approved_constraints = [
            item for item in self.mapping.get("constraint_mapping", []) if item.get("approved", True)
        ]
        if approved_constraints:
            instructions.append("\n## Constraint（守るべきこと）")
            instructions.append("以下の制約を抽出してください：")
            for con in approved_constraints:
                instructions.append(
                    f"- **{con['name']}**: {con.get('description', '')} "
                    f"（カテゴリー: {con.get('category', 'Performance')}）"
                )

        # Hardware抽出指示
        approved_hardware = [
            item for item in self.mapping.get("hardware_mapping", []) if item.get("approved", True)
        ]
        if approved_hardware:
            instructions.append("\n## Hardware（ハードウェア）")
            instructions.append("以下のハードウェアを抽出してください：")
            for hw in approved_hardware:
                instructions.append(
                    f"- **{hw['name']}**: {hw.get('description', '')} "
                    f"（種類: {hw.get('device_type', 'Unknown')}）"
                )

        # 関係性抽出指示
        instructions.append("\n## 関係性（Relations）")
        instructions.append("以下の関係性を自動で推論してください：")
        for relation, description in self.STANDARD_RELATIONS.items():
            instructions.append(f"- **{relation}**: {description}")

        instructions.append("\n## 関係性の原則（IS/SHOULDレイヤーモデル）")
        instructions.append("\n### ISレイヤー（構造グラフ）:")
        instructions.append("- Actor/Requirement は Function とのみ関係を持つ")
        instructions.append("  - (Actor) -[:USES]-> (Function)")
        instructions.append("  - (Function) -[:SATISFIES]-> (Requirement)")
        instructions.append("- Data/Hardware は Function とのみ関係を持つ")
        instructions.append("  - (Function) -[:MANIPULATES]-> (Data)")
        instructions.append("  - (Function) -[:CONTROLS]-> (Hardware)")
        instructions.append("- Function は Function と関係を持つ")
        instructions.append("  - (Function) -[:DEPENDS_ON]-> (Function)")
        instructions.append("\n### SHOULDレイヤー（制約グラフ）:")
        instructions.append("- Constraint はすべてのノードと関係を持つ")
        instructions.append("  - (Constraint) -[:APPLIES_TO]-> (Function/Data/Hardware/Actor/Requirement)")

        return "\n".join(instructions)

    def print_mapping_summary(self):
        """マッピングサマリーをコンソールに出力"""
        print("\n" + "=" * 80)
        print("スキーママッピング サマリー")
        print("=" * 80)

        print(f"\n【Actor】 {len(self.mapping.get('actor_mapping', []))}件")
        for item in self.mapping.get("actor_mapping", [])[:5]:  # 最初の5件のみ表示
            status = "✅" if item.get("approved", True) else "❌"
            print(f"  {status} {item['name']}: {item.get('description', '')}")
        if len(self.mapping.get("actor_mapping", [])) > 5:
            print(f"  ... 他 {len(self.mapping.get('actor_mapping', [])) - 5}件")

        print(f"\n【Function】 {len(self.mapping.get('function_mapping', []))}件")
        for item in self.mapping.get("function_mapping", [])[:5]:
            status = "✅" if item.get("approved", True) else "❌"
            print(f"  {status} {item['name']}: {item.get('description', '')}")
        if len(self.mapping.get("function_mapping", [])) > 5:
            print(f"  ... 他 {len(self.mapping.get('function_mapping', [])) - 5}件")

        print(f"\n【Data】 {len(self.mapping.get('data_mapping', []))}件")
        for item in self.mapping.get("data_mapping", [])[:5]:
            status = "✅" if item.get("approved", True) else "❌"
            print(
                f"  {status} {item['name']}: {item.get('description', '')} "
                f"[{item.get('sensitivity', 'low')}]"
            )
        if len(self.mapping.get("data_mapping", [])) > 5:
            print(f"  ... 他 {len(self.mapping.get('data_mapping', [])) - 5}件")

        print(f"\n【Requirement（やるべきこと）】 {len(self.mapping.get('requirement_mapping', []))}件")
        for item in self.mapping.get("requirement_mapping", [])[:5]:
            status = "✅" if item.get("approved", True) else "❌"
            print(
                f"  {status} {item['name']}: {item.get('description', '')} "
                f"[{item.get('type', 'Functional')}]"
            )
        if len(self.mapping.get("requirement_mapping", [])) > 5:
            print(f"  ... 他 {len(self.mapping.get('requirement_mapping', [])) - 5}件")

        print(f"\n【Constraint（守るべきこと）】 {len(self.mapping.get('constraint_mapping', []))}件")
        for item in self.mapping.get("constraint_mapping", [])[:5]:
            status = "✅" if item.get("approved", True) else "❌"
            print(
                f"  {status} {item['name']}: {item.get('description', '')} "
                f"[{item.get('category', 'Performance')}]"
            )
        if len(self.mapping.get("constraint_mapping", [])) > 5:
            print(f"  ... 他 {len(self.mapping.get('constraint_mapping', [])) - 5}件")

        print(f"\n【Hardware】 {len(self.mapping.get('hardware_mapping', []))}件")
        for item in self.mapping.get("hardware_mapping", [])[:5]:
            status = "✅" if item.get("approved", True) else "❌"
            print(
                f"  {status} {item['name']}: {item.get('description', '')} "
                f"[{item.get('device_type', 'Unknown')}]"
            )
        if len(self.mapping.get("hardware_mapping", [])) > 5:
            print(f"  ... 他 {len(self.mapping.get('hardware_mapping', [])) - 5}件")

        print("\n" + "=" * 80)
