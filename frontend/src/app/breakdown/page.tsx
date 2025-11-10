"use client";

import { useState } from "react";
import { apiClient, Question } from "@/lib/api";
import MarkdownViewer from "@/components/MarkdownViewer";
import ChatInterface from "@/components/ChatInterface";
import { ArrowLeft, Download } from "lucide-react";
import Link from "next/link";

export default function BreakdownPage() {
  const [step, setStep] = useState<"input" | "chat">("input");
  const [sessionId, setSessionId] = useState<string>("");
  const [requirements, setRequirements] = useState<string>("");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [completionRate, setCompletionRate] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [inputText, setInputText] = useState<string>("");

  // 初期化処理
  const handleInitialize = async () => {
    if (!inputText.trim()) {
      alert("打ち合わせの記録を入力してください");
      return;
    }

    setIsLoading(true);

    try {
      const response = await apiClient.initializeBreakdown({
        input_text: inputText,
      });

      setSessionId(response.session_id);
      setRequirements(response.draft_requirements);
      setQuestions(response.questions);
      setCompletionRate(response.completion_rate);
      setStep("chat");
    } catch (error) {
      console.error("初期化エラー:", error);
      alert("初期化に失敗しました: " + (error as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  // 回答処理
  const handleAnswer = async (questionId: string, answer: string) => {
    setIsLoading(true);

    try {
      const response = await apiClient.answerQuestion({
        session_id: sessionId,
        question_id: questionId,
        answer: answer,
      });

      setRequirements(response.updated_requirements);
      setQuestions((prev) => [
        ...prev.filter((q) => q.id !== questionId),
        ...response.new_questions,
      ]);
      setCompletionRate(response.completion_rate);
    } catch (error) {
      console.error("回答処理エラー:", error);
      alert("回答の処理に失敗しました: " + (error as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  // ダウンロード処理
  const handleDownload = () => {
    const blob = new Blob([requirements], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `requirements_${sessionId}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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
            要件定義のブレークダウン
          </h1>
        </div>
        {step === "chat" && (
          <button
            onClick={handleDownload}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            <Download size={16} />
            ダウンロード
          </button>
        )}
      </header>

      {/* メインコンテンツ */}
      {step === "input" ? (
        <div className="flex-1 bg-gray-50 p-8 overflow-y-auto">
          <div className="max-w-4xl mx-auto">
            <div className="bg-white rounded-lg shadow-lg p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                打ち合わせの記録を入力
              </h2>
              <p className="text-gray-600 mb-6">
                議事録や打ち合わせのメモを入力してください。AIが要件定義書のたたき台を自動生成します。
              </p>

              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="例:&#10;&#10;【プロジェクト概要】&#10;社内の業務管理システムを新規開発する。&#10;&#10;【主な機能】&#10;- ユーザー管理&#10;- タスク管理&#10;- レポート出力&#10;&#10;【制約】&#10;- 予算: 500万円&#10;- 納期: 6ヶ月後"
                className="w-full h-96 p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />

              <div className="mt-6 flex justify-end">
                <button
                  onClick={handleInitialize}
                  disabled={isLoading || !inputText.trim()}
                  className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed font-semibold"
                >
                  {isLoading ? "生成中..." : "要件定義を開始"}
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden">
          {/* 左側: 要件定義書プレビュー */}
          <div className="w-1/2 border-r bg-white overflow-hidden flex flex-col">
            <div className="p-4 border-b bg-gray-50">
              <h2 className="font-semibold text-gray-800">要件定義書</h2>
            </div>
            <MarkdownViewer content={requirements} />
          </div>

          {/* 右側: AIチャット */}
          <div className="w-1/2 bg-white overflow-hidden">
            <ChatInterface
              questions={questions}
              onAnswer={handleAnswer}
              isLoading={isLoading}
              completionRate={completionRate}
            />
          </div>
        </div>
      )}
    </div>
  );
}
