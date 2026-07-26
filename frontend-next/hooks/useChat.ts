"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { Message } from "@/lib/types";
import { getGuestCount, incrementGuestCount, isGuestLimitReached } from "@/lib/auth";
import { sendChat } from "@/lib/api";
import { useUser } from "@/context/UserContext";

export const OPENING_MESSAGE: Message = {
  role: "assistant",
  content: "שלום! אני כאן לעזור לך להבין כל מה שקשור לקרקעות בישראל — תכניות בנייה, ייעוד, תהליכים, ועוד. מה מביא אותך לכאן?",
};

interface UseChatOptions {
  initialMessages?: Message[];
  initialSessionId?: string;
}

export function useChat(options: UseChatOptions = {}) {
  const { user, refreshSessions, setShowRegister } = useUser();

  const [messages, setMessages] = useState<Message[]>(
    options.initialMessages ?? [OPENING_MESSAGE]
  );
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(options.initialSessionId);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || loading) return;

    // Guest limit
    if (!user && isGuestLimitReached()) {
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

      // Guest counter
      if (!user) {
        const count = incrementGuestCount();
        if (count >= 3) setTimeout(() => setShowRegister(true), 800);
      }

      refreshSessions();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "שגיאה בשרת";
      setMessages([...newMessages, { role: "assistant", content: `סליחה, הייתה שגיאה: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, sessionId, user, refreshSessions, setShowRegister]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  const reset = useCallback(() => {
    setMessages([OPENING_MESSAGE]);
    setSessionId(undefined);
    setInput("");
  }, []);

  return {
    messages,
    setMessages,
    input,
    setInput,
    loading,
    sessionId,
    bottomRef,
    sendMessage,
    handleKeyDown,
    reset,
    guestLeft: Math.max(0, 3 - getGuestCount()),
  };
}
