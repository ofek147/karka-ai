import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "karka-ai — מה מסתתר מאחורי הקרקע שלך?",
  description: "שאל כל שאלה על קרקעות, תכניות בנייה וייעוד בישראל. AI מקצועי שמסביר בשפה פשוטה.",
  icons: { icon: "/favicon.ico" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl" className="h-full">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
      </head>
      <body className="h-full">{children}</body>
    </html>
  );
}
