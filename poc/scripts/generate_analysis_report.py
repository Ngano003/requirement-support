#!/usr/bin/env python3
"""
分析レポート生成スクリプト

既存のfull_report.jsonから人間が読みやすいマークダウンレポートを生成する
"""

import json
import sys
from pathlib import Path
from analysis_reporter import AnalysisReporter


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("Usage: python generate_analysis_report.py <full_report.json>")
        print("\nExample:")
        print("  python generate_analysis_report.py output/full_report.json")
        sys.exit(1)

    report_file = sys.argv[1]
    report_path = Path(report_file)

    if not report_path.exists():
        print(f"Error: File not found: {report_file}")
        sys.exit(1)

    # JSONレポートを読み込み
    print(f"Loading report from: {report_file}")
    with open(report_path, "r", encoding="utf-8") as f:
        result = json.load(f)

    # マークダウンレポートを生成
    print("Generating markdown analysis report...")
    markdown_report = AnalysisReporter.generate_markdown_report(result)

    # 出力ファイル名を決定
    output_file = report_path.parent / "analysis_report.md"

    # レポートを保存
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown_report)

    print(f"✅ Analysis report saved to: {output_file}")
    print()

    # コンソールにサマリーを表示
    AnalysisReporter.print_console_summary(result)


if __name__ == "__main__":
    main()
