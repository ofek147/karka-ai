"use client";
import { ChatSession } from "@/lib/types";
import Link from "next/link";
import { useRouter } from "next/navigation";

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
        w-72 bg-gray-50 border-l border-gray-200 flex flex-col
        transition-transform duration-200
        ${isOpen ? "translate-x-0" : "translate-x-full md:translate-x-0"}
      `}
    >
      {/* Logo */}
      <div className="px-4 py-4 border-b border-gray-200">
        <Link href="/" className="font-bold text-lg text-gray-900">karka-ai</Link>
      </div>

      {/* New chat */}
      <div className="px-3 py-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-gray-200 bg-white text-sm text-gray-700 hover:bg-gray-100 transition-colors"
        >
          <span className="text-lg leading-none">+</span>
          שיחה חדשה
        </button>
      </div>

      {/* Sessions list */}
      <div className="flex-1 overflow-y-auto px-3 pb-4">
        {sessions.length === 0 ? (
          <p className="text-xs text-gray-400 text-center mt-6">אין שיחות קודמות</p>
        ) : (
          <div className="flex flex-col gap-1">
            {sessions.map((s) => (
              <Link
                key={s.id}
                href={`/chat/${s.id}`}
                className={`
                  block px-3 py-2.5 rounded-lg text-sm truncate transition-colors
                  ${currentSessionId === s.id
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-600 hover:bg-gray-100"}
                `}
              >
                {s.title}
              </Link>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
