#!/usr/bin/env python3
"""
GraphRAG PoC メインスクリプト

要件定義書からエンティティを抽出し、グラフを構築し、問題を検出する
"""

import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Any

from config import Config
from entity_extractor import EntityExtractor
from graph_builder import GraphBuilder
from problem_detector import ProblemDetector
from analysis_reporter import AnalysisReporter
from dotenv import load_dotenv

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

class GraphRAGPoC:
    """GraphRAG実現性検証スクリプト"""

    def __init__(self, config: Config, schema_mapping: Dict[str, Any] = None):
        self.config = config
        self.schema_mapping = schema_mapping
        self.entity_extractor = EntityExtractor(config, schema_mapping=schema_mapping)
        self.graph_builder = GraphBuilder(config)
        self.problem_detector = ProblemDetector(config)

    async def run(self, requirements_file: str) -> Dict[str, Any]:
        """
        検証を実行

        Args:
            requirements_file: 要件定義書ファイルパス

        Returns:
            検証結果（dict）
        """
        logger.info("=" * 80)
        logger.info("GraphRAG PoC Started")
        logger.info("=" * 80)

        overall_start_time = time.time()

        try:
            # Memgraphに接続
            await self.graph_builder.connect()
            await self.problem_detector.connect()

            # 1. 要件定義書を読み込み
            logger.info(f"\n[Step 1] Loading requirements from: {requirements_file}")
            requirements_text = self._load_requirements(requirements_file)
            logger.info(f"Loaded {len(requirements_text)} characters")

            # 2. エンティティ抽出（LLM使用）
            logger.info("\n[Step 2] Extracting entities and relations...")
            extraction_start = time.time()
            extraction_result = await self.entity_extractor.extract(requirements_text)
            extraction_time = time.time() - extraction_start

            logger.info(
                f"Extraction completed in {extraction_time:.2f}s\n"
                f"  - Entities: {len(extraction_result['entities'])}\n"
                f"  - Relations: {len(extraction_result['relations'])}\n"
                f"  - Validation errors: {len(extraction_result['validation_errors'])}"
            )

            # 3. グラフ構築（Memgraphに保存）
            logger.info("\n[Step 3] Building graph in Memgraph...")
            session_id = self._generate_session_id()
            build_start = time.time()

            build_stats = await self.graph_builder.build_graph(
                session_id=session_id,
                entities=extraction_result['entities'],
                relations=extraction_result['relations']
            )

            build_time = time.time() - build_start

            logger.info(
                f"Graph built in {build_time:.2f}s\n"
                f"  - Nodes created: {build_stats['nodes_created']}\n"
                f"  - Edges created: {build_stats['edges_created']}"
            )

            # グラフ統計を取得
            graph_stats = await self.graph_builder.get_graph_stats(session_id)
            logger.info(
                f"Graph statistics:\n"
                f"  - Total nodes: {graph_stats['node_count']}\n"
                f"  - Total edges: {graph_stats['edge_count']}\n"
                f"  - Node types: {graph_stats['node_types']}"
            )

            # 4. 問題検出（Cypherクエリ実行）
            logger.info("\n[Step 4] Detecting problems...")
            detection_start = time.time()
            detection_result = await self.problem_detector.detect_all(session_id)
            detection_time = time.time() - detection_start

            logger.info(f"Problem detection completed in {detection_time:.2f}s")

            # 5. 結果の集計・出力
            logger.info("\n[Step 5] Generating report...")
            result = self._generate_report(
                extraction_result=extraction_result,
                graph_stats=graph_stats,
                detection_result=detection_result,
                extraction_time=extraction_time,
                build_time=build_time,
                detection_time=detection_time,
                session_id=session_id,
            )

            overall_time = time.time() - overall_start_time
            logger.info(f"\nTotal time: {overall_time:.2f}s")

            # 結果をファイルに保存
            self._save_results(result)

            logger.info("\n" + "=" * 80)
            logger.info("GraphRAG PoC Completed Successfully")
            logger.info("=" * 80)

            return result

        except Exception as e:
            logger.error(f"PoC execution failed: {e}", exc_info=True)
            raise

        finally:
            # 接続を閉じる
            await self.graph_builder.close()
            await self.problem_detector.close()

    def _load_requirements(self, file_path: str) -> str:
        """要件定義書を読み込み"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Requirements file not found: {file_path}")

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _generate_session_id(self) -> str:
        """セッションIDを生成"""
        return f"poc-{uuid.uuid4()}"

    def _generate_report(
        self,
        extraction_result: Dict,
        graph_stats: Dict,
        detection_result: Dict,
        extraction_time: float,
        build_time: float,
        detection_time: float,
        session_id: str,
    ) -> Dict[str, Any]:
        """レポートを生成"""

        # ヌケモレのサマリー
        missing_items = detection_result["missing_items"]
        missing_summary = {
            "isolated_functions": len(missing_items.get("isolated_functions", [])),
            "unused_actors": len(missing_items.get("unused_actors", [])),
            "unsatisfied_requirements": len(missing_items.get("unsatisfied_requirements", [])),
            "orphan_data": len(missing_items.get("orphan_data", [])),
            "orphan_hardware": len(missing_items.get("orphan_hardware", [])),
            "isolated_constraints": len(missing_items.get("isolated_constraints", [])),
            "missing_security_constraints": len(missing_items.get("missing_security_constraints", [])),
        }

        # 矛盾のサマリー
        contradictions = detection_result["contradictions"]
        contradiction_summary = {
            "circular_dependencies": len(contradictions["circular_dependencies"]),
            "permission_conflicts": len(contradictions["permission_conflicts"]),
            "data_access_conflicts": len(contradictions["data_access_conflicts"]),
        }

        # 総合評価
        total_issues = sum(missing_summary.values()) + sum(contradiction_summary.values())

        return {
            "session_id": session_id,
            "summary": {
                "total_issues": total_issues,
                "missing_items_count": sum(missing_summary.values()),
                "contradictions_count": sum(contradiction_summary.values()),
            },
            "extraction": {
                "entities_count": len(extraction_result["entities"]),
                "relations_count": len(extraction_result["relations"]),
                "validation_errors_count": len(extraction_result["validation_errors"]),
                "validation_errors": extraction_result["validation_errors"],
            },
            "graph": graph_stats,
            "detection": {
                "missing_items": {
                    "summary": missing_summary,
                    "details": missing_items,
                },
                "contradictions": {
                    "summary": contradiction_summary,
                    "details": contradictions,
                },
            },
            "performance": {
                "extraction_time_seconds": round(extraction_time, 2),
                "build_time_seconds": round(build_time, 2),
                "detection_time_seconds": round(detection_time, 2),
                "total_time_seconds": round(extraction_time + build_time + detection_time, 2),
            },
        }

    def _save_results(self, result: Dict[str, Any]):
        """結果をファイルに保存"""
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)

        # 抽出結果を保存
        extraction_output = output_dir / "extracted_entities.json"
        with open(extraction_output, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "entities": result["extraction"]["entities_count"],
                    "relations": result["extraction"]["relations_count"],
                    "validation_errors": result["extraction"]["validation_errors"],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info(f"Saved extraction results to: {extraction_output}")

        # 検出結果を保存
        detection_output = output_dir / "detection_results.json"
        with open(detection_output, "w", encoding="utf-8") as f:
            json.dump(
                result["detection"],
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info(f"Saved detection results to: {detection_output}")

        # パフォーマンス測定結果を保存
        performance_output = output_dir / "performance_metrics.json"
        with open(performance_output, "w", encoding="utf-8") as f:
            json.dump(
                result["performance"],
                f,
                ensure_ascii=False,
                indent=2,
            )
        logger.info(f"Saved performance metrics to: {performance_output}")

        # 統合レポートを保存
        full_report_output = output_dir / "full_report.json"
        with open(full_report_output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved full report to: {full_report_output}")

        # マークダウン形式の分析レポートを生成・保存
        markdown_report = AnalysisReporter.generate_markdown_report(result)
        analysis_report_output = output_dir / "analysis_report.md"
        with open(analysis_report_output, "w", encoding="utf-8") as f:
            f.write(markdown_report)
        logger.info(f"Saved analysis report to: {analysis_report_output}")


async def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="GraphRAG PoC Script")
    parser.add_argument(
        "requirements_file",
        type=str,
        help="要件定義書ファイルパス",
    )
    parser.add_argument(
        "--llm-provider",
        type=str,
        choices=["openai", "google_ai", "openrouter", "vllm"],
        default="google_ai",
        help="LLMプロバイダー（デフォルト: google_ai）",
    )
    parser.add_argument(
        "--schema-mapping",
        type=str,
        help="スキーママッピングJSONファイルパス（オプション）",
    )

    args = parser.parse_args()

    # 設定を読み込み
    config = Config.from_env()

    # コマンドライン引数でLLMプロバイダーを上書き
    if args.llm_provider:
        config.llm_provider = args.llm_provider

    logger.info(f"Using LLM provider: {config.llm_provider}")

    # スキーママッピングを読み込み（指定されている場合）
    schema_mapping = None
    if args.schema_mapping:
        schema_mapping_path = Path(args.schema_mapping)
        if schema_mapping_path.exists():
            with open(schema_mapping_path, "r", encoding="utf-8") as f:
                schema_mapping = json.load(f)
            logger.info(f"Loaded schema mapping from: {args.schema_mapping}")
        else:
            logger.warning(f"Schema mapping file not found: {args.schema_mapping}")

    # PoCを実行
    poc = GraphRAGPoC(config, schema_mapping=schema_mapping)
    result = await poc.run(args.requirements_file)

    # コンソールに読みやすいサマリーを表示
    AnalysisReporter.print_console_summary(result)


if __name__ == "__main__":
    asyncio.run(main())
