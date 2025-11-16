"""
問題検出器（GraphRAG PoC用 - IS/SHOULDレイヤーモデル）

Cypherクエリでヌケモレと矛盾を検出
- ISレイヤー: Function中心の構造グラフからヌケモレを検出
- SHOULDレイヤー: Constraint中心の制約グラフから矛盾を検出
- IS vs SHOULD: 構造と制約の矛盾を検出

矛盾検出アプローチ：
- Cypherで矛盾の可能性がある候補ペアを抽出
- LLMで候補が本当に矛盾しているか論理判定
"""

import logging
from typing import Dict, Any, List
from neo4j import AsyncGraphDatabase, AsyncDriver

from config import Config

logger = logging.getLogger(__name__)


class ProblemDetector:
    """問題検出器"""

    def __init__(self, config: Config):
        self.config = config
        self.driver: AsyncDriver | None = None

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

    async def connect(self):
        """Memgraphに接続"""
        uri = f"bolt://{self.config.memgraph_host}:{self.config.memgraph_port}"

        if self.config.memgraph_username:
            auth = (self.config.memgraph_username, self.config.memgraph_password)
        else:
            auth = None

        self.driver = AsyncGraphDatabase.driver(uri, auth=auth)

        logger.info(f"ProblemDetector connected to Memgraph at {uri}")

    async def close(self):
        """接続を閉じる"""
        if self.driver:
            await self.driver.close()

    async def _llm_judge_contradiction(self, prompt: str) -> Dict[str, Any]:
        """
        LLMを使って矛盾候補が本当に矛盾しているか判定

        Args:
            prompt: 判定用プロンプト

        Returns:
            {
                "is_contradiction": bool,
                "reasoning": str,
                "recommended_action": str
            }
        """
        try:
            print(f"prompt:{prompt}")
            if self.google_model:
                # Google AI Studio (Gemini)
                response = self.google_model.generate_content(prompt)
                response_text = response.text
            else:
                # OpenAI互換API
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,  # 判定は一貫性を重視
                )
                response_text = response.choices[0].message.content

            # レスポンスをパース
            # 期待形式: "回答 (YES/NO/UNCLEAR): 理由: 推奨対処:"
            print(f"response:{response_text}")
            lines = response_text.strip().split('\n')
            is_contradiction = False
            reasoning = ""
            recommended_action = ""

            for line in lines:
                if line.startswith("回答") or line.startswith("答え") or line.startswith("判定"):
                    # YES/NO/UNCLEARを抽出
                    if "YES" in line.upper() or "はい" in line or "矛盾" in line:
                        is_contradiction = True
                elif line.startswith("理由"):
                    reasoning = line.split(":", 1)[1].strip() if ":" in line else line
                elif line.startswith("推奨対処") or line.startswith("対処"):
                    recommended_action = line.split(":", 1)[1].strip() if ":" in line else line
                else:
                    # マルチライン対応
                    if reasoning and not recommended_action:
                        reasoning += " " + line
                    elif recommended_action:
                        recommended_action += " " + line

            # 理由が取得できなかった場合は全文を理由とする
            if not reasoning:
                reasoning = response_text

            return {
                "is_contradiction": is_contradiction,
                "reasoning": reasoning.strip(),
                "recommended_action": recommended_action.strip()
            }

        except Exception as e:
            logger.error(f"LLM judgment failed: {e}")
            # エラー時は安全側（矛盾と判定）
            return {
                "is_contradiction": True,
                "reasoning": f"LLM判定エラー: {str(e)}",
                "recommended_action": "手動確認が必要"
            }

    async def detect_all(self, session_id: str) -> Dict[str, Any]:
        """
        すべての問題を検出

        Args:
            session_id: セッションID

        Returns:
            {
                "missing_items": {...},
                "contradictions": {...}
            }
        """
        missing_items = await self.detect_missing_items(session_id)
        contradictions = await self.detect_contradictions(session_id)

        return {
            "missing_items": missing_items,
            "contradictions": contradictions,
        }

    async def detect_missing_items(self, session_id: str) -> Dict[str, List[Dict]]:
        """ヌケモレを検出（ISレイヤー + SHOULDレイヤー）"""
        result = {}

        # ISレイヤーのヌケモレ
        # 1. 孤立したFunction
        result["isolated_functions"] = await self._detect_isolated_functions(session_id)

        # 2. Functionと関係を持たないActor
        result["unused_actors"] = await self._detect_unused_actors(session_id)

        # 3. Functionによって満たされていないRequirement
        result["unsatisfied_requirements"] = await self._detect_unsatisfied_requirements(session_id)

        # 4. Functionと関係を持たないData
        result["orphan_data"] = await self._detect_orphan_data(session_id)

        # 5. Functionと関係を持たないHardware
        result["orphan_hardware"] = await self._detect_orphan_hardware(session_id)

        # SHOULDレイヤーのヌケモレ
        # 6. 適用対象のないConstraint
        result["isolated_constraints"] = await self._detect_isolated_constraints(session_id)

        # 7. セキュリティ制約の漏れ
        result["missing_security_constraints"] = (
            await self._detect_missing_security_constraints(session_id)
        )

        return result

    async def detect_contradictions(self, session_id: str) -> Dict[str, List[Dict]]:
        """矛盾を検出"""
        result = {}

        # 1. 循環依存（確定検出）
        result["circular_dependencies"] = (
            await self._detect_circular_dependencies(session_id)
        )

        # 2. 権限の競合（候補抽出 + LLM判定）
        result["permission_conflicts"] = (
            await self._detect_permission_conflicts(session_id)
        )

        # 3. データアクセスの矛盾（候補抽出 + LLM判定）
        result["data_access_conflicts"] = (
            await self._detect_data_access_conflicts(session_id)
        )

        # 4. Actor→Hardware間接制御とConstraintの矛盾（候補抽出 + LLM判定）
        result["actor_hardware_conflicts"] = (
            await self._detect_actor_hardware_conflicts(session_id)
        )

        # 5. Actor→Data間接アクセスとConstraintの矛盾（候補抽出 + LLM判定）
        result["actor_data_conflicts"] = (
            await self._detect_actor_data_conflicts(session_id)
        )

        return result

    async def _detect_isolated_functions(self, session_id: str) -> List[Dict]:
        """孤立したFunction（他のFunctionやActorと無関係）を検出"""
        async with self.driver.session() as session:
            query = """
                MATCH (f:Function {session_id: $session_id})
                OPTIONAL MATCH (f)-[:DEPENDS_ON]->(:Function {session_id: $session_id})
                OPTIONAL MATCH (f)<-[:DEPENDS_ON]-(:Function {session_id: $session_id})
                OPTIONAL MATCH (a:Actor {session_id: $session_id})-[:USES]->(f)
                WITH f, count(DISTINCT a) AS actor_count
                WHERE actor_count = 0
                RETURN f.name AS function_name,
                       f.description AS description,
                       f.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            return [
                {
                    "function_name": record["function_name"],
                    "description": record.get("description"),
                    "entity_id": record["entity_id"],
                    "issue_type": "孤立したFunction",
                }
                async for record in result
            ]

    async def _detect_unused_actors(self, session_id: str) -> List[Dict]:
        """Functionと関係を持たないActorを検出"""
        async with self.driver.session() as session:
            query = """
                MATCH (a:Actor {session_id: $session_id})
                OPTIONAL MATCH (a)-[:USES]->(:Function {session_id: $session_id})
                WITH a, count(*) AS uses_count
                WHERE uses_count = 0
                RETURN a.name AS actor_name,
                       a.description AS description,
                       a.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            return [
                {
                    "actor_name": record["actor_name"],
                    "description": record.get("description"),
                    "entity_id": record["entity_id"],
                    "issue_type": "Functionと関係を持たないActor",
                }
                async for record in result
            ]

    async def _detect_unsatisfied_requirements(self, session_id: str) -> List[Dict]:
        """Functionによって満たされていないRequirementを検出"""
        async with self.driver.session() as session:
            query = """
                MATCH (r:Requirement {session_id: $session_id})
                OPTIONAL MATCH (f:Function {session_id: $session_id})-[:SATISFIES]->(r)
                WITH r, count(f) AS satisfies_count
                WHERE satisfies_count = 0
                RETURN r.name AS requirement_name,
                       r.description AS description,
                       r.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            return [
                {
                    "requirement_name": record["requirement_name"],
                    "description": record.get("description"),
                    "entity_id": record["entity_id"],
                    "issue_type": "Functionによって満たされていないRequirement",
                }
                async for record in result
            ]

    async def _detect_orphan_hardware(self, session_id: str) -> List[Dict]:
        """Functionと関係を持たないHardwareを検出"""
        async with self.driver.session() as session:
            query = """
                MATCH (h:Hardware {session_id: $session_id})
                OPTIONAL MATCH (f:Function {session_id: $session_id})-[:CONTROLS]->(h)
                WITH h, count(f) AS controls_count
                WHERE controls_count = 0
                RETURN h.name AS hardware_name,
                       h.description AS description,
                       h.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            return [
                {
                    "hardware_name": record["hardware_name"],
                    "description": record.get("description"),
                    "entity_id": record["entity_id"],
                    "issue_type": "Functionと関係を持たないHardware",
                }
                async for record in result
            ]

    async def _detect_isolated_constraints(self, session_id: str) -> List[Dict]:
        """適用対象のないConstraintを検出"""
        async with self.driver.session() as session:
            query = """
                MATCH (c:Constraint {session_id: $session_id})
                OPTIONAL MATCH (c)-[:APPLIES_TO]->()
                WITH c, count(*) AS applies_count
                WHERE applies_count = 0
                RETURN c.name AS constraint_name,
                       c.category AS category,
                       c.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            return [
                {
                    "constraint_name": record["constraint_name"],
                    "category": record.get("category"),
                    "entity_id": record["entity_id"],
                    "issue_type": "適用対象のないConstraint",
                }
                async for record in result
            ]

    async def _detect_missing_security_constraints(
        self, session_id: str
    ) -> List[Dict]:
        """セキュリティ制約の漏れを検出"""
        async with self.driver.session() as session:
            query = """
                MATCH (d:Data {session_id: $session_id})
                WHERE (d.name CONTAINS '個人情報' OR d.name CONTAINS '決済情報' OR d.sensitivity = 'confidential')

                OPTIONAL MATCH (c:Constraint {session_id: $session_id, category: 'Security'})-[:APPLIES_TO]->(d)

                WITH d, count(c) AS security_constraint_count
                WHERE security_constraint_count = 0

                RETURN d.name AS data_name,
                       d.sensitivity AS sensitivity,
                       d.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            return [
                {
                    "data_name": record["data_name"],
                    "sensitivity": record.get("sensitivity"),
                    "entity_id": record["entity_id"],
                    "issue_type": "セキュリティConstraintが未適用",
                }
                async for record in result
            ]

    async def _detect_orphan_data(self, session_id: str) -> List[Dict]:
        """Functionと関係を持たないDataを検出"""
        async with self.driver.session() as session:
            query = """
                MATCH (d:Data {session_id: $session_id})
                OPTIONAL MATCH (f:Function {session_id: $session_id})-[:MANIPULATES]->(d)
                WITH d, count(f) AS manipulates_count
                WHERE manipulates_count = 0
                RETURN d.name AS data_name,
                       d.description AS description,
                       d.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            return [
                {
                    "data_name": record["data_name"],
                    "description": record.get("description"),
                    "entity_id": record["entity_id"],
                    "issue_type": "Functionと関係を持たないData",
                }
                async for record in result
            ]
            
    async def _detect_circular_dependencies(self, session_id: str) -> List[Dict]:
        """循環依存を検出"""
        async with self.driver.session() as session:
            query = """
                MATCH path = (f1:Function {session_id: $session_id})-[:DEPENDS_ON*]->(f1)
                RETURN f1.name AS function_name,
                       nodes(path) AS cycle_nodes,
                       f1.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            return [
                {
                    "function_name": record["function_name"],
                    "cycle_path": [node["name"] for node in record["cycle_nodes"]],
                    "entity_id": record["entity_id"],
                }
                async for record in result
            ]

    async def _detect_permission_conflicts(self, session_id: str) -> List[Dict]:
        """権限の競合を検出"""
        async with self.driver.session() as session:
            query = """
                MATCH (a:Actor {session_id: $session_id})-[r1:AUTHORIZES {permission: 'Allow'}]->(f:Function {session_id: $session_id}),
                      (a)-[r2:AUTHORIZES {permission: 'Deny'}]->(f)
                RETURN a.name AS actor_name,
                       f.name AS function_name,
                       a.entity_id AS actor_id,
                       f.entity_id AS function_id
            """

            result = await session.run(query, session_id=session_id)
            print(f"_detect_permission_conflicts result:{result}")
            return [
                {
                    "actor_name": record["actor_name"],
                    "function_name": record["function_name"],
                    "actor_id": record["actor_id"],
                    "function_id": record["function_id"],
                    "conflict_type": "Permission conflict",
                }
                async for record in result
            ]

    async def _detect_data_access_conflicts(self, session_id: str) -> List[Dict]:
        """データアクセスの矛盾を検出"""
        async with self.driver.session() as session:
            query = """
                MATCH (f1:Function {session_id: $session_id})-[m1:MANIPULATES {action: 'Write'}]->(d:Data {session_id: $session_id}),
                      (f2:Function {session_id: $session_id})-[m2:MANIPULATES {action: 'Write'}]->(d)
                WHERE f1.name < f2.name

                OPTIONAL MATCH (f1)-[r_f1_f2:DEPENDS_ON]->(f2)
                OPTIONAL MATCH (f2)-[r_f2_f1:DEPENDS_ON]->(f1)
                
                WITH f1, f2, d, r_f1_f2, r_f2_f1
                WHERE r_f1_f2 IS NULL AND r_f2_f1 IS NULL
                
                RETURN d.name AS data_name,
                       f1.name AS function1,
                       f2.name AS function2,
                       d.entity_id AS data_id,
                       f1.entity_id AS function1_id,
                       f2.entity_id AS function2_id
            """

            result = await session.run(query, session_id=session_id)
            print(f"_detect_data_access_conflicts result:{result}")
            conflicts = [
                {
                    "data_name": record["data_name"],
                    "function1": record["function1"],
                    "function2": record["function2"],
                    "data_id": record["data_id"],
                    "function1_id": record["function1_id"],
                    "function2_id": record["function2_id"],
                    "issue": "Concurrent write without dependency",
                }
                async for record in result
            ]

            # 各競合について周辺情報を取得
            for conflict in conflicts:
                conflict["context"] = await self._get_conflict_context(
                    session_id, conflict["data_id"], conflict["function1_id"], conflict["function2_id"]
                )

            return conflicts

    async def _get_conflict_context(
        self, session_id: str, data_id: str, function1_id: str, function2_id: str
    ) -> Dict[str, Any]:
        """データアクセス競合の周辺情報を取得"""
        async with self.driver.session() as session:
            # データの詳細情報を取得
            data_query = """
                MATCH (d:Data {session_id: $session_id, entity_id: $data_id})
                OPTIONAL MATCH (d)-[:STORED_IN]->(storage)
                OPTIONAL MATCH (req:Requirement {session_id: $session_id, type: 'Security'})-[:APPLIES_TO]->(d)
                RETURN d.name AS data_name,
                       d.description AS data_description,
                       d.sensitivity AS sensitivity,
                       d.data_type AS data_type,
                       storage.name AS storage_location,
                       COLLECT(DISTINCT req.name) AS security_requirements
            """
            data_result = await session.run(query=data_query, session_id=session_id, data_id=data_id)
            print(f"_get_conflict_context result:{data_query}")
            data_record = await data_result.single()

            # 機能1の詳細情報を取得
            func1_query = """
                MATCH (f:Function {session_id: $session_id, entity_id: $func_id})
                OPTIONAL MATCH (a:Actor {session_id: $session_id})-[:USES]->(f)
                OPTIONAL MATCH (f)-[m:MANIPULATES]->(d:Data {session_id: $session_id})
                RETURN f.name AS function_name,
                       f.description AS function_description,
                       COLLECT(DISTINCT a.name) AS actors,
                       COLLECT(DISTINCT {data: d.name, action: m.action}) AS data_operations
            """
            func1_result = await session.run(query=func1_query, session_id=session_id, func_id=function1_id)
            func1_record = await func1_result.single()

            # 機能2の詳細情報を取得
            func2_result = await session.run(query=func1_query, session_id=session_id, func_id=function2_id)
            func2_record = await func2_result.single()

            return {
                "data": {
                    "name": data_record["data_name"] if data_record else None,
                    "description": data_record["data_description"] if data_record else None,
                    "sensitivity": data_record["sensitivity"] if data_record else None,
                    "data_type": data_record["data_type"] if data_record else None,
                    "storage_location": data_record["storage_location"] if data_record else None,
                    "security_requirements": [r for r in (data_record["security_requirements"] if data_record else []) if r],
                },
                "function1": {
                    "name": func1_record["function_name"] if func1_record else None,
                    "description": func1_record["function_description"] if func1_record else None,
                    "actors": [a for a in (func1_record["actors"] if func1_record else []) if a],
                    "data_operations": func1_record["data_operations"] if func1_record else [],
                },
                "function2": {
                    "name": func2_record["function_name"] if func2_record else None,
                    "description": func2_record["function_description"] if func2_record else None,
                    "actors": [a for a in (func2_record["actors"] if func2_record else []) if a],
                    "data_operations": func2_record["data_operations"] if func2_record else [],
                },
            }

    async def _detect_actor_hardware_conflicts(self, session_id: str) -> List[Dict]:
        """
        Actor→Hardware間接制御とConstraintの矛盾を検出（Query 12-A）

        Actorが Function を経由して Hardware を制御するパスが、
        排他的なConstraint（「のみ」「only」）と矛盾していないかを検出
        """
        async with self.driver.session() as session:
            # Cypherで候補を抽出
            query = """
                MATCH path = (a:Actor {session_id: $session_id})-[:USES]->(f:Function {session_id: $session_id})-[:CONTROLS]->(h:Hardware {session_id: $session_id})

                MATCH (c:Constraint {session_id: $session_id})-[:APPLIES_TO]->(h)

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
                       c.name AS constraint_description,
                       c.category AS constraint_category,
                       collect(DISTINCT allowed_actor.name) AS allowed_actors,
                       nodes(path) AS path_nodes
            """

            result = await session.run(query, session_id=session_id)
            print(f"_detect_actor_hardware_conflicts result:{result}")
            conflicts = []

            async for record in result:
                # アクセスパスを生成
                access_path = [node["name"] for node in record["path_nodes"]]

                # LLM判定用プロンプトを構築
                allowed_actors_str = ", ".join([a for a in record["allowed_actors"] if a]) or "明示的な許可なし"

                prompt = f"""以下の構造パスと制約を分析し、論理的な矛盾があるか判定してください。

【構造（IS）】
アクセスパス: {" → ".join(access_path)}
- {record['accessing_actor']}が{record['function_name']}を使用し、その機能が{record['hardware_name']}を制御します
- 機能の説明: {record.get('function_description', '説明なし')}
- ハードウェアの説明: {record.get('hardware_description', '説明なし')}

【制約（SHOULD）】
制約: {record['constraint_name']} ({record['constraint_category']})
内容: "{record['constraint_description']}"
許可されているアクター: {allowed_actors_str}

【質問】
{record['accessing_actor']}は{record['hardware_name']}を間接的に制御できますが、制約"{record['constraint_description']}"と矛盾していますか？

回答 (YES/NO/UNCLEAR):
理由:
推奨対処:"""

                # LLMに判定を依頼
                judgment = await self._llm_judge_contradiction(prompt)
                print(f"judgement: {judgment}")
                
                # 矛盾と判定された場合のみ結果に追加
                if judgment["is_contradiction"]:
                    conflicts.append({
                        "accessing_actor": record["accessing_actor"],
                        "accessing_actor_id": record["accessing_actor_id"],
                        "function_name": record["function_name"],
                        "function_id": record["function_id"],
                        "hardware_name": record["hardware_name"],
                        "hardware_id": record["hardware_id"],
                        "constraint_name": record["constraint_name"],
                        "constraint_id": record["constraint_id"],
                        "constraint_description": record["constraint_description"],
                        "allowed_actors": [a for a in record["allowed_actors"] if a],
                        "access_path": access_path,
                        "issue_type": "Actor-Hardware間接制御とConstraintの矛盾",
                        "llm_reasoning": judgment["reasoning"],
                        "recommended_action": judgment["recommended_action"]
                    })

            return conflicts

    async def _detect_actor_data_conflicts(self, session_id: str) -> List[Dict]:
        """
        Actor→Data間接アクセスとConstraintの矛盾を検出（Query 12-B）

        Actorが Function を経由して Data にアクセスするパスが、
        排他的なConstraint（「のみ」「only」）と矛盾していないかを検出
        """
        async with self.driver.session() as session:
            # Cypherで候補を抽出
            query = """
                MATCH path = (a:Actor {session_id: $session_id})-[:USES]->(f:Function {session_id: $session_id})-[m:MANIPULATES]->(d:Data {session_id: $session_id})

                MATCH (c:Constraint {session_id: $session_id})-[:APPLIES_TO]->(d)

                OPTIONAL MATCH (c)-[:APPLIES_TO]->(allowed_actor:Actor {session_id: $session_id})

                RETURN a.name AS accessing_actor,
                       a.entity_id AS accessing_actor_id,
                       f.name AS function_name,
                       f.entity_id AS function_id,
                       f.description AS function_description,
                       d.name AS data_name,
                       d.entity_id AS data_id,
                       d.description AS data_description,
                       m.action AS access_action,
                       c.name AS constraint_name,
                       c.entity_id AS constraint_id,
                       c.name AS constraint_description,
                       c.category AS constraint_category,
                       collect(DISTINCT allowed_actor.name) AS allowed_actors,
                       nodes(path) AS path_nodes
            """

            result = await session.run(query, session_id=session_id)
            print(f"_detect_actor_data_conflicts result:{result}")
            conflicts = []

            async for record in result:
                # アクセスパスを生成
                access_path = [node["name"] for node in record["path_nodes"]]

                # LLM判定用プロンプトを構築
                allowed_actors_str = ", ".join([a for a in record["allowed_actors"] if a]) or "明示的な許可なし"

                prompt = f"""以下の構造パスと制約を分析し、論理的な矛盾があるか判定してください。

【構造（IS）】
アクセスパス: {" → ".join(access_path)}
- {record['accessing_actor']}が{record['function_name']}を使用し、その機能が{record['data_name']}に{record['access_action']}アクセスします
- 機能の説明: {record.get('function_description', '説明なし')}
- データの説明: {record.get('data_description', '説明なし')}

【制約（SHOULD）】
制約: {record['constraint_name']} ({record['constraint_category']})
内容: "{record['constraint_description']}"
許可されているアクター: {allowed_actors_str}

【質問】
{record['accessing_actor']}は{record['data_name']}を間接的に{record['access_action']}できますが、制約"{record['constraint_description']}"と矛盾していますか？

回答 (YES/NO/UNCLEAR):
理由:
推奨対処:"""

                # LLMに判定を依頼
                judgment = await self._llm_judge_contradiction(prompt)
                print(f"judgement: {judgment}")
                
                # 矛盾と判定された場合のみ結果に追加
                if judgment["is_contradiction"]:
                    conflicts.append({
                        "accessing_actor": record["accessing_actor"],
                        "accessing_actor_id": record["accessing_actor_id"],
                        "function_name": record["function_name"],
                        "function_id": record["function_id"],
                        "data_name": record["data_name"],
                        "data_id": record["data_id"],
                        "access_action": record["access_action"],
                        "constraint_name": record["constraint_name"],
                        "constraint_id": record["constraint_id"],
                        "constraint_description": record["constraint_description"],
                        "allowed_actors": [a for a in record["allowed_actors"] if a],
                        "access_path": access_path,
                        "issue_type": "Actor-Data間接アクセスとConstraintの矛盾",
                        "llm_reasoning": judgment["reasoning"],
                        "recommended_action": judgment["recommended_action"]
                    })

            return conflicts
