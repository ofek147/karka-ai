"use client";
import { useState } from "react";
import { registerUser } from "@/lib/api";
import { saveUser } from "@/lib/auth";
import { User } from "@/lib/types";

interface Props {
  onSuccess: (user: User) => void;
}

export default function RegisterModal({ onSuccess }: Props) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name || !phone || !email) {
      setError("נא למלא את כל השדות");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const user = await registerUser(name, phone, email);
      saveUser(user);
      onSuccess(user);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "שגיאה ברישום");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 border border-slate-100">
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[#d97706] text-xl">◈</span>
          <h2 className="text-xl font-bold text-[#0f172a]">המשך את השיחה</h2>
        </div>
        <p className="text-sm text-slate-500 mb-6 mr-7">
          הירשם חינם כדי לשמור שיחות ולקבל גישה מלאה
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="text"
            placeholder="שם מלא"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:border-[#d97706] focus:ring-2 focus:ring-[#d97706]/20 transition-all"
            style={{ fontSize: "16px" }}
          />
          <input
            type="tel"
            placeholder="טלפון"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:border-[#d97706] focus:ring-2 focus:ring-[#d97706]/20 transition-all"
            style={{ fontSize: "16px" }}
          />
          <input
            type="email"
            placeholder="אימייל"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-slate-200 rounded-xl px-4 py-3 focus:outline-none focus:border-[#d97706] focus:ring-2 focus:ring-[#d97706]/20 transition-all"
            style={{ fontSize: "16px" }}
          />

          {error && <p className="text-sm text-red-500 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="bg-[#d97706] text-white py-3 rounded-xl font-semibold hover:bg-[#b45309] transition-colors disabled:opacity-60 mt-1 shadow-sm"
          >
            {loading ? "רושם..." : "המשך בחינם"}
          </button>
        </form>

        <p className="text-xs text-slate-400 mt-4 text-center">
          הפרטים ישמשו ליצירת קשר בלבד · לא נשלח spam
        </p>
      </div>
    </div>
  );
}
