"""
要件定義書からエンティティとリレーションシップを抽出するサービス

knowledge_graph_schema.py で定義されたスキーマに基づいて、
LLMを使ってエンティティとリレーションを抽出・検証します。
"""

import json
import logging
from typing import Dict, Any, List, Set
from pydantic import ValidationError

from app.schemas.knowledge_graph_schema import (
    ENTITY_TYPES,
    RELATION_TYPES,
    EntityType,
    RelationType,
)
from app.prompts.entity_extraction_prompt import (
    ENTITY_EXTRACTION_SYSTEM_PROMPT,
    build_entity_extraction_prompt,
)
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class EntityExtractor:
    """エンティティ抽出器"""

    def __init__(self):
        self.entity_types = ENTITY_TYPES
        self.relation_types = RELATION_TYPES

        # エンティティタイプ名のセット（高速検索用）
        self.valid_entity_types: Set[str] = {et.name for et in self.entity_types}

        # リレーションタイプ名のセット（高速検索用）
        self.valid_relation_types: Set[str] = {rt.name for rt in self.relation_types}

        # リレーションタイプごとの制約マップ
        self.relation_constraints: Dict[str, RelationType] = {
            rt.name: rt for rt in self.relation_types
        }

    async def extract(self, requirements_text: str) -> Dict[str, Any]:
        """
        要件定義書からエンティティとリレーションを抽出

        Args:
            requirements_text: 要件定義書のテキスト

        Returns:
            {
                "entities": [...],
                "relations": [...],
                "validation_errors": [...]  # バリデーションで除外されたエラーログ
            }
        """
        try:
            # プロンプト構築
            prompt = build_entity_extraction_prompt(requirements_text)

            # LLMで抽出
            logger.info("Extracting entities and relations from requirements text...")
            response = await llm_service.generate_with_system_prompt(
                system_prompt=ENTITY_EXTRACTION_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2,  # 一貫性のため低め
            )

            # JSONパース
            data = self._parse_json(response)

            # バリデーション
            validated = self._validate_and_clean(data)

            logger.info(
                f"Extracted {len(validated['entities'])} entities and "
                f"{len(validated['relations'])} relations"
            )

            return validated

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}", exc_info=True)
            return {
                "entities": [],
                "relations": [],
                "validation_errors": [str(e)],
            }

    def _parse_json(self, json_str: str) -> dict:
        """JSON文字列をパース"""
        json_str = json_str.strip()

        # コードブロックを除去
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        elif json_str.startswith("```"):
            json_str = json_str[3:]

        if json_str.endswith("```"):
            json_str = json_str[:-3]

        json_str = json_str.strip()

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.debug(f"JSON string: {json_str[:500]}...")
            raise

    def _validate_and_clean(self, data: dict) -> dict:
        """
        エンティティとリレーションをバリデーションしてクリーニング

        Returns:
            {
                "entities": [...],      # バリデーション済みエンティティ
                "relations": [...],     # バリデーション済みリレーション
                "validation_errors": [] # エラーログ
            }
        """
        validation_errors = []

        # エンティティのバリデーション
        validated_entities = []
        for entity in data.get("entities", []):
            is_valid, error = self._validate_entity(entity)
            if is_valid:
                validated_entities.append(entity)
            else:
                validation_errors.append(f"Invalid entity: {error} - {entity}")

        # エンティティIDのセット（リレーション検証用）
        entity_ids = {e["id"] for e in validated_entities}

        # リレーションのバリデーション
        validated_relations = []
        for relation in data.get("relations", []):
            is_valid, error = self._validate_relation(relation, entity_ids)
            if is_valid:
                validated_relations.append(relation)
            else:
                validation_errors.append(f"Invalid relation: {error} - {relation}")

        return {
            "entities": validated_entities,
            "relations": validated_relations,
            "validation_errors": validation_errors,
        }

    def _validate_entity(self, entity: dict) -> tuple[bool, str]:
        """
        エンティティが有効かチェック

        Returns:
            (is_valid, error_message)
        """
        # 必須フィールドチェック
        if not all(k in entity for k in ["type", "id", "properties"]):
            return False, "Missing required fields (type, id, properties)"

        # エンティティタイプチェック
        entity_type = entity["type"]
        if entity_type not in self.valid_entity_types:
            return False, f"Invalid entity type: {entity_type}"

        # エンティティタイプ定義を取得
        entity_type_def = next(
            (et for et in self.entity_types if et.name == entity_type),
            None
        )

        if not entity_type_def:
            return False, f"Entity type definition not found: {entity_type}"

        # 必須プロパティチェック
        properties = entity["properties"]
        for required_prop in entity_type_def.required_properties:
            if required_prop not in properties:
                return False, f"Missing required property: {required_prop}"

        return True, ""

    def _validate_relation(
        self, relation: dict, valid_entity_ids: Set[str]
    ) -> tuple[bool, str]:
        """
        リレーションが有効かチェック

        Returns:
            (is_valid, error_message)
        """
        # 必須フィールドチェック
        if not all(k in relation for k in ["type", "source_id", "target_id"]):
            return False, "Missing required fields (type, source_id, target_id)"

        # リレーションタイプチェック
        relation_type = relation["type"]
        if relation_type not in self.valid_relation_types:
            return False, f"Invalid relation type: {relation_type}"

        # エンティティ存在チェック
        source_id = relation["source_id"]
        target_id = relation["target_id"]

        if source_id not in valid_entity_ids:
            return False, f"Source entity not found: {source_id}"

        if target_id not in valid_entity_ids:
            return False, f"Target entity not found: {target_id}"

        # リレーションタイプ制約チェック（オプショナル）
        # 例: USES は Actor -> Function のみ許可
        relation_def = self.relation_constraints.get(relation_type)
        if relation_def:
            # TODO: source/target のエンティティタイプをチェック
            # 現在は entity_ids しか持っていないため、スキップ
            pass

        return True, ""

    def get_entity_by_id(
        self, entities: List[dict], entity_id: str
    ) -> dict | None:
        """IDでエンティティを検索"""
        return next((e for e in entities if e["id"] == entity_id), None)

    def get_entities_by_type(
        self, entities: List[dict], entity_type: str
    ) -> List[dict]:
        """タイプでエンティティをフィルタ"""
        return [e for e in entities if e["type"] == entity_type]

    def get_relations_by_type(
        self, relations: List[dict], relation_type: str
    ) -> List[dict]:
        """タイプでリレーションをフィルタ"""
        return [r for r in relations if r["type"] == relation_type]

    def get_outgoing_relations(
        self, relations: List[dict], source_id: str
    ) -> List[dict]:
        """特定エンティティからの出力エッジを取得"""
        return [r for r in relations if r["source_id"] == source_id]

    def get_incoming_relations(
        self, relations: List[dict], target_id: str
    ) -> List[dict]:
        """特定エンティティへの入力エッジを取得"""
        return [r for r in relations if r["target_id"] == target_id]


# シングルトンインスタンス
entity_extractor = EntityExtractor()
