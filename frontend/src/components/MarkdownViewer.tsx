"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";

interface MarkdownViewerProps {
  content: string;
}

export default function MarkdownViewer({ content }: MarkdownViewerProps) {
  return (
    <div className="h-full overflow-y-auto bg-white">
      <div className="prose prose-slate max-w-none p-6 lg:prose-lg">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeRaw]}
          components={{
            // カスタムスタイリング
            h1: ({ node, ...props }) => (
              <h1 className="text-3xl font-bold mt-8 mb-4 text-gray-900 border-b-2 border-blue-500 pb-2" {...props} />
            ),
            h2: ({ node, ...props }) => (
              <h2 className="text-2xl font-bold mt-6 mb-3 text-gray-800 border-b border-gray-300 pb-2" {...props} />
            ),
            h3: ({ node, ...props }) => (
              <h3 className="text-xl font-semibold mt-5 mb-2 text-gray-800" {...props} />
            ),
            h4: ({ node, ...props }) => (
              <h4 className="text-lg font-semibold mt-4 mb-2 text-gray-700" {...props} />
            ),
            p: ({ node, ...props }) => (
              <p className="my-3 text-gray-700 leading-relaxed" {...props} />
            ),
            ul: ({ node, ...props }) => (
              <ul className="my-4 ml-6 list-disc space-y-2 text-gray-700" {...props} />
            ),
            ol: ({ node, ...props }) => (
              <ol className="my-4 ml-6 list-decimal space-y-2 text-gray-700" {...props} />
            ),
            li: ({ node, ...props }) => (
              <li className="ml-2" {...props} />
            ),
            code: ({ node, inline, ...props }: any) =>
              inline ? (
                <code className="bg-gray-100 text-red-600 px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
              ) : (
                <code className="block bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono my-4" {...props} />
              ),
            pre: ({ node, ...props }) => (
              <pre className="my-4" {...props} />
            ),
            blockquote: ({ node, ...props }) => (
              <blockquote className="border-l-4 border-blue-500 pl-4 py-2 my-4 italic text-gray-600 bg-blue-50" {...props} />
            ),
            table: ({ node, ...props }) => (
              <div className="overflow-x-auto my-6">
                <table className="min-w-full divide-y divide-gray-300 border border-gray-300" {...props} />
              </div>
            ),
            thead: ({ node, ...props }) => (
              <thead className="bg-gray-50" {...props} />
            ),
            tbody: ({ node, ...props }) => (
              <tbody className="divide-y divide-gray-200 bg-white" {...props} />
            ),
            tr: ({ node, ...props }) => (
              <tr {...props} />
            ),
            th: ({ node, ...props }) => (
              <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900" {...props} />
            ),
            td: ({ node, ...props }) => (
              <td className="px-4 py-3 text-sm text-gray-700" {...props} />
            ),
            a: ({ node, ...props }) => (
              <a className="text-blue-600 hover:text-blue-800 underline" {...props} />
            ),
            strong: ({ node, ...props }) => (
              <strong className="font-bold text-gray-900" {...props} />
            ),
            em: ({ node, ...props }) => (
              <em className="italic text-gray-700" {...props} />
            ),
            hr: ({ node, ...props }) => (
              <hr className="my-8 border-t-2 border-gray-300" {...props} />
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
