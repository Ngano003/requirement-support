#!/usr/bin/env python3
"""
セットアップ検証スクリプト

GraphRAG PoCの実行に必要な環境をチェックします
"""

import sys
import os


def check_python_version():
    """Python バージョンチェック"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"   ❌ Python 3.8+ required, found {version.major}.{version.minor}.{version.micro}")
        return False


def check_dependencies():
    """依存パッケージチェック"""
    print("\n📦 Checking dependencies...")
    required = ["openai", "google.generativeai", "neo4j", "pydantic"]
    all_ok = True

    for package in required:
        try:
            if package == "google.generativeai":
                import google.generativeai
                print(f"   ✅ google-generativeai")
            else:
                __import__(package)
                print(f"   ✅ {package}")
        except ImportError:
            display_name = "google-generativeai" if package == "google.generativeai" else package
            print(f"   ❌ {display_name} not found")
            all_ok = False

    if not all_ok:
        print("\n   Install missing packages:")
        print("   pip install -r requirements.txt")

    return all_ok


def check_environment_variables():
    """環境変数チェック"""
    print("\n🔐 Checking environment variables...")

    llm_provider = os.getenv("LLM_PROVIDER", "google_ai")
    print(f"   LLM Provider: {llm_provider}")

    if llm_provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            print(f"   ✅ OPENROUTER_API_KEY is set")
            return True
        else:
            print(f"   ⚠️  OPENROUTER_API_KEY not set")
            return False
    elif llm_provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            print(f"   ✅ OPENAI_API_KEY is set")
            return True
        else:
            print(f"   ❌ OPENAI_API_KEY not set")
            return False
    elif llm_provider == "google_ai":
        api_key = os.getenv("GOOGLE_AI_API_KEY")
        if api_key:
            print(f"   ✅ GOOGLE_AI_API_KEY is set")
            model = os.getenv("GOOGLE_AI_MODEL", "gemini-1.5-flash")
            print(f"   ✅ GOOGLE_AI_MODEL: {model}")
            return True
        else:
            print(f"   ❌ GOOGLE_AI_API_KEY not set")
            print(f"   Get your API key from: https://aistudio.google.com/app/apikey")
            return False
    elif llm_provider == "vllm":
        api_base = os.getenv("VLLM_API_BASE", "http://localhost:8000/v1")
        print(f"   ✅ VLLM_API_BASE: {api_base}")
        return True
    else:
        print(f"   ❌ Unknown LLM provider: {llm_provider}")
        return False


def check_files():
    """必要なファイルチェック"""
    print("\n📄 Checking required files...")

    script_dir = os.path.dirname(__file__)
    required_files = [
        "graphrag_poc.py",
        "config.py",
        "entity_extractor.py",
        "graph_builder.py",
        "problem_detector.py",
        "samples/sample_requirements_1.md",
        "samples/sample_requirements_2.md",
        "samples/sample_requirements_3.md",
    ]

    all_ok = True
    for file in required_files:
        path = os.path.join(script_dir, file)
        if os.path.exists(path):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} not found")
            all_ok = False

    return all_ok


def check_backend_app():
    """バックエンドappディレクトリのチェック"""
    print("\n🔍 Checking backend app modules...")

    script_dir = os.path.dirname(__file__)
    poc_scripts_dir = script_dir
    poc_dir = os.path.dirname(poc_scripts_dir)  # scripts -> poc
    project_root = os.path.dirname(poc_dir)  # poc -> requirement-support
    backend_dir = os.path.join(project_root, 'backend')

    if os.path.exists(backend_dir):
        sys.path.insert(0, backend_dir)
    else:
        # backend/scriptsから実行される場合
        parent_dir = os.path.dirname(script_dir)
        sys.path.insert(0, parent_dir)

    try:
        from app.schemas.knowledge_graph_schema import ENTITY_TYPES, RELATION_TYPES
        print(f"   ✅ knowledge_graph_schema.py ({len(ENTITY_TYPES)} entities, {len(RELATION_TYPES)} relations)")

        from app.prompts.entity_extraction_prompt import build_entity_extraction_prompt
        print(f"   ✅ entity_extraction_prompt.py")

        return True
    except ImportError as e:
        print(f"   ❌ Failed to import backend modules: {e}")
        print(f"   Make sure backend/app directory exists")
        return False


def check_memgraph_connection():
    """Memgraph接続チェック（オプショナル）"""
    print("\n🗄️  Checking Memgraph connection (optional)...")

    try:
        from neo4j import GraphDatabase

        host = os.getenv("MEMGRAPH_HOST", "localhost")
        port = int(os.getenv("MEMGRAPH_PORT", "7687"))
        uri = f"bolt://{host}:{port}"

        driver = GraphDatabase.driver(uri)

        with driver.session() as session:
            result = session.run("RETURN 1 AS test")
            result.consume()

        driver.close()
        print(f"   ✅ Memgraph connected at {uri}")
        return True
    except Exception as e:
        print(f"   ⚠️  Memgraph not available: {e}")
        print(f"   Start Memgraph with: docker run -d -p 7687:7687 memgraph/memgraph-platform")
        return False


def main():
    """メイン関数"""
    print("=" * 80)
    print("GraphRAG PoC セットアップ検証")
    print("=" * 80)

    checks = [
        ("Python version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment variables", check_environment_variables),
        ("Required files", check_files),
        ("Backend app modules", check_backend_app),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n   ❌ Error during {name} check: {e}")
            results.append((name, False))

    # Memgraph check is optional
    print("\n" + "-" * 80)
    check_memgraph_connection()

    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)

    all_passed = all(result for _, result in results)

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    if all_passed:
        print("\n✅ All checks passed! Ready to run GraphRAG PoC.")
        print("\nRun the PoC with:")
        print("  python3 graphrag_poc.py samples/sample_requirements_1.md")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
