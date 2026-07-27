import { Message, ChatSession, User } from "./types";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.karka-ai.co.il";

export async function sendChat(
  messages: Message[],
  sessionId?: string,
  userId?: string
): Promise<{ answer: string; session_id: string }> {
  const res = await fetch(`${API}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages, session_id: sessionId, user_id: userId != null ? String(userId) : null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    throw new Error(detail || "שגיאה בשרת");
  }
  return res.json();
}

export async function registerUser(
  name: string,
  phone: string,
  email: string,
  source?: string,
  guestSessionId?: string,
): Promise<User> {
  const res = await fetch(`${API}/api/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, phone, email, source, guest_session_id: guestSessionId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "שגיאה ברישום");
  }
  const data = await res.json();
  // Backend returns lead id — use as user id
  return { id: data.id || crypto.randomUUID(), name, phone, email };
}

export async function getSessions(userId: string): Promise<ChatSession[]> {
  const res = await fetch(`${API}/api/sessions/${userId}`);
  if (!res.ok) return [];
  return res.json();
}

export async function saveSession(
  userId: string,
  sessionId: string,
  messages: Message[],
  title: string
): Promise<void> {
  await fetch(`${API}/api/sessions/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, session_id: sessionId, messages, title }),
  });
}

export async function getSessionMessages(sessionId: string): Promise<Message[]> {
  const res = await fetch(`${API}/api/sessions/${sessionId}/messages`);
  if (!res.ok) return [];
  return res.json();
}

export async function requestMagicLink(email: string): Promise<{ ok: boolean; reason?: string }> {
  const res = await fetch(`${API}/api/auth/request-magic`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  const data = await res.json().catch(() => ({ ok: false }));
  return data;
}

export async function verifyMagicToken(token: string): Promise<User> {
  const res = await fetch(`${API}/api/auth/verify-magic?token=${encodeURIComponent(token)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "קישור לא תקין");
  }
  const data = await res.json();
  return data.user;
}
