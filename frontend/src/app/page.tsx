"use client";

import Link from "next/link";
import { FileText, Search } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-16">
        {/* ヘッダー */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-800 mb-4">
            要件定義書支援AI
          </h1>
          <p className="text-xl text-gray-600">
            AIが要件定義作業を強力にサポート
          </p>
        </div>

        {/* 機能選択カード */}
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {/* ブレークダウン機能 */}
          <Link href="/breakdown">
            <div className="bg-white rounded-xl shadow-lg p-8 hover:shadow-2xl transition-shadow cursor-pointer border-2 border-transparent hover:border-blue-500">
              <div className="flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-6 mx-auto">
                <FileText className="w-8 h-8 text-blue-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 mb-4 text-center">
                要件定義のブレークダウン
              </h2>
              <p className="text-gray-600 mb-4">
                打ち合わせの記録から要件定義書のたたき台を自動生成し、AIとの対話で要件を深掘りします。
              </p>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-start">
                  <span className="text-blue-600 mr-2">✓</span>
                  議事録から自動でたたき台を生成
                </li>
                <li className="flex items-start">
                  <span className="text-blue-600 mr-2">✓</span>
                  AIが質問を生成し、対話形式で要件を洗い出し
                </li>
                <li className="flex items-start">
                  <span className="text-blue-600 mr-2">✓</span>
                  リアルタイムで要件定義書が更新
                </li>
              </ul>
              <div className="mt-6 text-center">
                <span className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold">
                  開始する →
                </span>
              </div>
            </div>
          </Link>

          {/* レビュー機能 */}
          <Link href="/review">
            <div className="bg-white rounded-xl shadow-lg p-8 hover:shadow-2xl transition-shadow cursor-pointer border-2 border-transparent hover:border-green-500">
              <div className="flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-6 mx-auto">
                <Search className="w-8 h-8 text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-800 mb-4 text-center">
                要件定義書のレビュー
              </h2>
              <p className="text-gray-600 mb-4">
                完成した要件定義書を分析し、漏れ・矛盾・曖昧な表現を自動で指摘します。
              </p>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-start">
                  <span className="text-green-600 mr-2">✓</span>
                  必須項目の漏れをチェック
                </li>
                <li className="flex items-start">
                  <span className="text-green-600 mr-2">✓</span>
                  機能間の矛盾を検出
                </li>
                <li className="flex items-start">
                  <span className="text-green-600 mr-2">✓</span>
                  改善提案を自動生成
                </li>
              </ul>
              <div className="mt-6 text-center">
                <span className="inline-block bg-green-600 text-white px-6 py-2 rounded-lg font-semibold">
                  開始する →
                </span>
              </div>
            </div>
          </Link>
        </div>

        {/* フッター */}
        <div className="text-center mt-16 text-gray-600">
          <p className="text-sm">
            Powered by vLLM + Qwen3-Coder
          </p>
        </div>
      </div>
    </div>
  );
}
