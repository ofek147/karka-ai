"use client";
import Link from "next/link";

const EXAMPLE_QUESTIONS = [
  "גוש 6111 חלקה 50 — כמה יחידות דיור אפשר לבנות?",
  "מה ההבדל בין תמ\"א 38 לתמ\"א 70?",
  "הציעו לי קרקע חקלאית — האם כדאי?",
  "מה זה ייעוד 'עירוני מעורב' ומה אפשר לעשות בו?",
];

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col overflow-y-auto bg-[#0a0f1a]" dir="rtl">

      {/* Header */}
      <header className="relative z-20 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span style={{ color: "#c4a044" }} className="text-2xl">◈</span>
          <span className="font-bold text-xl text-white tracking-tight">karka-ai</span>
        </div>
        <Link
          href="/chat"
          className="text-sm font-semibold px-5 py-2 rounded-lg text-white border border-white/20 hover:bg-white/10 transition-colors"
        >
          כניסה
        </Link>
      </header>

      {/* Hero — תמונת קרקע + overlay */}
      <section className="relative flex-1 flex flex-col items-center justify-center min-h-[85vh] px-6 py-20 overflow-hidden">
        {/* Background image */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat"
          style={{ backgroundImage: "url('/hero.jpg')" }}
        />
        {/* Dark overlay — gradient */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#0a0f1a]/80 via-[#0a0f1a]/60 to-[#0a0f1a]" />

        {/* Content */}
        <div className="relative z-10 max-w-2xl mx-auto text-center">
          <div
            className="inline-flex items-center gap-2 border text-xs px-3 py-1.5 rounded-full mb-6 font-medium"
            style={{ background: "rgba(196,160,68,0.1)", borderColor: "rgba(196,160,68,0.3)", color: "#d4b05a" }}
          >
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "#c4a044" }} />
            AI לניתוח קרקעות בישראל
          </div>

          <h1 className="text-5xl md:text-6xl font-bold text-white mb-5 leading-tight">
            כל מה שרצית לדעת
            <br />
            <span style={{ color: "#c4a044" }}>על הקרקע שלך</span>
          </h1>

          <p className="text-lg text-slate-300 mb-10 leading-relaxed max-w-lg mx-auto">
            שאל בעברית חופשית על ייעוד, תכניות בנייה, זכויות, ותהליכי אישור.
            <br />
            AI שמבין קרקעות ישראליות — ועונה בשפה פשוטה.
          </p>

          <Link
            href="/chat"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl text-lg font-semibold text-white transition-all hover:-translate-y-0.5"
            style={{ background: "#c4a044", boxShadow: "0 4px 24px rgba(196,160,68,0.3)" }}
            onMouseEnter={e => (e.currentTarget.style.background = "#b38c36")}
            onMouseLeave={e => (e.currentTarget.style.background = "#c4a044")}
          >
            שאל שאלה — חינם
            <span>◀</span>
          </Link>
          <p className="text-sm text-slate-500 mt-3">ללא הרשמה · 3 שאלות ראשונות</p>
        </div>
      </section>

      {/* Example questions */}
      <section className="bg-[#0a0f1a] px-6 py-16">
        <div className="max-w-3xl mx-auto">
          <p className="text-center text-sm font-medium text-slate-500 uppercase tracking-wider mb-8">
            שאלות שאנשים שואלים
          </p>
          <div className="grid md:grid-cols-2 gap-3">
            {EXAMPLE_QUESTIONS.map((q) => (
              <Link
                key={q}
                href="/chat"
                className="group flex items-start gap-3 px-4 py-4 rounded-xl border border-white/8 bg-white/3 hover:bg-white/6 hover:border-white/15 transition-all cursor-pointer"
              >
                <span className="mt-0.5 text-sm shrink-0" style={{ color: "#c4a044" }}>◈</span>
                <span className="text-sm text-slate-300 group-hover:text-white transition-colors leading-relaxed">
                  {q}
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* Value props */}
      <section className="px-6 py-14 border-t border-white/8">
        <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-6">
          {[
            {
              icon: "🛰️",
              title: "נתונים ממקור ראשון",
              desc: "מחובר לiplan — תכניות, ייעוד, וזכויות בנייה עדכניות בזמן אמת",
            },
            {
              icon: "🧠",
              title: "מבין הקשר",
              desc: "שואל בחזרה, מעמיק, ומזהה מה חשוב — לא רק עונה ונגמר",
            },
            {
              icon: "🔒",
              title: "בלי מתווכים",
              desc: "ישירות אליך. ללא עורכי דין, ללא יועצים, ללא תורים",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="rounded-2xl p-6 border border-white/8 bg-white/3"
            >
              <span className="text-2xl mb-3 block">{f.icon}</span>
              <h3 className="font-semibold text-white mb-2">{f.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-14 text-center border-t border-white/8 bg-[#0d1320]">
        <h2 className="text-2xl font-bold text-white mb-2">מוכן להבין את הקרקע שלך?</h2>
        <p className="text-slate-400 text-sm mb-6">הצטרף — חינם, ללא כרטיס אשראי</p>
        <Link
          href="/chat"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white border border-white/20 hover:bg-white/8 transition-colors"
        >
          התחל עכשיו
        </Link>
      </section>

      {/* Footer */}
      <footer className="px-6 py-4 text-center text-xs text-slate-700 border-t border-white/5">
        karka-ai © 2026 · המידע לצרכי לימוד בלבד · אינו מהווה ייעוץ משפטי, תכנוני, או השקעתי
      </footer>
    </main>
  );
}
