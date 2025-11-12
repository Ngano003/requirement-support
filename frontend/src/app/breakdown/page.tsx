"use client";

import { useState, useEffect } from "react";
import { apiClient, Question } from "@/lib/api";
import MarkdownViewer from "@/components/MarkdownViewer";
import ChatInterface from "@/components/ChatInterface";
import { ArrowLeft, Download, RefreshCw } from "lucide-react";
import Link from "next/link";

const STORAGE_KEY = "breakdown_session";

interface SessionState {
  sessionId: string;
  step: "input" | "chat";
  inputText: string;
}

export default function BreakdownPage() {
  const [step, setStep] = useState<"input" | "chat">("input");
  const [sessionId, setSessionId] = useState<string>("");
  const [requirements, setRequirements] = useState<string>("");
  const [questions, setQuestions] = useState<Question[]>([]);
  const [completionRate, setCompletionRate] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [inputText, setInputText] = useState<string>("");
  const [isRestoring, setIsRestoring] = useState<boolean>(true);
  const [isRestoredSession, setIsRestoredSession] = useState<boolean>(false);
  const [answeredCount, setAnsweredCount] = useState<number>(0);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [followUpQuestion, setFollowUpQuestion] = useState<string | null>(null);
  const [systemMessage, setSystemMessage] = useState<string | null>(null);
  const [updateSummary, setUpdateSummary] = useState<string | null>(null);
  const [nextQuestionsMessage, setNextQuestionsMessage] = useState<string | null>(null);

  // ページロード時にセッションを復元
  useEffect(() => {
    const restoreSession = async () => {
      try {
        const savedState = localStorage.getItem(STORAGE_KEY);
        if (savedState) {
          const state: SessionState = JSON.parse(savedState);

          if (state.sessionId && state.step === "chat") {
            // バックエンドからセッション状態を取得
            const status = await apiClient.getBreakdownStatus(state.sessionId);

            setSessionId(state.sessionId);
            setRequirements(status.requirements);
            setQuestions(status.remaining_questions);
            setCompletionRate(status.completion_rate);
            setStep("chat");
            setIsRestoredSession(true); // 復元されたセッションとしてマーク
          } else if (state.inputText) {
            // 入力テキストだけ復元
            setInputText(state.inputText);
          }
        }
      } catch (error) {
        console.error("セッション復元エラー:", error);
        // エラーの場合はストレージをクリア
        localStorage.removeItem(STORAGE_KEY);
      } finally {
        setIsRestoring(false);
      }
    };

    restoreSession();
  }, []);

  // セッション状態を保存
  useEffect(() => {
    if (!isRestoring) {
      const state: SessionState = {
        sessionId,
        step,
        inputText,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
  }, [sessionId, step, inputText, isRestoring]);

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
      setAnsweredCount(response.answered_count);
      setTotalCount(response.total_count);
      if (response.system_message) {
        setSystemMessage(response.system_message);
      }
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

      // 回答が受け入れられなかった場合（不十分な回答）
      if (!response.answer_accepted && response.follow_up_question) {
        // 追加質問をチャット欄に表示
        setFollowUpQuestion(response.follow_up_question);
        setIsLoading(false);
        return;
      }

      // 回答が受け入れられた場合、追加質問をクリア
      setFollowUpQuestion(null);

      // 回答が受け入れられた場合、質問をローカルで削除
      setQuestions((prev) => prev.filter((q) => q.id !== questionId));
      setAnsweredCount((prev) => prev + 1);

      // 全質問に回答した場合、要件定義書が更新される
      if (response.all_answered) {
        // 1. システムメッセージ表示（更新開始）
        if (response.system_message) {
          setSystemMessage(response.system_message);
        }

        setIsUpdating(true);

        // 要件定義書を更新（バックグラウンド）
        setRequirements(response.updated_requirements);

        // 2. 更新要点を2秒後に表示（AIが処理している感じ）
        setTimeout(() => {
          setIsUpdating(false);
          if (response.update_summary) {
            setUpdateSummary(response.update_summary);
          }

          // 3. 次の質問についてのメッセージを2秒後に表示
          setTimeout(() => {
            // 新しい質問を追加
            setQuestions(response.new_questions);
            // カウンターをリセット
            setAnsweredCount(0);
            setTotalCount(response.new_questions.length);

            if (response.next_questions_message) {
              setNextQuestionsMessage(response.next_questions_message);
            }
          }, 2000);
        }, 2000);
      }

      setCompletionRate(response.completion_rate);
      // バックエンドから返ってきた値でも更新
      setAnsweredCount(response.answered_count);
      setTotalCount(response.total_count);
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

  // 新規セッション開始
  const handleNewSession = () => {
    if (confirm("新しいセッションを開始しますか？現在の進行状況は保存されません。")) {
      localStorage.removeItem(STORAGE_KEY);
      setStep("input");
      setSessionId("");
      setRequirements("");
      setQuestions([]);
      setCompletionRate(0);
      setInputText("");
      setIsRestoredSession(false);
      setAnsweredCount(0);
      setTotalCount(0);
      setIsUpdating(false);
      setFollowUpQuestion(null);
      setSystemMessage(null);
      setUpdateSummary(null);
      setNextQuestionsMessage(null);
    }
  };

  // 復元中の表示
  if (isRestoring) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">セッションを復元中...</p>
        </div>
      </div>
    );
  }

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
        <div className="flex items-center gap-2">
          {step === "chat" && (
            <>
              <button
                onClick={handleDownload}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Download size={16} />
                ダウンロード
              </button>
              <button
                onClick={handleNewSession}
                className="flex items-center gap-2 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                <RefreshCw size={16} />
                新規セッション
              </button>
            </>
          )}
        </div>
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
              isRestoredSession={isRestoredSession}
              answeredCount={answeredCount}
              totalCount={totalCount}
              isUpdating={isUpdating}
              followUpQuestion={followUpQuestion}
              systemMessage={systemMessage}
              updateSummary={updateSummary}
              nextQuestionsMessage={nextQuestionsMessage}
            />
          </div>
        </div>
      )}
    </div>
  );
}
