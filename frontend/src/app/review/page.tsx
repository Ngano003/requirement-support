"use client";

import { useState } from "react";
import { apiClient, ReviewIssue } from "@/lib/api";
import { ArrowLeft, AlertCircle, CheckCircle2, Info } from "lucide-react";
import Link from "next/link";

export default function ReviewPage() {
  const [step, setStep] = useState<"input" | "result">("input");
  const [inputText, setInputText] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [reviewId, setReviewId] = useState<string>("");
  const [issues, setIssues] = useState<ReviewIssue[]>([]);
  const [scores, setScores] = useState({
    completeness: 0,
    consistency: 0,
    quality: 0,
  });
  const [summary, setSummary] = useState<string>("");
  const [filterSeverity, setFilterSeverity] = useState<string>("all");
  const [filterCategory, setFilterCategory] = useState<string>("all");

  // レビュー実行
  const handleReview = async () => {
    if (!inputText.trim()) {
      alert("要件定義書を入力してください");
      return;
    }

    setIsLoading(true);

    try {
      const response = await apiClient.reviewRequirements({
        requirements_text: inputText,
      });

      setReviewId(response.review_id);
      setIssues(response.issues);
      setScores({
        completeness: response.completeness_score,
        consistency: response.consistency_score,
        quality: response.quality_score,
      });
      setSummary(response.summary);
      setStep("result");
    } catch (error) {
      console.error("レビューエラー:", error);
      alert("レビューに失敗しました: " + (error as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  // フィルタリングされた指摘事項
  const filteredIssues = issues.filter((issue) => {
    if (filterSeverity !== "all" && issue.severity !== filterSeverity) {
      return false;
    }
    if (filterCategory !== "all" && issue.category !== filterCategory) {
      return false;
    }
    return true;
  });

  // 重大度アイコン
  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "high":
        return <AlertCircle className="text-red-600" size={20} />;
      case "medium":
        return <Info className="text-yellow-600" size={20} />;
      case "low":
        return <CheckCircle2 className="text-green-600" size={20} />;
      default:
        return null;
    }
  };

  // 重大度ラベル
  const getSeverityLabel = (severity: string) => {
    switch (severity) {
      case "high":
        return "高";
      case "medium":
        return "中";
      case "low":
        return "低";
      default:
        return severity;
    }
  };

  // カテゴリラベル
  const getCategoryLabel = (category: string) => {
    switch (category) {
      case "missing":
        return "漏れ";
      case "inconsistency":
        return "矛盾";
      case "ambiguity":
        return "曖昧";
      case "quality":
        return "品質";
      default:
        return category;
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {/* ヘッダー */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-gray-600 hover:text-gray-800"
          >
            <ArrowLeft size={20} />
            戻る
          </Link>
          <h1 className="text-xl font-bold text-gray-800">
            要件定義書のレビュー
          </h1>
        </div>
      </header>

      {/* メインコンテンツ */}
      {step === "input" ? (
        <div className="flex-1 bg-gray-50 p-8 overflow-y-auto">
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-lg shadow-lg p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                要件定義書を入力
              </h2>
              <p className="text-gray-600 mb-6">
                レビューしたい要件定義書を入力してください。AIが漏れ・矛盾・曖昧な表現を自動で指摘します。
              </p>

              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="要件定義書（マークダウン形式）を入力..."
                className="w-full h-96 p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 font-mono text-sm"
              />

              <div className="mt-6 flex justify-end">
                <button
                  onClick={handleReview}
                  disabled={isLoading || !inputText.trim()}
                  className="px-8 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-semibold"
                >
                  {isLoading ? "レビュー中..." : "レビュー開始"}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 bg-gray-50 p-8 overflow-y-auto">
          <div className="max-w-6xl mx-auto">
            {/* スコア表示 */}
            <div className="grid md:grid-cols-3 gap-4 mb-8">
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm text-gray-600 mb-2">完全性スコア</h3>
                <div className="text-3xl font-bold text-blue-600">
                  {Math.round(scores.completeness)}
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full"
                    style={{ width: `${scores.completeness}%` }}
                  />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm text-gray-600 mb-2">整合性スコア</h3>
                <div className="text-3xl font-bold text-green-600">
                  {Math.round(scores.consistency)}
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full"
                    style={{ width: `${scores.consistency}%` }}
                  />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-sm text-gray-600 mb-2">品質スコア</h3>
                <div className="text-3xl font-bold text-purple-600">
                  {Math.round(scores.quality)}
                </div>
                <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-purple-600 h-2 rounded-full"
                    style={{ width: `${scores.quality}%` }}
                  />
                </div>
              </div>
            </div>

            {/* サマリー */}
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-800 mb-2">
                総評
              </h3>
              <p className="text-gray-700">{summary}</p>
            </div>

            {/* フィルター */}
            <div className="bg-white rounded-lg shadow p-6 mb-4">
              <div className="flex gap-4">
                <div>
                  <label className="text-sm text-gray-600 mb-1 block">
                    重大度
                  </label>
                  <select
                    value={filterSeverity}
                    onChange={(e) => setFilterSeverity(e.target.value)}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value="all">すべて</option>
                    <option value="high">高</option>
                    <option value="medium">中</option>
                    <option value="low">低</option>
                  </select>
                </div>

                <div>
                  <label className="text-sm text-gray-600 mb-1 block">
                    カテゴリ
                  </label>
                  <select
                    value={filterCategory}
                    onChange={(e) => setFilterCategory(e.target.value)}
                    className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value="all">すべて</option>
                    <option value="missing">漏れ</option>
                    <option value="inconsistency">矛盾</option>
                    <option value="ambiguity">曖昧</option>
                    <option value="quality">品質</option>
                  </select>
                </div>

                <div className="flex-1"></div>

                <div className="flex items-end">
                  <span className="text-sm text-gray-600">
                    指摘事項: {filteredIssues.length}件
                  </span>
                </div>
              </div>
            </div>

            {/* 指摘事項リスト */}
            <div className="space-y-4">
              {filteredIssues.length === 0 ? (
                <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                  指摘事項はありません
                </div>
              ) : (
                filteredIssues.map((issue, index) => (
                  <div key={index} className="bg-white rounded-lg shadow p-6">
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 mt-1">
                        {getSeverityIcon(issue.severity)}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span
                            className={`text-xs px-2 py-1 rounded font-semibold ${
                              issue.severity === "high"
                                ? "bg-red-100 text-red-700"
                                : issue.severity === "medium"
                                ? "bg-yellow-100 text-yellow-700"
                                : "bg-green-100 text-green-700"
                            }`}
                          >
                            {getSeverityLabel(issue.severity)}
                          </span>
                          <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">
                            {getCategoryLabel(issue.category)}
                          </span>
                          <span className="text-sm text-gray-600">
                            {issue.section}
                          </span>
                          {issue.line && (
                            <span className="text-sm text-gray-500">
                              (行: {issue.line})
                            </span>
                          )}
                        </div>
                        <h4 className="font-semibold text-gray-800 mb-2">
                          {issue.description}
                        </h4>
                        <div className="bg-blue-50 border-l-4 border-blue-500 p-3 rounded">
                          <p className="text-sm text-gray-700">
                            <span className="font-semibold">改善提案: </span>
                            {issue.suggestion}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* 戻るボタン */}
            <div className="mt-8 flex justify-center">
              <button
                onClick={() => {
                  setStep("input");
                  setInputText("");
                }}
                className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
              >
                新しい要件定義書をレビュー
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
