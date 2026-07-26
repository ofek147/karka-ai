"use client";
import Link from "next/link";
import { useUser } from "@/context/UserContext";

interface Props {
  onMenuClick?: () => void;
}

export default function ChatTopbar({ onMenuClick }: Props) {
  const { user, setShowRegister } = useUser();

  return (
    <header className="bg-[#0f172a] border-b border-white/10 px-4 py-3 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        {user && (
          <button
            onClick={onMenuClick}
            className="md:hidden p-1.5 rounded-md text-slate-400 hover:text-white transition-colors"
            aria-label="תפריט"
          >
            ☰
          </button>
        )}
        <Link href="/" className="flex items-center gap-2">
          <span className="text-[#d97706] text-lg">◈</span>
          <span className="font-bold text-white text-base tracking-tight">karka-ai</span>
        </Link>
      </div>

      <div className="flex items-center gap-3">
        {!user ? (
          <button
            onClick={() => setShowRegister(true)}
            className="text-sm text-[#f59e0b] font-medium hover:text-[#d97706] transition-colors"
          >
            הירשם לשמירת שיחות
          </button>
        ) : (
          <span className="text-sm text-slate-400">שלום, {user.name.split(" ")[0]}</span>
        )}
      </div>
    </header>
  );
}
