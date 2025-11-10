import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "要件定義書支援AI",
  description: "要件定義作業を支援するAIシステム",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
