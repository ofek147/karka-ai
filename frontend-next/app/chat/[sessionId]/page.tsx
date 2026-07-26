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
    <div className="flex h-screen overflow-hidden bg-white" dir="rtl">
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/30 z-30 md:hidden" onClick={() => setSidebarOpen(false)} />
      )}
      {user && (
        <ChatSidebar sessions={sessions} currentSessionId={sessionId} onNewChat={handleNewChat} isOpen={sidebarOpen} />
      )}
      <div className="flex flex-col flex-1 min-w-0">
        <header className="border-b border-gray-100 px-4 py-3 flex items-center justify-between bg-white">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="md:hidden p-1.5 rounded-md hover:bg-gray-100">☰</button>
            <span className="font-semibold text-gray-800">karka-ai</span>
          </div>
          {user && <span className="text-sm text-gray-400">שלום, {user.name.split(" ")[0]}</span>}
        </header>

        <div className="flex-1 overflow-y-auto px-4 py-6 max-w-2xl mx-auto w-full">
          {messages.length === 0 && !loading && (
            <p className="text-center text-gray-400 text-sm mt-10">טוען שיחה...</p>
          )}
          {messages.map((msg, i) => <MessageBubble key={i} message={msg} />)}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-gray-100 px-4 py-3 bg-white">
          <div className="max-w-2xl mx-auto flex gap-2 items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="שאל כל שאלה על קרקעות בישראל..."
              rows={1}
              className="flex-1 resize-none border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-400 max-h-32 overflow-y-auto"
              style={{ direction: "rtl" }}
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
    </div>
  );
}
