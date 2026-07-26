"use client";

interface Props {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent) => void;
  loading: boolean;
  guestLeft?: number;
  showGuest?: boolean;
}

export default function ChatInput({ value, onChange, onSend, onKeyDown, loading, guestLeft, showGuest }: Props) {
  return (
    <div className="shrink-0 px-4 pb-4 pt-2 bg-[#f8fafc] border-t border-slate-200">
      <div className="max-w-2xl mx-auto">
        {/* Guest counter */}
        {showGuest && guestLeft !== undefined && guestLeft > 0 && (
          <p className="text-center text-xs text-slate-400 mb-2">
            {guestLeft} שאלות נותרו ללא הרשמה
          </p>
        )}

        {/* Input row */}
        <div className="flex gap-2 items-end bg-white border border-slate-200 rounded-2xl px-4 py-3 shadow-sm focus-within:border-[#d97706]/60 focus-within:shadow-[0_0_0_3px_rgba(217,119,6,0.1)] transition-all">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="שאל כל שאלה על קרקעות בישראל..."
            rows={1}
            disabled={loading}
            className="flex-1 resize-none bg-transparent focus:outline-none text-[#0f172a] placeholder-slate-400 max-h-32 overflow-y-auto disabled:opacity-60"
            style={{ direction: "rtl", fontSize: "16px", lineHeight: "1.6" }}
          />
          <button
            onClick={onSend}
            disabled={!value.trim() || loading}
            className="shrink-0 w-9 h-9 rounded-xl bg-[#d97706] text-white flex items-center justify-center hover:bg-[#b45309] disabled:opacity-30 transition-all disabled:cursor-not-allowed"
            aria-label="שלח"
          >
            {loading ? (
              <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            )}
          </button>
        </div>

        <p className="text-center text-xs text-slate-400 mt-2">
          המידע לצרכי לימוד בלבד · אינו מהווה ייעוץ משפטי או השקעתי
        </p>
      </div>
    </div>
  );
}
