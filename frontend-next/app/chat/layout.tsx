"use client";
import { useState } from "react";
import { useUser } from "@/context/UserContext";
import ChatSidebar from "@/components/ChatSidebar";
import RegisterModal from "@/components/RegisterModal";
import { useRouter } from "next/navigation";
import { User } from "@/lib/types";

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const { user, sessions, showRegister, setShowRegister, handleRegistered } = useUser();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const router = useRouter();

  function onNewChat() {
    setSidebarOpen(false);
    router.push("/chat");
  }

  async function onRegisterSuccess(newUser: User) {
    await handleRegistered(newUser);
  }

  return (
    <div className="flex overflow-hidden" style={{ height: "100dvh", background: "#f8fafc" }} dir="rtl">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar — registered users only */}
      {user && (
        <ChatSidebar
          sessions={sessions}
          onNewChat={onNewChat}
          isOpen={sidebarOpen}
          onMenuToggle={() => setSidebarOpen(v => !v)}
        />
      )}

      {/* Page content (injected with sidebar toggle prop) */}
      <div className="flex flex-col flex-1 min-w-0">
        {children}
      </div>

      {/* Register modal */}
      {showRegister && (
        <RegisterModal onSuccess={onRegisterSuccess} onClose={() => setShowRegister(false)} />
      )}
    </div>
  );
}
