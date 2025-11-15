"""
グラフ構築器（GraphRAG PoC用）

Memgraphにエンティティとリレーションを保存
"""

import logging
from typing import Dict, Any, List
from neo4j import AsyncGraphDatabase, AsyncDriver

from config import Config

logger = logging.getLogger(__name__)


class GraphBuilder:
    """グラフ構築器"""

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

        # 接続テスト
        async with self.driver.session() as session:
            result = await session.run("RETURN 1 AS test")
            await result.consume()

        logger.info(f"Connected to Memgraph at {uri}")

    async def close(self):
        """接続を閉じる"""
        if self.driver:
            await self.driver.close()
            logger.info("Closed Memgraph connection")

    async def clear_session(self, session_id: str):
        """セッションのグラフをクリア"""
        async with self.driver.session() as session:
            query = """
                MATCH (n {session_id: $session_id})
                DETACH DELETE n
            """
            await session.run(query, session_id=session_id)

        logger.info(f"Cleared graph for session: {session_id}")

    async def build_graph(
        self,
        session_id: str,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        エンティティとリレーションからグラフを構築

        Args:
            session_id: セッションID
            entities: エンティティリスト
            relations: リレーションリスト

        Returns:
            統計情報 {"nodes_created": 5, "edges_created": 7}
        """
        try:
            # 既存のグラフをクリア
            await self.clear_session(session_id)

            # ノードを作成
            nodes_created = await self._create_nodes(session_id, entities)

            # エッジを作成
            edges_created = await self._create_edges(session_id, relations)

            logger.info(
                f"Graph built: {nodes_created} nodes, {edges_created} edges"
            )

            return {
                "nodes_created": nodes_created,
                "edges_created": edges_created,
            }

        except Exception as e:
            logger.error(f"Graph building failed: {e}", exc_info=True)
            raise

    async def _create_nodes(
        self, session_id: str, entities: List[Dict[str, Any]]
    ) -> int:
        """ノードを作成"""
        nodes_created = 0

        async with self.driver.session() as session:
            for entity in entities:
                entity_type = entity["type"]
                entity_id = entity["id"]
                properties = entity["properties"]

                # プロパティにsession_idとidを追加
                all_properties = {
                    "session_id": session_id,
                    "entity_id": entity_id,
                    **properties,
                }

                # Cypherクエリを動的に構築
                query = f"""
                    CREATE (n:{entity_type} $properties)
                    RETURN n
                """

                await session.run(query, properties=all_properties)
                nodes_created += 1

        logger.info(f"Created {nodes_created} nodes")
        return nodes_created

    async def _create_edges(
        self, session_id: str, relations: List[Dict[str, Any]]
    ) -> int:
        """エッジを作成"""
        edges_created = 0

        async with self.driver.session() as session:
            for relation in relations:
                relation_type = relation["type"]
                source_id = relation["source_id"]
                target_id = relation["target_id"]
                properties = relation.get("properties", {})

                # Cypherクエリ
                query = f"""
                    MATCH (source {{session_id: $session_id, entity_id: $source_id}})
                    MATCH (target {{session_id: $session_id, entity_id: $target_id}})
                    CREATE (source)-[r:{relation_type} $properties]->(target)
                    RETURN r
                """

                result = await session.run(
                    query,
                    session_id=session_id,
                    source_id=source_id,
                    target_id=target_id,
                    properties=properties,
                )

                # エッジが作成されたか確認
                if await result.single():
                    edges_created += 1

        logger.info(f"Created {edges_created} edges")
        return edges_created

    async def get_graph_stats(self, session_id: str) -> Dict[str, Any]:
        """グラフの統計情報を取得"""
        async with self.driver.session() as session:
            # ノード数を取得
            node_count_query = """
                MATCH (n {session_id: $session_id})
                RETURN count(n) AS node_count
            """
            result = await session.run(node_count_query, session_id=session_id)
            record = await result.single()
            node_count = record["node_count"]

            # エッジ数を取得
            edge_count_query = """
                MATCH (n {session_id: $session_id})-[r]->()
                RETURN count(r) AS edge_count
            """
            result = await session.run(edge_count_query, session_id=session_id)
            record = await result.single()
            edge_count = record["edge_count"]

            # ノードタイプ別カウント
            node_types_query = """
                MATCH (n {session_id: $session_id})
                RETURN labels(n)[0] AS type, count(n) AS count
            """
            result = await session.run(node_types_query, session_id=session_id)
            node_types = {record["type"]: record["count"] async for record in result}

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "node_types": node_types,
        }
