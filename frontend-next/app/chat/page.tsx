"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { Message, ChatSession, User } from "@/lib/types";
import { getUser, getGuestCount, incrementGuestCount } from "@/lib/auth";
import { sendChat, getSessions, saveSession } from "@/lib/api";
import ChatSidebar from "@/components/ChatSidebar";
import MessageBubble, { TypingIndicator } from "@/components/MessageBubble";
import RegisterModal from "@/components/RegisterModal";

const OPENING_MESSAGE: Message = {
  role: "assistant",
  content: "שלום! אני כאן לעזור לך להבין כל מה שקשור לקרקעות בישראל — תכניות בנייה, ייעוד, תהליכים, ועוד. מה מביא אותך לכאן?",
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([OPENING_MESSAGE]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [user, setUser] = useState<User | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [showRegister, setShowRegister] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const u = getUser();
    setUser(u);
    if (u) getSessions(u.id).then(setSessions);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    const isGuest = !user;
    if (isGuest && getGuestCount() >= 3) {
      setShowRegister(true);
      return;
    }

    const userMsg: Message = { role: "user", content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const { answer, session_id } = await sendChat(newMessages, sessionId, user?.id);
      setSessionId(session_id);
      setMessages([...newMessages, { role: "assistant", content: answer }]);

      if (isGuest) {
        const newCount = incrementGuestCount();
        if (newCount >= 3) setTimeout(() => setShowRegister(true), 800);
      }

      if (user) getSessions(user.id).then(setSessions);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "שגיאה בשרת";
      setMessages([...newMessages, { role: "assistant", content: `סליחה, הייתה שגיאה: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, sessionId, user]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  function handleNewChat() {
    setMessages([OPENING_MESSAGE]);
    setSessionId(undefined);
    setInput("");
    setSidebarOpen(false);
  }

  async function handleRegistered(newUser: User) {
    setUser(newUser);
    setShowRegister(false);
    if (messages.length > 1 && sessionId) {
      const firstUserMsg = messages.find(m => m.role === "user");
      const title = firstUserMsg?.content.slice(0, 40) || "שיחה חדשה";
      await saveSession(newUser.id, sessionId, messages, title);
    }
    getSessions(newUser.id).then(setSessions);
  }

  const guestLeft = 3 - getGuestCount();

  return (
    <div className="flex overflow-hidden" style={{ height: "100dvh", background: "#f8fafc" }} dir="rtl">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/60 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      {user && (
        <ChatSidebar
          sessions={sessions}
          currentSessionId={sessionId}
          onNewChat={handleNewChat}
          isOpen={sidebarOpen}
        />
      )}

      {/* Main */}
      <div className="flex flex-col flex-1 min-w-0">

        {/* Topbar */}
        <header className="bg-[#0f172a] border-b border-white/10 px-4 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            {user && (
              <button onClick={() => setSidebarOpen(!sidebarOpen)} className="md:hidden p-1.5 rounded-md text-slate-400 hover:text-white">
                ☰
              </button>
            )}
            <div className="flex items-center gap-2">
              <span className="text-[#d97706] text-lg">◈</span>
              <span className="font-bold text-white text-base">karka-ai</span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {!user && (
              <button onClick={() => setShowRegister(true)} className="text-sm text-[#f59e0b] font-medium hover:text-[#d97706] transition-colors">
                הירשם לשמירת שיחות
              </button>
            )}
            {user && (
              <span className="text-sm text-slate-400">שלום, {user.name.split(" ")[0]}</span>
            )}
          </div>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-2xl mx-auto">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Guest counter */}
        {!user && guestLeft > 0 && (
          <div className="text-center text-xs text-slate-400 pb-1">
            {guestLeft} שאלות נותרו ללא הרשמה
          </div>
        )}

        {/* Input */}
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
                className="shrink-0 w-9 h-9 rounded-xl bg-[#d97706] text-white flex items-center justify-center hover:bg-[#b45309] disabled:opacity-30 transition-all disabled:cursor-not-allowed"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
            </div>
            <p className="text-center text-xs text-slate-400 mt-2">
              המידע מוצג לצרכי לימוד בלבד · אינו מהווה ייעוץ משפטי או השקעתי
            </p>
          </div>
        </div>
      </div>

      {showRegister && <RegisterModal onSuccess={handleRegistered} />}
    </div>
  );
}
