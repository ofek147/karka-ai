"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Message, ChatSession, User } from "@/lib/types";
import { getUser } from "@/lib/auth";
import { getSessionMessages, getSessions, sendChat } from "@/lib/api";
import ChatSidebar from "@/components/ChatSidebar";
import MessageBubble, { TypingIndicator } from "@/components/MessageBubble";
import { useRef, useCallback } from "react";

export default function SessionPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const u = getUser();
    if (!u) { router.push("/chat"); return; }
    setUser(u);
    getSessions(u.id).then(setSessions);
    getSessionMessages(sessionId).then(setMessages);
  }, [sessionId, router]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading || !user) return;
    const userMsg: Message = { role: "user", content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);
    try {
      const { answer } = await sendChat(newMessages, sessionId, user.id);
      setMessages([...newMessages, { role: "assistant", content: answer }]);
      getSessions(user.id).then(setSessions);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "שגיאה";
      setMessages([...newMessages, { role: "assistant", content: `שגיאה: ${errMsg}` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, sessionId, user]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  function handleNewChat() {
    router.push("/chat");
  }

  return (
    <div className="flex overflow-hidden" style={{ height: "100dvh", background: "#f8fafc" }} dir="rtl">
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}
      {user && (
        <ChatSidebar sessions={sessions} currentSessionId={sessionId} onNewChat={handleNewChat} isOpen={sidebarOpen} />
      )}
      <div className="flex flex-col flex-1 min-w-0">
        <header className="bg-[#0f172a] border-b border-white/10 px-4 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="md:hidden p-1.5 rounded-md text-slate-400 hover:text-white">☰</button>
            <div className="flex items-center gap-2"><span className="text-[#d97706] text-lg">◈</span><span className="font-bold text-white text-base">karka-ai</span></div>
          </div>
          {user && <span className="text-sm text-slate-400">שלום, {user.name.split(" ")[0]}</span>}
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-2xl mx-auto">
          {messages.length === 0 && !loading && (
            <p className="text-center text-gray-400 text-sm mt-10">טוען שיחה...</p>
          )}
          {messages.map((msg, i) => <MessageBubble key={i} message={msg} />)}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
          </div>
        </div>

        <div className="shrink-0 px-4 pb-4 pt-2 bg-[#f8fafc] border-t border-slate-200">
          <div className="max-w-2xl mx-auto">
            <div className="flex gap-2 items-end bg-white border border-slate-200 rounded-2xl px-4 py-3 shadow-sm focus-within:border-[#d97706]/60 focus-within:shadow-[0_0_0_3px_rgba(217,119,6,0.1)] transition-all">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="שאל כל שאלה על קרקעות בישראל..."
                rows={1}
                className="flex-1 resize-none bg-transparent focus:outline-none text-[#0f172a] placeholder-slate-400 max-h-32 overflow-y-auto"
                style={{ direction: "rtl", fontSize: "16px", lineHeight: "1.5" }}
              />
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="shrink-0 w-9 h-9 rounded-xl bg-[#d97706] text-white flex items-center justify-center hover:bg-[#b45309] disabled:opacity-30 transition-all"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
