"""
エンティティ抽出器（GraphRAG PoC用）

（変更点）
- `extract`メソッドが全文を受け取った際に、内部で自動的にチャンキング、
  チャンクごとの抽出、結果の集約を行うように修正。
- チャンキングと集約ロジックをクラス内部に（プライベートメソッドとして）移植。
- Few-Shotプロンプトは維持。
"""

import json
import logging
import asyncio
import time
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

    def __init__(self, config: Config, schema_mapping: Dict[str, Any] = None):
        self.config = config
        self.entity_types = ENTITY_TYPES
        self.relation_types = RELATION_TYPES
        self.schema_mapping = schema_mapping  # スキーママッピング（オプション）

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

    def _split_markdown_by_section(self, text: str) -> List[str]:
        """
        MarkdownテキストをH2 (##) ヘッダーでセクション分割する。
        H1やヘッダーのない部分も最初のチャンクとして保持する。
        """
        if not text:
            return []
        
        # H2ヘッダー (##) で分割。ヘッダー自体もチャンクに含める
        sections = text.split("\n## ")
        
        processed_sections = []
        if sections:
            # 最初のセクション（H2より前、またはH2がない場合）
            if not text.startswith("## ") and sections[0]:
                processed_sections.append(sections[0])
            elif text.startswith("## ") and sections[0]:
                 processed_sections.append(f"## {sections[0]}") # 最初のH2を復元

            # 2番目以降のセクションに "## " を戻す
            if len(sections) > 1:
                processed_sections.extend([f"## {s}" for s in sections[1:] if s])
        
        if not processed_sections and text:
             processed_sections = [text] # 分割できなかった場合は全文を1チャンクとする
            
        logger.info(f"Document split into {len(processed_sections)} chunks.")
        return processed_sections

    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        チャンクごとの抽出結果を集約し、エンティティの重複を排除する。
        """
        aggregated_entities: Dict[str, Dict[str, Any]] = {}
        aggregated_relations: List[Dict[str, Any]] = []
        all_validation_errors: List[str] = []
        
        entity_ids: Set[str] = set()
        relation_tuples: Set[tuple] = set()

        for result in results:
            all_validation_errors.extend(result.get("validation_errors", []))
            
            # エンティティの重複排除 (idベース)
            for entity in result.get("entities", []):
                entity_id = entity.get("id")
                if entity_id and entity_id not in aggregated_entities:
                    aggregated_entities[entity_id] = entity
                    entity_ids.add(entity_id)
            
            # リレーションの追加 (エンティティIDの存在確認)
            for rel in result.get("relations", []):
                src_id = rel.get("source_id")
                tgt_id = rel.get("target_id")
                rel_type = rel.get("type")
                
                # ソースとターゲットが両方有効なエンティティリストにあるか確認
                if src_id in entity_ids and tgt_id in entity_ids:
                    # 重複リレーションを防止
                    rel_tuple = (src_id, tgt_id, rel_type)
                    if rel_tuple not in relation_tuples:
                        aggregated_relations.append(rel)
                        relation_tuples.add(rel_tuple)

        return {
            "entities": list(aggregated_entities.values()),
            "relations": aggregated_relations,
            "validation_errors": all_validation_errors
        }

    async def extract(self, requirements_text: str) -> Dict[str, Any]:
        """
        要件定義書（全文）からエンティティとリレーションを抽出
        （内部でチャンキングと集約を実行）

        Args:
            requirements_text: 要件定義書のテキスト（全文）

        Returns:
            集約されたグラフデータとバリデーションエラー
        """
        logger.info("Starting extraction process (with internal chunking)...")
        start_time = time.time()
        
        # --- 1. チャンキングの実行 ---
        chunks = self._split_markdown_by_section(requirements_text)
        if not chunks:
            logger.warning("No text chunks found to process.")
            return {
                "entities": [],
                "relations": [],
                "validation_errors": ["Input text was empty."]
            }

        # --- 2. チャンクごとに抽出を非同期実行 ---
        tasks = []
        for i, chunk in enumerate(chunks):
            logger.debug(f"Creating task for chunk {i+1}/{len(chunks)}...")
            # チャンク処理用のプライベートメソッドを呼び出す
            tasks.append(self._extract_chunk(chunk)) 
            
        chunk_results = await asyncio.gather(*tasks)
        
        logger.info(f"All {len(chunks)} chunks processed.")

        # --- 3. 結果の集約と重複排除 ---
        final_graph = self._aggregate_results(chunk_results)
        end_time = time.time()

        logger.info(f"Extraction completed in {end_time - start_time:.2f}s")
        logger.info(f"Total Unique Entities: {len(final_graph['entities'])}")
        logger.info(f"Total Unique Relations: {len(final_graph['relations'])}")
        logger.info(f"Total Validation Errors: {len(final_graph['validation_errors'])}")

        if final_graph["validation_errors"]:
             logger.warning("Validation errors occurred:")
             for i, error in enumerate(final_graph["validation_errors"]):
                logger.warning(f"  Error {i+1}: {error}")

        return final_graph

    async def _extract_chunk(self, chunk_text: str) -> Dict[str, Any]:
        """
        単一のテキストチャンクからエンティティとリレーションを抽出
        （元のextractメソッドのロジックを移植）
        """
        try:
            # プロンプト構築（スキーママッピングがあれば使用）
            if self.schema_mapping:
                # logger.info("Using schema mapping for guided extraction...")
                prompt = self._build_guided_extraction_prompt(chunk_text)
                system_prompt = "あなたは要件定義書のエンティティ抽出の専門家です。与えられたスキーマ定義に従って、正確にエンティティと関係性を抽出してください。"
            else:
                prompt = build_entity_extraction_prompt(chunk_text)
                system_prompt = ENTITY_EXTRACTION_SYSTEM_PROMPT

            # LLMで抽出
            # logger.info("Extracting entities and relations from requirements text...")
            response = await self._call_llm(
                system_prompt=system_prompt,
                user_prompt=prompt,
                temperature=0.0  # 安定性を確保するために0.0固定
            )

            # JSONパース
            data = self._parse_json(response)

            # バリデーション
            validated = self._validate_and_clean(data)

            # チャンクごとのログはデバッグレベルに（多すぎるため）
            logger.debug(
                f"Chunk extracted {len(validated['entities'])} entities, "
                f"{len(validated['relations'])} relations, "
                f"{len(validated['validation_errors'])} errors"
            )

            return validated

        except Exception as e:
            logger.error(f"Entity extraction failed for chunk: {e}", exc_info=True)
            # チャンクレベルのエラーは、集約フェーズで処理するためにリストで返す
            return {
                "entities": [],
                "relations": [],
                "validation_errors": [f"Chunk processing error: {e}"],
            }

    async def _call_llm(self, system_prompt: str, user_prompt: str, temperature=None) -> str:
        """LLM APIを呼び出し"""
        try:
            if temperature is None:
                # configのtemperatureをデフォルトとして使用
                temperature = self.config.extraction_temperature
            
            # 抽出タスクでは常に0.0を強制する (安定性のため)
            llm_temperature = 0.0

            if self.google_model:
                # Google AI Studio (Gemini) API
                combined_prompt = f"{system_prompt}\n\n{user_prompt}"

                # 同期APIを非同期ラッパーで実行
                import asyncio
                response = await asyncio.to_thread(
                    self.google_model.generate_content,
                    combined_prompt,
                    generation_config={
                        "temperature": llm_temperature,
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
                    temperature=llm_temperature,
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
            # パースエラー時は空のデータを返し、エラーは集約フェーズで報告する
            raise ValueError(f"JSON Parse Error: {e}")

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

    def _build_guided_extraction_prompt(self, requirements_text: str) -> str:
        """
        スキーママッピングを使ったガイド付き抽出プロンプトを生成

        Args:
            requirements_text: 要件定義書のテキスト（チャンク）

        Returns:
            ガイド付きプロンプト
        """
        prompt_parts = []

        prompt_parts.append("以下の要件定義書から、指定されたスキーマ定義に従ってエンティティと関係性を抽出してください。\n")

        # スキーマ定義セクション
        prompt_parts.append("## スキーマ定義\n")

        # Actor
        approved_actors = [
            item
            for item in self.schema_mapping.get("actor_mapping", [])
            if item.get("approved", True)
        ]
        if approved_actors:
            prompt_parts.append("\n### Actor（アクター）\n")
            prompt_parts.append("以下のアクターを抽出してください：\n")
            for actor in approved_actors:
                prompt_parts.append(f"- **{actor['name']}**: {actor.get('description', '')}\n")

        # Function
        approved_functions = [
            item
            for item in self.schema_mapping.get("function_mapping", [])
            if item.get("approved", True)
        ]
        if approved_functions:
            prompt_parts.append("\n### Function（機能）\n")
            prompt_parts.append("以下の機能を抽出してください：\n")
            for func in approved_functions:
                prompt_parts.append(f"- **{func['name']}**: {func.get('description', '')}\n")

        # Data
        approved_data = [
            item
            for item in self.schema_mapping.get("data_mapping", [])
            if item.get("approved", True)
        ]
        if approved_data:
            prompt_parts.append("\n### Data（データ）\n")
            prompt_parts.append("以下のデータを抽出してください：\n")
            for data in approved_data:
                prompt_parts.append(
                    f"- **{data['name']}**: {data.get('description', '')} "
                    f"（sensitivity: {data.get('sensitivity', 'low')}）\n"
                )

        # Requirement（やるべきこと）
        approved_requirements = [
            item
            for item in self.schema_mapping.get("requirement_mapping", [])
            if item.get("approved", True)
        ]
        if approved_requirements:
            prompt_parts.append("\n### Requirement（やるべきこと）\n")
            prompt_parts.append("以下の要件を抽出してください：\n")
            for req in approved_requirements:
                prompt_parts.append(
                    f"- **{req['name']}**: {req.get('description', '')} "
                    f"（type: {req.get('type', 'Functional')}）\n"
                )

        # Constraint（守るべきこと）
        approved_constraints = [
            item
            for item in self.schema_mapping.get("constraint_mapping", [])
            if item.get("approved", True)
        ]
        if approved_constraints:
            prompt_parts.append("\n### Constraint（守るべきこと）\n")
            prompt_parts.append("以下の制約を抽出してください：\n")
            for con in approved_constraints:
                prompt_parts.append(
                    f"- **{con['name']}**: {con.get('description', '')} "
                    f"（category: {con.get('category', 'Performance')}）\n"
                )

        # Hardware
        approved_hardware = [
            item
            for item in self.schema_mapping.get("hardware_mapping", [])
            if item.get("approved", True)
        ]
        if approved_hardware:
            prompt_parts.append("\n### Hardware（ハードウェア）\n")
            prompt_parts.append("以下のハードウェアを抽出してください：\n")
            for hw in approved_hardware:
                prompt_parts.append(
                    f"- **{hw['name']}**: {hw.get('description', '')} "
                    f"（deivice_type: {hw.get('device_type', 'Unknown')}）\n"
                )

        # 関係性
        prompt_parts.append("\n### 関係性（Relations）\n")
        prompt_parts.append("以下の関係性を推論してください：\n\n")
        prompt_parts.append("**ISレイヤー（構造グラフ）:**\n")
        prompt_parts.append("- **USES**: ActorがFunctionを使用する\n")
        prompt_parts.append("- **AUTHORIZES**: ActorがFunctionへのアクセス権限を持つ（permission: Allow/Deny）\n")
        prompt_parts.append("- **SATISFIES**: FunctionがRequirementを満たす\n")
        prompt_parts.append("- **MANIPULATES**: FunctionがDataを操作する（action: Read/Write/Delete）\n")
        prompt_parts.append("- **CONTROLS**: FunctionがHardwareを制御する（control_type: Input/Output/InputOutput）\n")
        prompt_parts.append("- **DEPENDS_ON**: FunctionがFunctionに依存する\n\n")
        prompt_parts.append("**SHOULDレイヤー（制約グラフ）:**\n")
        prompt_parts.append("- **APPLIES_TO**: Constraintがすべてのノード（Function/Data/Hardware/Actor/Requirement）に適用される\n\n")
        prompt_parts.append("**重要:** Actor/RequirementはFunctionとのみ、Data/HardwareはFunctionとのみ関係を持ちます。\n")

        # 出力形式
        prompt_parts.append("\n## 出力形式\n")
        prompt_parts.append("以下のJSON形式で出力してください。JSONのみを出力し、他の説明は含めないでください。\n\n")
        prompt_parts.append('```json\n')
        prompt_parts.append('{\n')
        prompt_parts.append('  "entities": [\n')
        prompt_parts.append('    {\n')
        prompt_parts.append('      "id": "（例: ACTOR-001 または 管理者）",\n')
        prompt_parts.append('      "type": "Actor",\n')
        prompt_parts.append('      "properties": {"name": "管理者", "description": "..."}\n')
        prompt_parts.append('    }\n')
        prompt_parts.append('  ],\n')
        prompt_parts.append('  "relations": [\n')
        prompt_parts.append('    {\n')
        prompt_parts.append('      "type": "USES",\n')
        prompt_parts.append('      "source_id": "（例: ACTOR-001 または 管理者）",\n')
        prompt_parts.append('      "target_id": "（例: FUNC-001 または 暗証番号解錠）",\n')
        prompt_parts.append('      "properties": {}\n')
        prompt_parts.append('    }\n')
        prompt_parts.append('  ]\n')
        prompt_parts.append('}\n')
        prompt_parts.append('```\n\n')

        # --- 対策B: Few-Shot（お手本）の追加 ---
        # 具体的で、スキーマ定義と一致する「お手本」をここに追加します。
        # これにより、LLMはJSONの構造と関係性の推論方法を正確に学習します。
        prompt_parts.append("## お手本 (Few-Shot Example)\n")
        prompt_parts.append("入力テキスト:\n")
        # 修正：お手本の入力テキストに「5. 非機能要件」セクションを追加
        prompt_parts.append("「## 4. 機能要件\n- **4.1 暗証番号解錠機能 (FUNC-001)**\n  - ユーザーがキーパッドで入力した暗証番号が、認証キーDBと一致するか照合する。\n  - 照合に成功した場合、ドアロックモーターを作動させ解錠する。\n\n" \
                            "## 5. 非機能要件\n- **5.1 性能 (CONST-P-001)**\n  - ユーザーによる解錠操作（暗証番号入力後）から、モーター作動完了までの応答時間は3秒以内であること。\n」\n\n")
        
        prompt_parts.append("期待するJSON出力:\n")
        prompt_parts.append('```json\n')
        prompt_parts.append('{\n')
        prompt_parts.append(' "entities": [\n')
        
        # ▼▼▼ 修正 ▼▼▼
        # 「id」に (FUNC-001) というコードを使用し、
        # 「name」に説明的な名前を入れるよう、LLMに学習させる。
        prompt_parts.append('    {"id": "FUNC-001", "type": "Function", "properties": {"name": "暗証番号解錠機能", "description": "ユーザーがキーパッドで入力した暗証番号が、認証キーDBと一致するか照合する。照合に成功した場合、ドアロックモーターを作動させ解錠する。"}},\n')
        # ▲▲▲ 修正 ▲▲▲
        
        prompt_parts.append('    {"id": "キーパッド", "type": "Hardware", "properties": {"name": "キーパッド", "description": "暗証番号入力のための物理的な入力装置"}},\n')
        prompt_parts.append('    {"id": "認証キーDB", "type": "Data", "properties": {"name": "認証キーDB", "description": "暗証番号やBLEキーなどの認証情報を格納するデータベース"}},\n')
        prompt_parts.append('    {"id": "ドアロックモーター", "type": "Hardware", "properties": {"name": "ドアロックモーター", "description": "ドアの施錠・解錠を行う物理的な駆動部"}},\n')
        
        # 修正：Constraintノードのお手本を追加。これが最も重要な修正。
        # "category" プロパティを明示的に含める。
        # 「id」には (CONST-P-001) のコードを使用する。
        prompt_parts.append('    {"id": "CONST-P-001", "type": "Constraint", "properties": {"name": "解錠応答時間", "description": "解錠操作の応答時間は3秒以内とする。", "category": "Performance"}}\n')

        prompt_parts.append('  ],\n')
        prompt_parts.append('  "relations": [\n')
        
        # ▼▼▼ 修正 ▼▼▼
        # relationのsource_id/target_idも、名前ではなく「コード」を使用する
        prompt_parts.append('    {"type": "USES", "source_id": "FUNC-001", "target_id": "キーパッド", "properties": {}},\n')
        prompt_parts.append('    {"type": "USES", "source_id": "FUNC-001", "target_id": "認証キーDB", "properties": {}},\n')
        prompt_parts.append('    {"type": "CONTROLS", "source_id": "FUNC-001", "target_id": "ドアロックモーター", "properties": {}},\n')
        
        # 修正：Constraintのリレーション (APPLIES_TO) のお手本を追加
        prompt_parts.append('    {"type": "APPLIES_TO", "source_id": "CONST-P-001", "target_id": "FUNC-001", "properties": {}}\n')
        # ▲▲▲ 修正 ▲▲▲
        
        prompt_parts.append('  ]\n')
        prompt_parts.append('}\n')
        prompt_parts.append('```\n\n')
        # --- お手本ここまで ---
        
        # 要件定義書（チャンク）
        prompt_parts.append("## 要件定義書（今回処理するチャンク）\n\n")
        prompt_parts.append(requirements_text)
        prompt_parts.append("\n\n## 出力\n")
        prompt_parts.append("JSON形式でエンティティと関係性を出力してください：")

        return "".join(prompt_parts)