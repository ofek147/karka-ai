"use client";
import { ChatSession } from "@/lib/types";
import Link from "next/link";
import KarkaLogo from "@/components/KarkaLogo";

interface Props {
  sessions: ChatSession[];
  currentSessionId?: string;
  onNewChat: () => void;
  isOpen: boolean;
}

export default function ChatSidebar({ sessions, currentSessionId, onNewChat, isOpen }: Props) {
  return (
    <aside
      className={`
        fixed md:relative top-0 right-0 h-full z-40
        w-64 flex flex-col
        bg-[#0f172a] border-l border-white/10
        transition-transform duration-200
        ${isOpen ? "translate-x-0" : "translate-x-full md:translate-x-0"}
      `}
    >
      {/* Logo */}
      <div className="px-4 py-4 border-b border-white/10">
        <Link href="/"><KarkaLogo size="sm" /></Link>
      </div>

      {/* New chat */}
      <div className="px-3 pt-3 pb-2">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-white/10 bg-white/5 text-sm text-slate-300 hover:bg-white/10 hover:text-white transition-colors"
        >
          <span className="text-[#c4a044] text-base leading-none">+</span>
          שיחה חדשה
        </button>
      </div>

      {/* Sessions label */}
      {sessions.length > 0 && (
        <div className="px-4 pt-3 pb-1">
          <span className="text-xs text-slate-500 font-medium uppercase tracking-wider">שיחות אחרונות</span>
        </div>
      )}

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto px-3 pb-4">
        {sessions.length === 0 ? (
          <p className="text-xs text-slate-600 text-center mt-8">אין שיחות קודמות</p>
        ) : (
          <div className="flex flex-col gap-0.5">
            {sessions.map((s) => (
              <Link
                key={s.id}
                href={`/chat/${s.id}`}
                className={`
                  block px-3 py-2.5 rounded-lg text-sm truncate transition-colors
                  ${currentSessionId === s.id
                    ? "bg-[#c4a044]/15 text-[#d4b05a] border border-[#c4a044]/20"
                    : "text-slate-400 hover:bg-white/5 hover:text-slate-200"}
                `}
              >
                {s.title}
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Bottom branding */}
      <div className="px-4 py-3 border-t border-white/10">
        <p className="text-xs text-slate-600 text-center">AI לקרקעות ישראל</p>
      </div>
    </aside>
  );
}
