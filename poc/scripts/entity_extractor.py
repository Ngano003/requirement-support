"""
エンティティ抽出器（GraphRAG PoC用）

既存のentity_extractor.pyを流用しつつ、スタンドアロンで動作するように調整
Google AI Studio (Gemini) APIにも対応
"""

import json
import logging
from typing import Dict, Any, List, Set

from config import Config

# スキーマ定義を直接インポート（backendディレクトリをパスに追加）
import sys
import os

# pocディレクトリから実行される場合、backendディレクトリを探す
current_dir = os.path.dirname(__file__)
poc_dir = os.path.dirname(current_dir)  # scripts -> poc
project_root = os.path.dirname(poc_dir)  # poc -> requirement-support
backend_dir = os.path.join(project_root, 'backend')

if os.path.exists(backend_dir):
    sys.path.insert(0, backend_dir)
else:
    # backend/scriptsから実行される場合
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.schemas.knowledge_graph_schema import (
    ENTITY_TYPES,
    RELATION_TYPES,
)
from app.prompts.entity_extraction_prompt import (
    ENTITY_EXTRACTION_SYSTEM_PROMPT,
    build_entity_extraction_prompt,
)

logger = logging.getLogger(__name__)


class EntityExtractor:
    """エンティティ抽出器"""

    def __init__(self, config: Config):
        self.config = config
        self.entity_types = ENTITY_TYPES
        self.relation_types = RELATION_TYPES

        # エンティティタイプ名のセット（高速検索用）
        self.valid_entity_types: Set[str] = {et.name for et in self.entity_types}

        # リレーションタイプ名のセット（高速検索用）
        self.valid_relation_types: Set[str] = {rt.name for rt in self.relation_types}

        # リレーションタイプごとの制約マップ
        self.relation_constraints: Dict[str, Any] = {
            rt.name: rt for rt in self.relation_types
        }

        # LLMクライアント初期化
        llm_config = config.get_llm_client_config()
        self.llm_provider = config.llm_provider
        self.model = llm_config["model"]

        # プロバイダーに応じてクライアントを初期化
        if llm_config.get("provider") == "google_ai":
            import google.generativeai as genai
            genai.configure(api_key=llm_config["api_key"])
            self.google_model = genai.GenerativeModel(self.model)
            self.client = None
        else:
            # OpenAI互換API（OpenAI、OpenRouter、vLLM）
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=llm_config["api_key"],
                base_url=llm_config.get("base_url"),
            )
            self.google_model = None

    async def extract(self, requirements_text: str) -> Dict[str, Any]:
        """
        要件定義書からエンティティとリレーションを抽出

        Args:
            requirements_text: 要件定義書のテキスト

        Returns:
            {
                "entities": [...],
                "relations": [...],
                "validation_errors": [...]
            }
        """
        try:
            # プロンプト構築
            prompt = build_entity_extraction_prompt(requirements_text)

            # LLMで抽出
            logger.info("Extracting entities and relations from requirements text...")
            response = await self._call_llm(
                system_prompt=ENTITY_EXTRACTION_SYSTEM_PROMPT,
                user_prompt=prompt,
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

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """LLM APIを呼び出し"""
        try:
            if self.google_model:
                # Google AI Studio (Gemini) API
                combined_prompt = f"{system_prompt}\n\n{user_prompt}"

                # 同期APIを非同期ラッパーで実行
                import asyncio
                response = await asyncio.to_thread(
                    self.google_model.generate_content,
                    combined_prompt,
                    generation_config={
                        "temperature": self.config.extraction_temperature,
                    }
                )

                return response.text
            else:
                # OpenAI互換API
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=self.config.extraction_temperature,
                )

                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM API call failed: {e}", exc_info=True)
            raise

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
                "entities": [...],
                "relations": [...],
                "validation_errors": []
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

        return True, ""
