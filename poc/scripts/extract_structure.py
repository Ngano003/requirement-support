#!/usr/bin/env python3
"""
構造抽出スクリプト（フェーズA + フェーズB）

要件定義書から構造候補を抽出し、スキーママッピングを生成する
"""

import asyncio
import logging
from pathlib import Path
import sys

from config import Config
from structure_extractor import StructureExtractor
from schema_mapper import SchemaMapper
from dotenv import load_dotenv

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()


async def main():
    """メイン関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Extract structure from requirements document")
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
        "--output-dir",
        type=str,
        default="output",
        help="出力ディレクトリ（デフォルト: output）",
    )

    args = parser.parse_args()

    # 設定を読み込み
    config = Config.from_env()
    if args.llm_provider:
        config.llm_provider = args.llm_provider

    logger.info(f"Using LLM provider: {config.llm_provider}")

    # 要件定義書を読み込み
    requirements_path = Path(args.requirements_file)
    if not requirements_path.exists():
        logger.error(f"Requirements file not found: {args.requirements_file}")
        sys.exit(1)

    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements_text = f.read()

    logger.info(f"Loaded requirements from: {args.requirements_file}")
    logger.info(f"Document length: {len(requirements_text)} characters")

    # 出力ディレクトリを作成
    output_dir = Path(__file__).parent / args.output_dir
    output_dir.mkdir(exist_ok=True)

    # LLMクライアントを初期化
    llm_config = config.get_llm_client_config()
    if llm_config.get("provider") == "google_ai":
        import google.generativeai as genai

        genai.configure(api_key=llm_config["api_key"])
        llm_client = genai.GenerativeModel(llm_config["model"])
    else:
        from openai import AsyncOpenAI

        llm_client = AsyncOpenAI(
            api_key=llm_config["api_key"], base_url=llm_config.get("base_url")
        )

    # フェーズA: 構造抽出
    logger.info("\n" + "=" * 80)
    logger.info("フェーズA: 構造抽出")
    logger.info("=" * 80)

    extractor = StructureExtractor(
        llm_client=llm_client, model=llm_config["model"], provider=llm_config["provider"]
    )

    structure_candidates = await extractor.extract_structure(requirements_text)

    # 候補を保存
    candidates_path = output_dir / "structure_candidates.json"
    extractor.save_candidates(structure_candidates, str(candidates_path))

    # フェーズB: スキーママッピング
    logger.info("\n" + "=" * 80)
    logger.info("フェーズB: スキーママッピング")
    logger.info("=" * 80)

    mapper = SchemaMapper()
    mapping = mapper.create_mapping_from_candidates(structure_candidates)

    # マッピングを保存
    mapping_path = output_dir / "schema_mapping.json"
    mapper.save_mapping(str(mapping_path))

    # マッピングサマリーを表示
    mapper.print_mapping_summary()

    # 抽出指示を生成
    extraction_instructions = mapper.generate_extraction_instructions()
    instructions_path = output_dir / "extraction_instructions.txt"
    with open(instructions_path, "w", encoding="utf-8") as f:
        f.write(extraction_instructions)

    logger.info(f"\n抽出指示を保存: {instructions_path}")

    # 完了メッセージ
    print("\n" + "=" * 80)
    print("✅ 構造抽出とスキーママッピングが完了しました")
    print("=" * 80)
    print(f"\n📁 出力ファイル:")
    print(f"  - 構造候補: {candidates_path}")
    print(f"  - スキーママッピング: {mapping_path}")
    print(f"  - 抽出指示: {instructions_path}")
    print(f"\n📝 次のステップ:")
    print(f"  1. {mapping_path} をテキストエディタで開く")
    print(f"  2. 各候補の 'approved' フィールドを確認・編集")
    print(f"     - 承認する候補: 'approved': true")
    print(f"     - 却下する候補: 'approved': false")
    print(f"  3. 必要に応じて name や description を修正")
    print(f"  4. 保存後、graphrag_poc.py を --schema-mapping オプション付きで実行")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
