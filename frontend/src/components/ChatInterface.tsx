"use client";

import React, { useState, useRef, useEffect } from "react";
import { Question } from "@/lib/api";
import { Send, CheckCircle } from "lucide-react";

interface Message {
  type: "question" | "answer" | "system";
  content: string;
  question?: Question;
}

interface ChatInterfaceProps {
  questions: Question[];
  onAnswer: (questionId: string, answer: string) => void;
  isLoading: boolean;
  completionRate: number;
  isRestoredSession?: boolean;
}

export default function ChatInterface({
  questions,
  onAnswer,
  isLoading,
  completionRate,
  isRestoredSession = false,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentAnswer, setCurrentAnswer] = useState("");
  const [displayedQuestionIds, setDisplayedQuestionIds] = useState<Set<string>>(new Set());
  const [isInitialized, setIsInitialized] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 初期化: 復元されたセッションでも通常の初期化のみ実行
  useEffect(() => {
    if (!isInitialized) {
      setIsInitialized(true);
    }
  }, [isInitialized]);

  useEffect(() => {
    if (!isInitialized) return;

    // 配列の最初の未表示の質問を見つけて表示
    const nextQuestion = questions.find(q => !displayedQuestionIds.has(q.id));

    if (nextQuestion) {
      setMessages((prev) => [
        ...prev,
        {
          type: "question",
          content: nextQuestion.question,
          question: nextQuestion,
        },
      ]);

      // 表示済みとしてマーク
      setDisplayedQuestionIds((prev) => new Set(prev).add(nextQuestion.id));
    }
    // displayedQuestionIdsを依存配列から除外して無限ループを防ぐ
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [questions, isInitialized]);

  const handleSubmitAnswer = () => {
    if (!currentAnswer.trim() || isLoading) return;

    // 現在回答すべき質問は、表示済みの質問の中で最初のもの
    const currentQuestion = questions.find(q => displayedQuestionIds.has(q.id));
    if (!currentQuestion) return;

    // 回答をメッセージに追加
    setMessages((prev) => [
      ...prev,
      {
        type: "answer",
        content: currentAnswer,
      },
    ]);

    // APIに回答を送信
    onAnswer(currentQuestion.id, currentAnswer);

    // 入力をクリア
    setCurrentAnswer("");
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case "high":
        return "text-red-600 bg-red-50";
      case "medium":
        return "text-yellow-600 bg-yellow-50";
      case "low":
        return "text-green-600 bg-green-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case "functional":
        return "機能要件";
      case "non_functional":
        return "非機能要件";
      case "constraint":
        return "制約条件";
      default:
        return "その他";
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* ヘッダー */}
      <div className="p-4 border-b bg-white">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">AIとの対話</h2>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">進捗率:</span>
            <span className="font-semibold text-blue-600">
              {Math.round(completionRate)}%
            </span>
          </div>
        </div>
        {/* 進捗バー */}
        <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${completionRate}%` }}
          />
        </div>
      </div>

      {/* メッセージエリア */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            質問が表示されるまでお待ちください...
          </div>
        )}

        {messages.map((message, index) => (
          <div key={index}>
            {message.type === "question" && message.question && (
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-semibold">
                  AI
                </div>
                <div className="flex-1">
                  <div className="bg-white rounded-lg p-4 shadow-sm">
                    <div className="flex gap-2 mb-2">
                      <span
                        className={`text-xs px-2 py-1 rounded ${getPriorityColor(
                          message.question.priority
                        )}`}
                      >
                        優先度: {message.question.priority.toUpperCase()}
                      </span>
                      <span className="text-xs px-2 py-1 rounded bg-blue-50 text-blue-600">
                        {getCategoryLabel(message.question.category)}
                      </span>
                    </div>
                    <p className="text-gray-800">{message.content}</p>
                    {message.question.context && (
                      <p className="text-sm text-gray-500 mt-2">
                        背景: {message.question.context}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {message.type === "answer" && (
              <div className="flex gap-3 justify-end">
                <div className="flex-1 max-w-2xl">
                  <div className="bg-blue-600 text-white rounded-lg p-4 shadow-sm">
                    <p>{message.content}</p>
                  </div>
                </div>
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-300 text-gray-700 flex items-center justify-center font-semibold">
                  You
                </div>
              </div>
            )}

            {message.type === "system" && (
              <div className="flex justify-center">
                <div className="bg-green-50 text-green-800 rounded-lg px-4 py-2 text-sm flex items-center gap-2">
                  <CheckCircle size={16} />
                  {message.content}
                </div>
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-semibold">
              AI
            </div>
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.1s" }}
                />
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 入力エリア */}
      <div className="p-4 border-t bg-white">
        {questions.length > 0 && questions.some(q => displayedQuestionIds.has(q.id)) ? (
          <div className="flex gap-2">
            <input
              type="text"
              value={currentAnswer}
              onChange={(e) => setCurrentAnswer(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmitAnswer();
                }
              }}
              placeholder="回答を入力してください..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
            <button
              onClick={handleSubmitAnswer}
              disabled={!currentAnswer.trim() || isLoading}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Send size={16} />
              送信
            </button>
          </div>
        ) : questions.length === 0 ? (
          <div className="text-center text-green-600 font-semibold">
            全ての質問に回答しました！
          </div>
        ) : (
          <div className="text-center text-gray-500">
            質問が表示されるまでお待ちください...
          </div>
        )}
      </div>
    </div>
  );
}
