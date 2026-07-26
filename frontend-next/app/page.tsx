"use client";
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0f172a] flex flex-col overflow-y-auto" dir="rtl">

      {/* Header */}
      <header className="px-6 py-5 flex items-center justify-between border-b border-white/10">
        <div className="flex items-center gap-2">
          <span className="text-[#d97706] text-2xl">◈</span>
          <span className="font-bold text-xl text-white tracking-tight">karka-ai</span>
        </div>
        <Link
          href="/chat"
          className="bg-[#d97706] text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-[#b45309] transition-colors"
        >
          התחל שיחה
        </Link>
      </header>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-24 text-center relative overflow-hidden topo-bg">
        {/* Glow */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#d97706]/5 via-transparent to-transparent pointer-events-none" />

        <div className="relative z-10 max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-[#d97706]/10 border border-[#d97706]/30 text-[#f59e0b] text-xs px-3 py-1.5 rounded-full mb-6 font-medium">
            <span className="w-1.5 h-1.5 bg-[#f59e0b] rounded-full animate-pulse" />
            AI מקצועי לקרקעות בישראל
          </div>

          <h1 className="text-5xl md:text-6xl font-bold text-white mb-5 leading-tight">
            מה מסתתר מאחורי
            <br />
            <span className="text-[#d97706]">הקרקע שלך?</span>
          </h1>

          <p className="text-lg text-slate-400 mb-10 leading-relaxed max-w-lg mx-auto">
            שאל כל שאלה על קרקעות, תכניות בנייה, ייעוד ותהליכי אישור בישראל.
            <br />
            תשובות מדויקות בשפה פשוטה — בלי עורכי דין, בלי בירוקרטיה.
          </p>

          <Link
            href="/chat"
            className="inline-flex items-center gap-2 bg-[#d97706] text-white px-8 py-4 rounded-xl text-lg font-semibold hover:bg-[#b45309] transition-all shadow-lg shadow-amber-900/30 hover:shadow-amber-900/50 hover:-translate-y-0.5"
          >
            שוחח עכשיו — חינם
            <span className="text-xl">◀</span>
          </Link>
          <p className="text-sm text-slate-500 mt-3">3 שאלות ראשונות ללא הרשמה</p>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-white/10 px-6 py-16 bg-[#0f172a]">
        <div className="max-w-4xl mx-auto grid md:grid-cols-3 gap-6">
          {[
            {
              icon: "🗺️",
              title: "נתוני תכנון אמיתיים",
              desc: "מחובר לiplan ומחלקות התכנון — נתונים עדכניים בזמן אמת",
              color: "from-blue-500/10 to-blue-600/5",
              border: "border-blue-500/20",
            },
            {
              icon: "💬",
              title: "שיחה, לא טפסים",
              desc: "שאל בעברית חופשית — הAI מבין הקשר ושואל בחזרה",
              color: "from-amber-500/10 to-amber-600/5",
              border: "border-amber-500/20",
            },
            {
              icon: "📊",
              title: "ניתוח מעמיק",
              desc: "תכניות, ייעוד, זכויות בנייה — מוסבר בשפה שכולם מבינים",
              color: "from-emerald-500/10 to-emerald-600/5",
              border: "border-emerald-500/20",
            },
          ].map((f) => (
            <div
              key={f.title}
              className={`bg-gradient-to-br ${f.color} border ${f.border} rounded-2xl p-6 flex flex-col gap-3`}
            >
              <span className="text-3xl">{f.icon}</span>
              <h3 className="font-semibold text-white text-base">{f.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA bottom */}
      <section className="px-6 py-14 text-center bg-gradient-to-b from-[#0f172a] to-[#1e293b]">
        <h2 className="text-2xl font-bold text-white mb-3">
          מוכן לחקור את הקרקע שלך?
        </h2>
        <p className="text-slate-400 mb-6 text-sm">הצטרף למשתמשים שכבר מקבלים תשובות</p>
        <Link
          href="/chat"
          className="inline-flex items-center gap-2 bg-white/5 border border-white/20 text-white px-6 py-3 rounded-xl text-sm font-medium hover:bg-white/10 transition-colors"
        >
          התחל שיחה חינמית
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 px-6 py-4 text-center text-xs text-slate-600">
        karka-ai © 2026 · המידע מוצג לצרכי לימוד בלבד ואינו מהווה ייעוץ משפטי, תכנוני, או השקעתי.
      </footer>
    </main>
  );
}
