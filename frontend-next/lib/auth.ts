import { User } from "./types";

const USER_KEY = "karka_user";
const GUEST_KEY = "karka_guest_count";

export function getUser(): User | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveUser(user: User): void {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getGuestCount(): number {
  if (typeof window === "undefined") return 0;
  return parseInt(localStorage.getItem(GUEST_KEY) || "0", 10);
}

export function incrementGuestCount(): number {
  const count = getGuestCount() + 1;
  localStorage.setItem(GUEST_KEY, String(count));
  return count;
}

export function isGuestLimitReached(): boolean {
  return getGuestCount() >= 3 && !getUser();
}
