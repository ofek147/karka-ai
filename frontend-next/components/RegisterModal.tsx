"use client";
import { useState } from "react";
import { registerUser, requestMagicLink } from "@/lib/api";
import { saveUser } from "@/lib/auth";
import { User } from "@/lib/types";
import KarkaIcon from "@/components/KarkaIcon";

type Mode = "register" | "login";
type LoginStep = "email" | "email-sent";

interface Props {
  onSuccess: (user: User) => void;
  onClose?: () => void;
}

export default function RegisterModal({ onSuccess, onClose }: Props) {
  const [mode, setMode] = useState<Mode>("register");
  const [loginStep, setLoginStep] = useState<LoginStep>("email");

  // Register fields
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  // Login fields
  const [loginEmail, setLoginEmail] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // UTM source from URL
  const source = typeof window !== "undefined"
    ? new URLSearchParams(window.location.search).get("utm_source") || undefined
    : undefined;

  function resetError() { setError(""); }

  // ── Validation ──────────────────────────────────────────────────────────
  function validateForm(): string | null {
    if (!name.trim() || name.trim().length < 2) return "שם חייב להכיל לפחות 2 תווים";
    const phone_clean = phone.replace(/[-\s]/g, "");
    if (!/^(\+972|972|0)([23489]|5[02-9]|7[0-9])[0-9]{7}$/.test(phone_clean)) return "מספר טלפון לא תקין — נא להכניס מספר ישראלי";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return "כתובת אימייל לא תקינה";
    return null;
  }

  // ── Register ──────────────────────────────────────────────────────────────
  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    const validErr = validateForm();
    if (validErr) { setError(validErr); return; }
    setLoading(true); resetError();
    try {
      const guestSessionId = typeof window !== "undefined"
        ? localStorage.getItem("karka_session_id") || undefined
        : undefined;
      const user = await registerUser(name, phone, email, source, guestSessionId);
      saveUser(user);
      onSuccess(user);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "שגיאה ברישום");
    } finally { setLoading(false); }
  }

  // ── Login: send magic link ────────────────────────────────────────────────
  async function handleMagicLink(e: React.FormEvent) {
    e.preventDefault();
    if (!loginEmail) { setError("נא להכניס אימייל"); return; }
    setLoading(true); resetError();
    try {
      const res = await requestMagicLink(loginEmail);
      if (res.reason === "not_registered") {
        setError("המייל הזה לא רשום — עבור ל\"משתמש חדש\" כדי להירשם");
      } else {
        setLoginStep("email-sent");
      }
    } catch {
      setError("שגיאה בשליחת הקישור");
    } finally { setLoading(false); }
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md border border-slate-100 overflow-hidden">

        {/* Header */}
        <div className="bg-[#0d1829] px-6 py-5 flex items-center gap-3">
          <KarkaIcon size={32} />
          <div className="flex-1">
            <h2 className="text-white font-bold text-lg leading-tight">
              {mode === "register" ? "המשך את השיחה" : "כניסה ל-karkAi"}
            </h2>
            <p className="text-slate-400 text-xs mt-0.5">
              {mode === "register" ? "הירשם חינם לשמירת שיחות" : "שלח קישור כניסה לאימייל שנרשמת איתו"}
            </p>
          </div>
          {onClose && (
            <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors text-xl leading-none">×</button>
          )}
        </div>

        {/* Tab switch */}
        <div className="flex border-b border-slate-100">
          {(["register", "login"] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setLoginStep("email"); resetError(); }}
              className={`flex-1 py-3 text-sm font-medium transition-colors ${
                mode === m
                  ? "text-[#c4a044] border-b-2 border-[#c4a044]"
                  : "text-slate-400 hover:text-slate-600"
              }`}
            >
              {m === "register" ? "משתמש חדש" : "כבר רשום"}
            </button>
          ))}
        </div>

        <div className="px-6 py-5">
          {/* ── Register form ── */}
          {mode === "register" && (
            <form onSubmit={handleRegister} className="flex flex-col gap-3">
              <input type="text" placeholder="שם מלא" value={name}
                onChange={e => setName(e.target.value)}
                className="border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:border-[#c4a044] focus:ring-2 focus:ring-[#c4a044]/20 transition-all text-base" />
              <input type="tel" placeholder="טלפון" value={phone} dir="rtl"
                onChange={e => setPhone(e.target.value)}
                className="border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:border-[#c4a044] focus:ring-2 focus:ring-[#c4a044]/20 transition-all text-base text-right" />
              <input type="email" placeholder="אימייל" value={email}
                onChange={e => setEmail(e.target.value)}
                className="border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:border-[#c4a044] focus:ring-2 focus:ring-[#c4a044]/20 transition-all text-base" />
              {error && <p className="text-sm text-red-500 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
              <button type="submit" disabled={loading}
                className="bg-[#c4a044] text-white py-3 rounded-xl font-semibold hover:bg-[#b38c36] transition-colors disabled:opacity-60 mt-1">
                {loading ? "רושם..." : "המשך בחינם"}
              </button>
              <p className="text-xs text-slate-400 text-center">הפרטים ישמשו ליצירת קשר בלבד</p>
            </form>
          )}

          {/* ── Login: magic link by email ── */}
          {mode === "login" && loginStep === "email" && (
            <form onSubmit={handleMagicLink} className="flex flex-col gap-3">
              <p className="text-sm text-slate-500 mb-1">נשלח קישור כניסה לאימייל שנרשמת איתו</p>
              <input type="email" placeholder="כתובת אימייל" value={loginEmail}
                onChange={e => setLoginEmail(e.target.value)}
                className="border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:border-[#c4a044] focus:ring-2 focus:ring-[#c4a044]/20 transition-all text-base"
                autoFocus />
              {error && <p className="text-sm text-red-500 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
              <button type="submit" disabled={loading}
                className="bg-[#c4a044] text-white py-3 rounded-xl font-semibold hover:bg-[#b38c36] transition-colors disabled:opacity-60">
                {loading ? "שולח..." : "שלח קישור לאימייל"}
              </button>

            </form>
          )}

          {/* ── Login: magic link sent ── */}
          {mode === "login" && loginStep === "email-sent" && (
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <div className="text-4xl">📬</div>
              <h3 className="font-semibold text-slate-800">בדוק את האימייל שלך</h3>
              <p className="text-sm text-slate-500">
                שלחנו קישור כניסה ל-<span className="font-medium text-slate-700">{loginEmail}</span>
                <br />בתוקף ל-30 דקות
              </p>
              <button onClick={() => { setLoginStep("email"); setLoginEmail(""); resetError(); }}
                className="text-sm text-[#c4a044] hover:underline mt-2">
                שלח שוב לאימייל אחר
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
