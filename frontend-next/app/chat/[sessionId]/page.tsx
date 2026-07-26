"use client";
import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useChat } from "@/hooks/useChat";
import { useUser } from "@/context/UserContext";
import { getSessionMessages } from "@/lib/api";
import ChatTopbar from "@/components/ChatTopbar";
import ChatInput from "@/components/ChatInput";
import MessageBubble, { TypingIndicator } from "@/components/MessageBubble";

export default function SessionPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const { user, initialized } = useUser();

  const { messages, setMessages, input, setInput, loading, bottomRef, sendMessage, handleKeyDown } = useChat({
    initialSessionId: sessionId,
  });

  useEffect(() => {
    if (!initialized) return;           // wait for localStorage to load
    if (!user) { router.push("/chat"); return; }
    getSessionMessages(sessionId).then(msgs => {
      if (msgs.length > 0) setMessages(msgs);
    });
  }, [sessionId, user, initialized, router, setMessages]);

  return (
    <>
      <ChatTopbar />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-2xl mx-auto">
          {messages.length === 0 && !loading && (
            <p className="text-center text-slate-400 text-sm mt-16">טוען שיחה...</p>
          )}
          {messages.map((msg, i) => <MessageBubble key={i} message={msg} />)}
          {loading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </div>

      <ChatInput
        value={input}
        onChange={setInput}
        onSend={sendMessage}
        onKeyDown={handleKeyDown}
        loading={loading}
      />
    </>
  );
}
