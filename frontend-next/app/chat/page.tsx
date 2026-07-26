"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { Message, ChatSession, User } from "@/lib/types";
import { getUser, getGuestCount, incrementGuestCount, isGuestLimitReached } from "@/lib/auth";
import { sendChat, getSessions } from "@/lib/api";
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

  // Init
  useEffect(() => {
    const u = getUser();
    setUser(u);
    if (u) {
      getSessions(u.id).then(setSessions);
    }
  }, []);

  // Scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    // Guest limit check — show gate AFTER answering
    const isGuest = !user;
    const guestCount = getGuestCount();
    if (isGuest && guestCount >= 3) {
      setShowRegister(true);
      return;
    }

    const userMsg: Message = { role: "user", content: text };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const { answer, session_id } = await sendChat(
        newMessages,
        sessionId,
        user?.id
      );

      setSessionId(session_id);
      setMessages([...newMessages, { role: "assistant", content: answer }]);

      // Increment guest count after receiving answer
      if (isGuest) {
        const newCount = incrementGuestCount();
        if (newCount >= 3) {
          // Show register gate after this answer renders
          setTimeout(() => setShowRegister(true), 800);
        }
      }

      // Refresh sessions
      if (user) {
        getSessions(user.id).then(setSessions);
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "שגיאה בשרת";
      setMessages([...newMessages, { role: "assistant", content: `סליחה, הייתה שגיאה: ${errMsg}` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, sessionId, user]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleNewChat() {
    setMessages([OPENING_MESSAGE]);
    setSessionId(undefined);
    setInput("");
    setSidebarOpen(false);
  }

  function handleRegistered(newUser: User) {
    setUser(newUser);
    setShowRegister(false);
    getSessions(newUser.id).then(setSessions);
  }

  return (
    <div className="flex overflow-hidden bg-white" style={{ height: "100dvh" }} dir="rtl">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar — only for registered users */}
      {user && (
        <ChatSidebar
          sessions={sessions}
          currentSessionId={sessionId}
          onNewChat={handleNewChat}
          isOpen={sidebarOpen}
        />
      )}

      {/* Main chat */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Topbar */}
        <header className="border-b border-gray-100 px-4 py-3 flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            {user && (
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="md:hidden p-1.5 rounded-md hover:bg-gray-100"
              >
                ☰
              </button>
            )}
            <span className="font-semibold text-gray-800">karka-ai</span>
          </div>
          {!user && (
            <button
              onClick={() => setShowRegister(true)}
              className="text-sm text-blue-600 font-medium hover:underline"
            >
              הירשם לשמירת שיחות
            </button>
          )}
          {user && (
            <span className="text-sm text-gray-400">שלום, {user.name.split(" ")[0]}</span>
          )}
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6 max-w-2xl mx-auto w-full">
          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        {/* Guest counter */}
        {!user && (
          <div className="text-center text-xs text-gray-400 pb-1">
            {3 - getGuestCount()} שאלות נותרו ללא הרשמה
          </div>
        )}

        {/* Input */}
        <div className="border-t border-gray-100 px-4 py-3 bg-white">
          <div className="max-w-2xl mx-auto flex gap-2 items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="שאל כל שאלה על קרקעות בישראל..."
              rows={1}
              className="flex-1 resize-none border border-gray-200 rounded-xl px-4 py-3 focus:outline-none focus:border-blue-400 max-h-32 overflow-y-auto"
              style={{ direction: "rtl", fontSize: "16px" }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="bg-blue-600 text-white px-4 py-3 rounded-xl hover:bg-blue-700 disabled:opacity-40 transition-colors shrink-0"
            >
              ➤
            </button>
          </div>
        </div>
      </div>

      {/* Registration modal */}
      {showRegister && <RegisterModal onSuccess={handleRegistered} />}
    </div>
  );
}
