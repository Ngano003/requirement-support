"""
分析レポート生成器

検出された問題を人間が読みやすい形式で出力する
"""

from typing import Dict, Any, List
from datetime import datetime


class AnalysisReporter:
    """分析レポート生成器"""

    @staticmethod
    def generate_markdown_report(result: Dict[str, Any]) -> str:
        """
        マークダウン形式のレポートを生成

        Args:
            result: GraphRAG PoCの実行結果

        Returns:
            マークダウン形式のレポート文字列
        """
        lines = []

        # ヘッダー
        lines.append("# 要件定義書 分析レポート")
        lines.append("")
        lines.append(f"**生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
        lines.append(f"**セッションID**: `{result['session_id']}`")
        lines.append("")
        lines.append("---")
        lines.append("")

        # サマリー
        lines.extend(AnalysisReporter._generate_summary(result))

        # 検出された問題の詳細
        lines.extend(AnalysisReporter._generate_issues_details(result))

        # グラフ統計
        lines.extend(AnalysisReporter._generate_graph_stats(result))

        # パフォーマンス
        lines.extend(AnalysisReporter._generate_performance(result))

        # 推奨アクション
        lines.extend(AnalysisReporter._generate_recommendations(result))

        return "\n".join(lines)

    @staticmethod
    def _generate_summary(result: Dict[str, Any]) -> List[str]:
        """サマリーセクションを生成"""
        lines = []
        summary = result["summary"]

        lines.append("## 📊 分析サマリー")
        lines.append("")

        total_issues = summary["total_issues"]
        if total_issues == 0:
            lines.append("✅ **問題は検出されませんでした**")
            lines.append("")
            lines.append("この要件定義書は以下の観点で問題がありません：")
            lines.append("- 利用されない機能")
            lines.append("- セキュリティ要件の漏れ")
            lines.append("- 孤立データ")
            lines.append("- 循環依存")
            lines.append("- 権限の競合")
            lines.append("- データアクセスの矛盾")
        else:
            lines.append(f"⚠️ **合計 {total_issues} 件の問題が検出されました**")
            lines.append("")
            lines.append("| カテゴリ | 件数 |")
            lines.append("|---------|------|")
            lines.append(f"| ヌケモレ | {summary['missing_items_count']} |")
            lines.append(f"| 矛盾 | {summary['contradictions_count']} |")
            lines.append(f"| **合計** | **{total_issues}** |")

        lines.append("")
        lines.append("---")
        lines.append("")
        return lines

    @staticmethod
    def _generate_issues_details(result: Dict[str, Any]) -> List[str]:
        """問題の詳細セクションを生成"""
        lines = []
        detection = result["detection"]

        lines.append("## 🔍 検出された問題の詳細")
        lines.append("")

        # ヌケモレ
        lines.extend(AnalysisReporter._generate_missing_items_section(detection["missing_items"]))

        # 矛盾
        lines.extend(AnalysisReporter._generate_contradictions_section(detection["contradictions"]))

        return lines

    @staticmethod
    def _generate_missing_items_section(missing_items: Dict[str, Any]) -> List[str]:
        """ヌケモレセクションを生成"""
        lines = []
        summary = missing_items["summary"]
        details = missing_items["details"]

        lines.append("### 🔴 ヌケモレ")
        lines.append("")

        total_missing = sum(summary.values())
        if total_missing == 0:
            lines.append("✅ ヌケモレは検出されませんでした。")
            lines.append("")
        else:
            # 1. 利用されない機能
            if summary["unused_functions"] > 0:
                lines.append(f"#### 1. 利用されない機能（{summary['unused_functions']}件）")
                lines.append("")
                lines.append("以下の機能はどのアクターからも利用されていません：")
                lines.append("")
                for item in details["unused_functions"]:
                    lines.append(f"- **{item['function_name']}** (`{item['entity_id']}`)")
                    if item.get("description"):
                        lines.append(f"  - 説明: {item['description']}")
                lines.append("")
                lines.append("**影響**: これらの機能は実装されても使われない可能性があります。")
                lines.append("")

            # 2. セキュリティ要件の漏れ
            if summary["missing_security_requirements"] > 0:
                lines.append(f"#### 2. セキュリティ要件の漏れ（{summary['missing_security_requirements']}件）")
                lines.append("")
                lines.append("以下の機密データにセキュリティ要件が適用されていません：")
                lines.append("")
                for item in details["missing_security_requirements"]:
                    lines.append(f"- **{item['data_name']}** (`{item['entity_id']}`)")
                    if item.get("sensitivity"):
                        lines.append(f"  - 機密性: {item['sensitivity']}")
                lines.append("")
                lines.append("**影響**: データ保護が不十分になる可能性があります。")
                lines.append("")

            # 3. 孤立データ
            if summary["orphan_data"] > 0:
                lines.append(f"#### 3. 孤立データ（{summary['orphan_data']}件）")
                lines.append("")
                lines.append("以下のデータはどの機能からも操作されていません：")
                lines.append("")
                for item in details["orphan_data"]:
                    lines.append(f"- **{item['data_name']}** (`{item['entity_id']}`)")
                lines.append("")
                lines.append("**影響**: これらのデータは使用されない可能性があります。")
                lines.append("")

        lines.append("---")
        lines.append("")
        return lines

    @staticmethod
    def _generate_contradictions_section(contradictions: Dict[str, Any]) -> List[str]:
        """矛盾セクションを生成"""
        lines = []
        summary = contradictions["summary"]
        details = contradictions["details"]

        lines.append("### 🔴 矛盾")
        lines.append("")

        total_contradictions = sum(summary.values())
        if total_contradictions == 0:
            lines.append("✅ 矛盾は検出されませんでした。")
            lines.append("")
        else:
            # 1. 循環依存
            if summary["circular_dependencies"] > 0:
                lines.append(f"#### 1. 循環依存（{summary['circular_dependencies']}件）")
                lines.append("")
                lines.append("以下の機能間で循環依存が発生しています：")
                lines.append("")
                for item in details["circular_dependencies"]:
                    lines.append(f"- **{item['function_name']}** (`{item['entity_id']}`)")
                    cycle = " → ".join(item['cycle_path'])
                    lines.append(f"  - 循環パス: {cycle}")
                lines.append("")
                lines.append("**影響**: 実装順序が決められず、デッドロックの原因になります。")
                lines.append("")

            # 2. 権限の競合
            if summary["permission_conflicts"] > 0:
                lines.append(f"#### 2. 権限の競合（{summary['permission_conflicts']}件）")
                lines.append("")
                lines.append("以下のアクターと機能の組み合わせで権限が競合しています：")
                lines.append("")
                for item in details["permission_conflicts"]:
                    lines.append(f"- **{item['actor_name']}** → **{item['function_name']}**")
                    lines.append(f"  - アクター: `{item['actor_id']}`")
                    lines.append(f"  - 機能: `{item['function_id']}`")
                    lines.append(f"  - 問題: {item['conflict_type']}")
                lines.append("")
                lines.append("**影響**: 同じアクターが同じ機能に対してAllowとDenyの両方を持っています。")
                lines.append("")

            # 3. データアクセスの矛盾
            if summary["data_access_conflicts"] > 0:
                lines.append(f"#### 3. データアクセスの矛盾（{summary['data_access_conflicts']}件）")
                lines.append("")
                lines.append("以下のデータに対して、複数の機能が依存関係なしに書き込みを行っています：")
                lines.append("")

                for idx, item in enumerate(details["data_access_conflicts"], 1):
                    lines.append(f"##### 競合 {idx}: {item['data_name']}")
                    lines.append("")

                    # 基本情報
                    lines.append(f"**データID**: `{item['data_id']}`")
                    lines.append(f"**問題**: {item['issue']}")
                    lines.append("")

                    # 周辺情報がある場合、詳細分析を追加
                    if "context" in item and item["context"]:
                        context = item["context"]

                        # データの詳細
                        lines.append("**📊 データの詳細**")
                        lines.append("")
                        data_info = context.get("data", {})
                        if data_info.get("description"):
                            lines.append(f"- **説明**: {data_info['description']}")
                        if data_info.get("data_type"):
                            lines.append(f"- **データ型**: {data_info['data_type']}")
                        if data_info.get("sensitivity"):
                            lines.append(f"- **機密性レベル**: {data_info['sensitivity']}")
                        if data_info.get("storage_location"):
                            lines.append(f"- **保存先**: {data_info['storage_location']}")
                        if data_info.get("security_requirements"):
                            lines.append(f"- **セキュリティ要件**: {', '.join(data_info['security_requirements']) if data_info['security_requirements'] else 'なし'}")
                        lines.append("")

                        # 機能1の詳細
                        lines.append(f"**🔧 機能1: {item['function1']}** (`{item['function1_id']}`)")
                        lines.append("")
                        func1_info = context.get("function1", {})
                        if func1_info.get("description"):
                            lines.append(f"- **説明**: {func1_info['description']}")
                        if func1_info.get("actors"):
                            lines.append(f"- **利用者**: {', '.join(func1_info['actors']) if func1_info['actors'] else 'なし'}")
                        if func1_info.get("data_operations"):
                            ops = [f"{op['data']} ({op['action']})" for op in func1_info['data_operations'] if op.get('data')]
                            if ops:
                                lines.append(f"- **データ操作**: {', '.join(ops)}")
                        lines.append("")

                        # 機能2の詳細
                        lines.append(f"**🔧 機能2: {item['function2']}** (`{item['function2_id']}`)")
                        lines.append("")
                        func2_info = context.get("function2", {})
                        if func2_info.get("description"):
                            lines.append(f"- **説明**: {func2_info['description']}")
                        if func2_info.get("actors"):
                            lines.append(f"- **利用者**: {', '.join(func2_info['actors']) if func2_info['actors'] else 'なし'}")
                        if func2_info.get("data_operations"):
                            ops = [f"{op['data']} ({op['action']})" for op in func2_info['data_operations'] if op.get('data')]
                            if ops:
                                lines.append(f"- **データ操作**: {', '.join(ops)}")
                        lines.append("")

                        # 競合分析
                        lines.append("**⚠️ 競合の分析**")
                        lines.append("")

                        # 保存先が同じか確認
                        if data_info.get("storage_location"):
                            lines.append(f"- 両機能が同じストレージ（{data_info['storage_location']}）に書き込みを行います")
                        else:
                            lines.append("- 両機能が同じデータに書き込みを行います")

                        # 利用者の重複確認
                        func1_actors = set(func1_info.get("actors", []))
                        func2_actors = set(func2_info.get("actors", []))
                        common_actors = func1_actors & func2_actors
                        if common_actors:
                            lines.append(f"- 共通の利用者（{', '.join(common_actors)}）が両機能を使用可能です")
                        else:
                            lines.append("- 異なる利用者が各機能を使用します")

                        # セキュリティ要件の確認
                        if data_info.get("security_requirements"):
                            lines.append(f"- セキュリティ要件が設定されていますが、並行書き込みの制御は明記されていません")
                        else:
                            lines.append("- セキュリティ要件が未設定です")

                        lines.append("")

                        # リスク評価
                        lines.append("**🚨 想定されるリスク**")
                        lines.append("")
                        lines.append("1. **データ不整合**: 同時に更新が発生した場合、片方の変更が失われる可能性")
                        lines.append("2. **整合性違反**: トランザクション境界が不明確で、中間状態が読み取られる可能性")

                        if common_actors:
                            lines.append("3. **ユーザー体験の低下**: 同じユーザーの操作結果が予期しない形で上書きされる可能性")

                        if data_info.get("sensitivity") in ["high", "confidential"]:
                            lines.append("4. **セキュリティリスク**: 機密データの整合性が損なわれる可能性")

                        lines.append("")
                    else:
                        # 周辺情報がない場合（従来の表示）
                        lines.append(f"- **機能1**: {item['function1']} (`{item['function1_id']}`)")
                        lines.append(f"- **機能2**: {item['function2']} (`{item['function2_id']}`)")
                        lines.append("")

                lines.append("**💡 推奨対処**")
                lines.append("")
                lines.append("1. **依存関係の明確化**: 一方の機能が他方に依存する場合、DEPENDS_ON関係を追加")
                lines.append("2. **トランザクション制御**: ACID特性を満たすトランザクション境界を要件に明記")
                lines.append("3. **排他制御**: 楽観的ロック（バージョン番号）または悲観的ロック（行ロック）の採用")
                lines.append("4. **イベントソーシング**: 更新ではなく追記型のデータモデルへの変更を検討")
                lines.append("5. **並行性制御の要件追加**: 同時書き込み時の動作（エラー、待機、マージ）を明確化")
                lines.append("")

        lines.append("---")
        lines.append("")
        return lines

    @staticmethod
    def _generate_graph_stats(result: Dict[str, Any]) -> List[str]:
        """グラフ統計セクションを生成"""
        lines = []
        graph = result["graph"]

        lines.append("## 📈 グラフ統計")
        lines.append("")
        lines.append(f"- **ノード数**: {graph['node_count']}")
        lines.append(f"- **エッジ数**: {graph['edge_count']}")
        lines.append("")
        lines.append("### ノードタイプの内訳")
        lines.append("")
        for node_type, count in graph["node_types"].items():
            lines.append(f"- {node_type}: {count}")
        lines.append("")
        lines.append("---")
        lines.append("")
        return lines

    @staticmethod
    def _generate_performance(result: Dict[str, Any]) -> List[str]:
        """パフォーマンスセクションを生成"""
        lines = []
        perf = result["performance"]

        lines.append("## ⏱️ パフォーマンス")
        lines.append("")
        lines.append(f"- **総処理時間**: {perf['total_time_seconds']}秒")
        lines.append(f"  - エンティティ抽出: {perf['extraction_time_seconds']}秒")
        lines.append(f"  - グラフ構築: {perf['build_time_seconds']}秒")
        lines.append(f"  - 問題検出: {perf['detection_time_seconds']}秒")
        lines.append("")
        lines.append("---")
        lines.append("")
        return lines

    @staticmethod
    def _generate_recommendations(result: Dict[str, Any]) -> List[str]:
        """推奨アクションセクションを生成"""
        lines = []
        summary = result["summary"]

        lines.append("## 💡 推奨アクション")
        lines.append("")

        if summary["total_issues"] == 0:
            lines.append("✅ 要件定義書は良好な状態です。以下の点を確認してください：")
            lines.append("")
            lines.append("1. すべての機能が適切なアクターに紐付いている")
            lines.append("2. 機密データにセキュリティ要件が適用されている")
            lines.append("3. すべてのデータが適切な機能で操作されている")
            lines.append("4. 機能間の依存関係に循環がない")
            lines.append("5. 権限設定に矛盾がない")
            lines.append("6. データアクセスに競合がない")
        else:
            detection = result["detection"]
            missing = detection["missing_items"]["summary"]
            contradictions = detection["contradictions"]["summary"]

            lines.append("以下の問題を優先的に対処してください：")
            lines.append("")

            priority = 1

            # 矛盾を優先
            if contradictions["circular_dependencies"] > 0:
                lines.append(f"{priority}. **循環依存の解消** - 実装順序を決められない問題を解決")
                priority += 1

            if contradictions["permission_conflicts"] > 0:
                lines.append(f"{priority}. **権限の競合の解消** - Allow/Denyの矛盾を修正")
                priority += 1

            if contradictions["data_access_conflicts"] > 0:
                lines.append(f"{priority}. **データアクセス競合の解消** - トランザクション制御や排他制御を追加")
                priority += 1

            # ヌケモレ
            if missing["missing_security_requirements"] > 0:
                lines.append(f"{priority}. **セキュリティ要件の追加** - 機密データの保護を明記")
                priority += 1

            if missing["unused_functions"] > 0:
                lines.append(f"{priority}. **未使用機能の確認** - 本当に必要か再検討")
                priority += 1

            if missing["orphan_data"] > 0:
                lines.append(f"{priority}. **孤立データの確認** - どの機能で使用するか明確化")
                priority += 1

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*このレポートはGraphRAG PoCによって自動生成されました*")
        lines.append("")

        return lines

    @staticmethod
    def print_console_summary(result: Dict[str, Any]):
        """コンソールにサマリーを出力"""
        print("\n" + "=" * 80)
        print("📊 分析結果サマリー")
        print("=" * 80)

        summary = result["summary"]
        total_issues = summary["total_issues"]

        if total_issues == 0:
            print("✅ 問題は検出されませんでした")
        else:
            print(f"⚠️  合計 {total_issues} 件の問題が検出されました")
            print(f"   - ヌケモレ: {summary['missing_items_count']}件")
            print(f"   - 矛盾: {summary['contradictions_count']}件")

            # 詳細
            detection = result["detection"]
            missing = detection["missing_items"]["summary"]
            contradictions = detection["contradictions"]["summary"]

            if summary["missing_items_count"] > 0:
                print("\n  【ヌケモレの内訳】")
                if missing["unused_functions"] > 0:
                    print(f"    - 利用されない機能: {missing['unused_functions']}件")
                if missing["missing_security_requirements"] > 0:
                    print(f"    - セキュリティ要件の漏れ: {missing['missing_security_requirements']}件")
                if missing["orphan_data"] > 0:
                    print(f"    - 孤立データ: {missing['orphan_data']}件")

            if summary["contradictions_count"] > 0:
                print("\n  【矛盾の内訳】")
                if contradictions["circular_dependencies"] > 0:
                    print(f"    - 循環依存: {contradictions['circular_dependencies']}件")
                if contradictions["permission_conflicts"] > 0:
                    print(f"    - 権限の競合: {contradictions['permission_conflicts']}件")
                if contradictions["data_access_conflicts"] > 0:
                    print(f"    - データアクセスの矛盾: {contradictions['data_access_conflicts']}件")

        print("\n⏱️  処理時間: {:.2f}秒".format(result["performance"]["total_time_seconds"]))
        print("=" * 80)
