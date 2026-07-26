import type { Metadata } from "next";
import "./globals.css";
import { UserProvider } from "@/context/UserContext";

export const metadata: Metadata = {
  title: "karkAi — AI לניתוח קרקעות בישראל",
  description: "שאל כל שאלה על ייעוד, תכניות בנייה, וזכויות קרקע בישראל. AI שמבין קרקעות ועונה בשפה פשוטה.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="he" dir="rtl" className="h-full">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
      </head>
      <body className="h-full"><UserProvider>{children}</UserProvider></body>
    </html>
  );
}
