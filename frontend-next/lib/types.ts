export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  name: string;
  phone: string;
  email: string;
}

export interface AuthState {
  user: User | null;
  guestCount: number; // messages used as guest (max 3)
}
