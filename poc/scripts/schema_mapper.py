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
        "Requirement": "制約、ルール、非機能要件、セキュリティ要件",
    }

    STANDARD_RELATIONS = {
        "USES": "ActorがFunctionを使用する",
        "MANIPULATES": "FunctionがDataを操作する（Read/Write/Delete）",
        "APPLIES_TO": "RequirementがData/Functionに適用される",
        "DEPENDS_ON": "FunctionがFunctionに依存する",
        "AUTHORIZES": "ActorがFunctionへのアクセス権限を持つ（Allow/Deny）",
        "STORED_IN": "DataがStorage（DB、ファイルシステム）に保存される",
    }

    def __init__(self):
        self.mapping = {
            "actor_mapping": [],
            "function_mapping": [],
            "data_mapping": [],
            "requirement_mapping": [],
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

        # Requirement候補をマッピング
        for candidate in structure_candidates.get("requirement_candidates", []):
            self.mapping["requirement_mapping"].append(
                {
                    "name": candidate["name"],
                    "description": candidate.get("description", ""),
                    "type": candidate.get("type", "Functional"),
                    "label": "Requirement",
                    "approved": True,
                }
            )

        logger.info(
            f"Mapping created:\n"
            f"  - Actors: {len(self.mapping['actor_mapping'])}\n"
            f"  - Functions: {len(self.mapping['function_mapping'])}\n"
            f"  - Data: {len(self.mapping['data_mapping'])}\n"
            f"  - Requirements: {len(self.mapping['requirement_mapping'])}"
        )

        return self.mapping

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

        # Requirement抽出指示
        approved_requirements = [
            item for item in self.mapping.get("requirement_mapping", []) if item.get("approved", True)
        ]
        if approved_requirements:
            instructions.append("\n## Requirement（要件）")
            instructions.append("以下の要件を抽出してください：")
            for req in approved_requirements:
                instructions.append(
                    f"- **{req['name']}**: {req.get('description', '')} "
                    f"（タイプ: {req.get('type', 'Functional')}）"
                )

        # 関係性抽出指示
        instructions.append("\n## 関係性（Relations）")
        instructions.append("以下の関係性を自動で推論してください：")
        for relation, description in self.STANDARD_RELATIONS.items():
            instructions.append(f"- **{relation}**: {description}")

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

        print(f"\n【Requirement】 {len(self.mapping.get('requirement_mapping', []))}件")
        for item in self.mapping.get("requirement_mapping", [])[:5]:
            status = "✅" if item.get("approved", True) else "❌"
            print(
                f"  {status} {item['name']}: {item.get('description', '')} "
                f"[{item.get('type', 'Functional')}]"
            )
        if len(self.mapping.get("requirement_mapping", [])) > 5:
            print(f"  ... 他 {len(self.mapping.get('requirement_mapping', [])) - 5}件")

        print("\n" + "=" * 80)
