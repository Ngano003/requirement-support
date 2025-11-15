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
            query = """
                MATCH (f:Function {session_id: $session_id})
                WHERE NOT EXISTS ((a:Actor {session_id: $session_id})-[:USES]->(f))
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
            query = """
                MATCH (d:Data {session_id: $session_id})
                WHERE (d.name CONTAINS '個人情報' OR d.name CONTAINS '決済情報' OR d.sensitivity = 'confidential')
                AND NOT EXISTS ((r:Requirement {session_id: $session_id, type: 'Security'})-[:APPLIES_TO]->(d))
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
            query = """
                MATCH (d:Data {session_id: $session_id})
                WHERE NOT EXISTS ((f:Function {session_id: $session_id})-[:MANIPULATES]->(d))
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
            query = """
                MATCH path = (f1:Function {session_id: $session_id})-[:DEPENDS_ON*]->(f1)
                RETURN f1.name AS function_name,
                       [n IN nodes(path) | n.name] AS cycle_path,
                       f1.entity_id AS entity_id
            """

            result = await session.run(query, session_id=session_id)

            return [
                {
                    "function_name": record["function_name"],
                    "cycle_path": record["cycle_path"],
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
            # MemgraphではUNIONを使ったEXISTSがサポートされていないため、分けて検出
            query = """
                MATCH (f1:Function {session_id: $session_id})-[m1:MANIPULATES {action: 'Write'}]->(d:Data {session_id: $session_id}),
                      (f2:Function {session_id: $session_id})-[m2:MANIPULATES {action: 'Write'}]->(d)
                WHERE f1.name <> f2.name
                AND NOT EXISTS ((f1)-[:DEPENDS_ON]->(f2))
                AND NOT EXISTS ((f2)-[:DEPENDS_ON]->(f1))
                RETURN d.name AS data_name,
                       f1.name AS function1,
                       f2.name AS function2,
                       d.entity_id AS data_id,
                       f1.entity_id AS function1_id,
                       f2.entity_id AS function2_id
            """

            result = await session.run(query, session_id=session_id)

            return [
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
