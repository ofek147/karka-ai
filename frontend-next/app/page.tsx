"use client";
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-100 px-6 py-4 flex items-center justify-between">
        <span className="font-bold text-xl text-gray-900">karka-ai</span>
        <Link
          href="/chat"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          התחל שיחה
        </Link>
      </header>

      {/* Hero */}
      <section className="flex-1 flex flex-col items-center justify-center px-6 py-20 text-center">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4 leading-tight">
          מה מסתתר מאחורי
          <br />
          <span className="text-blue-600">הקרקע שלך?</span>
        </h1>
        <p className="text-lg text-gray-500 mb-8 max-w-lg">
          שאל כל שאלה על קרקעות, תכניות בנייה, ייעוד ותהליכי אישור בישראל.
          <br />
          AI מקצועי שמסביר בשפה פשוטה — בלי עורכי דין.
        </p>
        <Link
          href="/chat"
          className="bg-blue-600 text-white px-8 py-4 rounded-xl text-lg font-medium hover:bg-blue-700 transition-colors shadow-sm"
        >
          שוחח עכשיו — חינם
        </Link>
        <p className="text-sm text-gray-400 mt-3">3 שאלות ראשונות ללא הרשמה</p>
      </section>

      {/* Features */}
      <section className="border-t border-gray-100 px-6 py-16">
        <div className="max-w-3xl mx-auto grid md:grid-cols-3 gap-8 text-center">
          {[
            { icon: "🗺️", title: "נתוני תכנון אמיתיים", desc: "מחובר לiplan ומחלקות התכנון בזמן אמת" },
            { icon: "💬", title: "שיחה, לא טפסים", desc: "שאל בעברית חופשית — אנחנו מבינים את ההקשר" },
            { icon: "🔒", title: "פרטיות מלאה", desc: "המידע שלך נשמר אצלנו בלבד" },
          ].map((f) => (
            <div key={f.title} className="flex flex-col items-center gap-2">
              <span className="text-3xl">{f.icon}</span>
              <h3 className="font-semibold text-gray-800">{f.title}</h3>
              <p className="text-sm text-gray-500">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-100 px-6 py-4 text-center text-xs text-gray-400">
        karka-ai © 2026 · המידע מוצג לצרכי לימוד בלבד ואינו מהווה ייעוץ משפטי, תכנוני, או השקעתי.
      </footer>
    </main>
  );
}
