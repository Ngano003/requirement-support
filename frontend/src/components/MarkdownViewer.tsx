"use client";

import React from "react";
import ReactMarkdown from "react-markdown";

interface MarkdownViewerProps {
  content: string;
}

export default function MarkdownViewer({ content }: MarkdownViewerProps) {
  return (
    <div className="h-full overflow-y-auto">
      <div className="prose prose-sm max-w-none p-6">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}
