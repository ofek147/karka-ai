"use client";
import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { User, ChatSession } from "@/lib/types";
import { getUser, saveUser } from "@/lib/auth";
import { getSessions, saveSession, registerUser } from "@/lib/api";
import { Message } from "@/lib/types";

interface UserContextValue {
  user: User | null;
  sessions: ChatSession[];
  showRegister: boolean;
  setShowRegister: (v: boolean) => void;
  refreshSessions: () => void;
  handleRegistered: (user: User, currentMessages?: Message[], currentSessionId?: string) => Promise<void>;
  register: (name: string, phone: string, email: string) => Promise<User>;
}

const UserContext = createContext<UserContextValue | null>(null);

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [showRegister, setShowRegister] = useState(false);

  useEffect(() => {
    const u = getUser();
    setUser(u);
    if (u) getSessions(u.id).then(setSessions);
  }, []);

  const refreshSessions = useCallback(() => {
    if (user) getSessions(user.id).then(setSessions);
  }, [user]);

  const register = useCallback(async (name: string, phone: string, email: string): Promise<User> => {
    const newUser = await registerUser(name, phone, email);
    saveUser(newUser);
    setUser(newUser);
    return newUser;
  }, []);

  const handleRegistered = useCallback(async (
    newUser: User,
    currentMessages?: Message[],
    currentSessionId?: string
  ) => {
    setShowRegister(false);
    // Save current guest conversation to DB
    if (currentMessages && currentMessages.length > 1 && currentSessionId) {
      const firstUserMsg = currentMessages.find(m => m.role === "user");
      const title = firstUserMsg?.content.slice(0, 40) || "שיחה חדשה";
      await saveSession(newUser.id, currentSessionId, currentMessages, title);
    }
    getSessions(newUser.id).then(setSessions);
  }, []);

  return (
    <UserContext.Provider value={{
      user, sessions, showRegister, setShowRegister,
      refreshSessions, handleRegistered, register
    }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const ctx = useContext(UserContext);
  if (!ctx) throw new Error("useUser must be used within UserProvider");
  return ctx;
}
