"use client";
import { useChat } from "@/hooks/useChat";
import { useUser } from "@/context/UserContext";
import ChatTopbar from "@/components/ChatTopbar";
import ChatInput from "@/components/ChatInput";
import MessageBubble, { TypingIndicator } from "@/components/MessageBubble";

export default function ChatPage() {
  const { user } = useUser();
  const { messages, input, setInput, loading, bottomRef, sendMessage, handleKeyDown, guestLeft } = useChat();

  return (
    <>
      <ChatTopbar />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-2xl mx-auto">
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
        guestLeft={guestLeft}
        showGuest={!user}
      />
    </>
  );
}
