"""
問題検出器（GraphRAG PoC用）

Cypherクエリでヌケモレと矛盾を検出
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
        """ヌケモレを検出"""
        result = {}

        # 1. 利用されない機能
        result["unused_functions"] = await self._detect_unused_functions(session_id)

        # 2. セキュリティ要件の漏れ
        result["missing_security_requirements"] = (
            await self._detect_missing_security_requirements(session_id)
        )

        # 3. 孤立データ
        result["orphan_data"] = await self._detect_orphan_data(session_id)

        return result

    async def detect_contradictions(self, session_id: str) -> Dict[str, List[Dict]]:
        """矛盾を検出"""
        result = {}

        # 1. 循環依存
        result["circular_dependencies"] = (
            await self._detect_circular_dependencies(session_id)
        )

        # 2. 権限の競合
        result["permission_conflicts"] = (
            await self._detect_permission_conflicts(session_id)
        )

        # 3. データアクセスの矛盾
        result["data_access_conflicts"] = (
            await self._detect_data_access_conflicts(session_id)
        )

        return result

    async def _detect_unused_functions(self, session_id: str) -> List[Dict]:
        """利用されない機能を検出"""
        async with self.driver.session() as session:
            # MemgraphではEXISTS {}構文ではなく、NOT EXISTS (pattern)を使用
            # --- 変更前 (エラー) ---
            # query = """
            #     MATCH (f:Function {session_id: $session_id})
            #     WHERE NOT EXISTS ((a:Actor {session_id: $session_id})-[:USES]->(f))
            #     RETURN f.name AS function_name,
            #            f.description AS description,
            #            f.entity_id AS entity_id
            # """
            
            # --- 変更後 (修正) ---
            # OPTIONAL MATCHとcount()を使用して、関係を持たないノードを検出する
            query = """
                MATCH (f:Function {session_id: $session_id})
                OPTIONAL MATCH (a:Actor {session_id: $session_id})-[:USES]->(f)
                WITH f, count(a) AS uses_count
                WHERE uses_count = 0
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
                }
                async for record in result
            ]

    async def _detect_missing_security_requirements(
        self, session_id: str
    ) -> List[Dict]:
        """セキュリティ要件の漏れを検出"""
        async with self.driver.session() as session:
            # OPTIONAL MATCHとcount()を使用して、
            # 特定の関係を持たないノードを検出する（Memgraph互換）
            query = """
                MATCH (d:Data {session_id: $session_id})
                WHERE (d.name CONTAINS '個人情報' OR d.name CONTAINS '決済情報' OR d.sensitivity = 'confidential')
                
                OPTIONAL MATCH (r:Requirement {session_id: $session_id, type: 'Security'})-[:APPLIES_TO]->(d)
                
                WITH d, count(r) AS security_req_count
                WHERE security_req_count = 0
                
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
                }
                async for record in result
            ]

    async def _detect_orphan_data(self, session_id: str) -> List[Dict]:
        """孤立データを検出"""
        async with self.driver.session() as session:
            # --- 変更前 (エラー) ---
            # query = """
            #     MATCH (d:Data {session_id: $session_id})
            #     WHERE NOT EXISTS ((f:Function {session_id: $session_id})-[:MANIPULATES]->(d))
            #     RETURN d.name AS data_name,
            #            d.entity_id AS entity_id
            # """

            # --- 変更後 (修正) ---
            # OPTIONAL MATCHとcount()を使用して、
            # どのFunctionからもMANIPULATESされていないDataを検出
            query = """
                MATCH (d:Data {session_id: $session_id})
                OPTIONAL MATCH (f:Function {session_id: $session_id})-[:MANIPULATES]->(d)
                WITH d, count(f) AS manipulates_count
                WHERE manipulates_count = 0
                RETURN d.name AS data_name,
                       d.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            return [
                {
                    "data_name": record["data_name"],
                    "entity_id": record["entity_id"],
                }
                async for record in result
            ]
            
    async def _detect_circular_dependencies(self, session_id: str) -> List[Dict]:
        """循環依存を検出"""
        async with self.driver.session() as session:
            
            # --- 変更前 (エラー) ---
            # query = """
            #     MATCH path = (f1:Function {session_id: $session_id})-[:DEPENDS_ON*]->(f1)
            #     RETURN f1.name AS function_name,
            #            [n IN nodes(path) | n.name] AS cycle_path,
            #            f1.entity_id AS entity_id
            # """
            
            # --- 変更後 (修正) ---
            # Memgraphがリスト内包表記をサポートしていないため、
            # ノードのリスト(nodes(path))を返し、Python側で処理する
            query = """
                MATCH path = (f1:Function {session_id: $session_id})-[:DEPENDS_ON*]->(f1)
                RETURN f1.name AS function_name,
                       nodes(path) AS cycle_nodes,
                       f1.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            # --- 変更前 ---
            # return [
            #     {
            #         "function_name": record["function_name"],
            #         "cycle_path": record["cycle_path"],
            #         "entity_id": record["entity_id"],
            #     }
            #     async for record in result
            # ]

            # --- 変更後 (修正) ---
            # Python側でノードのリスト(cycle_nodes)から名前のリスト(cycle_path)を生成
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
            # --- 変更前 (エラーの可能性あり) ---
            # query = """
            #     MATCH (f1:Function {session_id: $session_id})-[m1:MANIPULATES {action: 'Write'}]->(d:Data {session_id: $session_id}),
            #           (f2:Function {session_id: $session_id})-[m2:MANIPULATES {action: 'Write'}]->(d)
            #     WHERE f1.name <> f2.name
            #     AND NOT EXISTS ((f1)-[:DEPENDS_ON]->(f2))
            #     AND NOT EXISTS ((f2)-[:DEPENDS_ON]->(f1))
            #     RETURN ...
            # """
            
            # --- 変更後 (修正) ---
            # 競合する書き込みを検出し、OPTIONAL MATCHで依存関係をチェック
            # f1.name < f2.name 条件で重複ペアを除外
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
