"""
強化版レビューAPIの実APIテスト（手動実行用）
"""
import asyncio
import httpx


async def test_enhanced_review_api():
    """強化版レビューAPIをテスト"""

    # サンプル要件定義書（意図的に抜け漏れと矛盾を含む）
    sample_requirements = """# システム概要
予約管理システム

## 目的
ユーザーが予約を管理できるシステムを構築する

## 対象ユーザー
- 一般利用者
- 管理者

## 機能要件

### ログイン機能
ユーザーがログインできる

### 書籍検索機能
書籍を検索できる
- タイトルで検索
- 著者で検索

### ユーザー情報表示
利用者の情報を表示する
"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8010/api/review/enhanced",
            json={"requirements_text": sample_requirements},
            timeout=60.0,
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("\n=== レビュー結果 ===")
            print(f"Review ID: {result['review_id']}")

            print("\n--- サマリー ---")
            summary = result['summary']
            print(f"抜け漏れ総数: {summary['total_missing_items']}")
            print(f"矛盾総数: {summary['total_contradictions']}")
            print(f"重大度High: {summary['high_severity_count']}")
            print(f"重大度Medium: {summary['medium_severity_count']}")
            print(f"重大度Low: {summary['low_severity_count']}")
            print(f"全体評価: {summary['overall_assessment']}")

            print("\n--- 抜け漏れ検出結果 ---")
            missing = result['missing_items']

            if missing['missing_sections']:
                print("\n欠落セクション:")
                for item in missing['missing_sections']:
                    print(f"  - [{item['severity'].upper()}] {item['section']}")
                    print(f"    説明: {item['description']}")
                    print(f"    提案: {item['suggestion']}")

            if missing['missing_functional_items']:
                print("\n機能要件の記載不足:")
                for item in missing['missing_functional_items']:
                    print(f"  - [{item['severity'].upper()}] {item['function_name']}")
                    print(f"    不足項目: {', '.join(item['missing_items'])}")
                    print(f"    提案: {item['suggestion']}")

            if missing['missing_non_functional_categories']:
                print("\n非機能要件の欠落:")
                for item in missing['missing_non_functional_categories']:
                    print(f"  - [{item['severity'].upper()}] {item['category']}")
                    print(f"    説明: {item['description']}")
                    print(f"    提案: {item['suggestion']}")

            if missing['implicit_missing']:
                print("\n暗黙的な抜け漏れ:")
                for item in missing['implicit_missing']:
                    print(f"  - [{item['severity'].upper()}] {item['item']}")
                    print(f"    理由: {item['reason']}")
                    print(f"    提案: {item['suggestion']}")

            print("\n--- 矛盾検出結果 ---")
            contradictions = result['contradictions']

            if contradictions['cross_section_contradictions']:
                print("\nセクション間の矛盾:")
                for item in contradictions['cross_section_contradictions']:
                    print(f"  - [{item['severity'].upper()}] {item['type']}")
                    print(f"    セクション: {', '.join(item['sections'])}")
                    print(f"    説明: {item['description']}")
                    print(f"    証拠:")
                    print(f"      セクション1: {item['evidence']['section1_statement']}")
                    print(f"      セクション2: {item['evidence']['section2_statement']}")
                    print(f"    提案: {item['suggestion']}")

            if contradictions['terminology_inconsistencies']:
                print("\n用語の不統一:")
                for item in contradictions['terminology_inconsistencies']:
                    print(f"  - [{item['severity'].upper()}] {item['concept']}")
                    print(f"    バリエーション: {', '.join(item['variations'])}")
                    print(f"    使用箇所: {', '.join(item['locations'])}")
                    print(f"    推奨用語: {item['recommended_term']}")

            if contradictions['logical_contradictions']:
                print("\n論理的矛盾:")
                for item in contradictions['logical_contradictions']:
                    print(f"  - [{item['severity'].upper()}] {item['contradiction_type']}")
                    print(f"    矛盾する要件: {', '.join(item['requirements'])}")
                    print(f"    説明: {item['description']}")
                    print(f"    提案: {item['suggestion']}")

            print("\n=== テスト成功 ===")
        else:
            print(f"Error: {response.text}")


if __name__ == "__main__":
    print("強化版レビューAPIのテストを開始...")
    print("注意: バックエンドサーバーが起動していて、LLM_PROVIDER環境変数が設定されている必要があります")
    print("")
    asyncio.run(test_enhanced_review_api())
