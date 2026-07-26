"use client";
import Link from "next/link";
import { useUser } from "@/context/UserContext";
import KarkaLogo from "@/components/KarkaLogo";

export default function ChatTopbar() {
  const { user, setShowRegister, setSidebarOpen } = useUser();

  return (
    <header className="bg-[#0f172a] border-b border-white/10 px-4 py-3 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        {user && (
          <button
            onClick={() => setSidebarOpen(v => !v)}
            className="md:hidden p-1.5 rounded-md text-slate-400 hover:text-white transition-colors"
            aria-label="תפריט"
          >
            ☰
          </button>
        )}
        <Link href="/"><KarkaLogo /></Link>
      </div>

      <div className="flex items-center gap-3">
        {!user ? (
          <button
            onClick={() => setShowRegister(true)}
            className="text-sm text-[#d4b05a] font-medium hover:text-[#c4a044] transition-colors"
          >
            הירשם לשמירת שיחות
          </button>
        ) : (
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400 hidden sm:block">שלום, {user.name.split(" ")[0]}</span>
            <button
              onClick={() => { localStorage.clear(); window.location.href = "/"; }}
              className="text-xs text-slate-600 hover:text-slate-400 transition-colors border border-white/10 px-2.5 py-1 rounded-lg"
            >
              יציאה
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
