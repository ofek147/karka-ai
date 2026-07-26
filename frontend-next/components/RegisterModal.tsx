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
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-1">המשך את השיחה</h2>
        <p className="text-sm text-gray-500 mb-6">
          השאר פרטים כדי לקבל גישה מלאה ולשמור את השיחות שלך
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="text"
            placeholder="שם מלא"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-blue-500"
          />
          <input
            type="tel"
            placeholder="טלפון"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-blue-500"
          />
          <input
            type="email"
            placeholder="אימייל"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-gray-200 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-blue-500"
          />

          {error && <p className="text-sm text-red-500">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-60"
          >
            {loading ? "רושם..." : "המשך"}
          </button>
        </form>

        <p className="text-xs text-gray-400 mt-4 text-center">
          הפרטים ישמשו ליצירת קשר בלבד. לא נשלח spam.
        </p>
      </div>
    </div>
  );
}
