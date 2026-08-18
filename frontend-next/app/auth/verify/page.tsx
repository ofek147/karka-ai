"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { verifyMagicToken } from "@/lib/api";
import { saveUser } from "@/lib/auth";
import KarkaLogo from "@/components/KarkaLogo";

function VerifyInner() {
  const params = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    const token = params.get("token");
    if (!token) { setStatus("error"); setError("קישור לא תקין"); return; }

    verifyMagicToken(token)
      .then(user => {
        saveUser(user);
        setStatus("success");
        setTimeout(() => { window.location.href = "/chat"; }, 1500);
      })
      .catch(err => {
        setStatus("error");
        setError(err instanceof Error ? err.message : "קישור לא תקין או פג תוקף");
      });
  }, [params, router]);

  return (
    <main className="min-h-screen bg-[#0d1829] flex flex-col items-center justify-center gap-6 px-4" dir="rtl">
      <KarkaLogo size="lg" />

      {status === "loading" && (
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-[#c4a044]/30 border-t-[#c4a044] rounded-full animate-spin" />
          <p className="text-slate-400 text-sm">מאמת את הקישור...</p>
        </div>
      )}

      {status === "success" && (
        <div className="flex flex-col items-center gap-3">
          <div className="w-14 h-14 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center text-2xl">✓</div>
          <p className="text-white font-semibold">מחובר בהצלחה!</p>
          <p className="text-slate-400 text-sm">מועבר לצ׳אט...</p>
        </div>
      )}

      {status === "error" && (
        <div className="flex flex-col items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center text-2xl">✕</div>
          <p className="text-white font-semibold">{error}</p>
          <button
            onClick={() => router.push("/chat")}
            className="px-6 py-2.5 rounded-xl text-sm font-medium text-white border border-white/20 hover:bg-white/8 transition-colors"
          >
            חזור לצ׳אט
          </button>
        </div>
      )}
    </main>
  );
}

export default function VerifyPage() {
  return (
    <Suspense fallback={
      <main className="min-h-screen bg-[#0d1829] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#c4a044]/30 border-t-[#c4a044] rounded-full animate-spin" />
      </main>
    }>
      <VerifyInner />
    </Suspense>
  );
}
