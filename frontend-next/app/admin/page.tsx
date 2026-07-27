"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "https://api.karka-ai.co.il";

interface Parcel { gush: number; helka: number; count: number; }
interface LeadSession { id: string; title: string; created_at: string; messages: { role: string; content: string }[]; }
interface Lead {
  id: number; name: string; email: string; phone: string; score: number;
  topics: string[]; parcels: Parcel[]; total_questions: number;
  total_sessions: number; source: string | null;
  last_active: string | null; created_at: string | null;
}

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 71 ? "#22c55e" : score >= 31 ? "#eab308" : "#6b7280";
  const bg = score >= 71 ? "rgba(34,197,94,0.15)" : score >= 31 ? "rgba(234,179,8,0.15)" : "rgba(107,114,128,0.15)";
  return (
    <span style={{ color, background: bg, border: `1px solid ${color}`, padding: "2px 10px", borderRadius: 999, fontWeight: 700, fontSize: 13 }}>
      {score}
    </span>
  );
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("he-IL", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export default function AdminPage() {
  const [token, setToken] = useState<string>(() =>
    typeof window !== "undefined" ? sessionStorage.getItem("admin_token") || "" : ""
  );
  const [tokenInput, setTokenInput] = useState("");
  const [authError, setAuthError] = useState("");

  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [sessions, setSessions] = useState<Record<number, LeadSession[]>>({});

  async function fetchLeads(t: string) {
    setLoading(true);
    const res = await fetch(`${API}/api/admin/leads`, {
      headers: { Authorization: `Bearer ${t}` },
    });
    if (res.status === 401) { setAuthError("טוקן שגוי"); setLoading(false); return; }
    const data = await res.json();
    setLeads(data);
    setLoading(false);
  }

  function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setAuthError("");
    sessionStorage.setItem("admin_token", tokenInput);
    setToken(tokenInput);
    fetchLeads(tokenInput);
  }

  useEffect(() => {
    if (token) fetchLeads(token);
  }, []); // eslint-disable-line

  async function toggleLead(id: number) {
    if (expanded === id) { setExpanded(null); return; }
    setExpanded(id);
    if (!sessions[id]) {
      const res = await fetch(`${API}/api/admin/leads/${id}/sessions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setSessions(prev => ({ ...prev, [id]: data }));
    }
  }

  async function deleteLead(e: React.MouseEvent, id: number) {
    e.stopPropagation();
    if (!confirm(`למחוק ליד #${id}?`)) return;
    await fetch(`${API}/api/admin/leads/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    setLeads(prev => prev.filter(l => l.id !== id));
  }

  // ── Login screen ──────────────────────────────────────────────────────────
  if (!token || authError) {
    return (
      <main dir="rtl" style={{ minHeight: "100vh", background: "#0d1829", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <form onSubmit={handleLogin} style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 16, padding: "40px 32px", width: 320, display: "flex", flexDirection: "column", gap: 16 }}>
          <h2 style={{ color: "#c4a044", margin: 0, textAlign: "center", fontSize: 20 }}>
            kark<span style={{ fontStyle: "italic" }}>A</span>i Admin
          </h2>
          <input
            type="password"
            placeholder="Admin Token"
            value={tokenInput}
            onChange={e => setTokenInput(e.target.value)}
            style={{ border: "1px solid rgba(255,255,255,0.15)", borderRadius: 10, padding: "10px 14px", background: "rgba(255,255,255,0.06)", color: "#e2e8f0", fontSize: 14, outline: "none" }}
            autoFocus
          />
          {authError && <p style={{ color: "#ef4444", fontSize: 13, margin: 0 }}>{authError}</p>}
          <button type="submit" style={{ background: "#c4a044", color: "#fff", border: "none", borderRadius: 10, padding: "10px", fontWeight: 700, cursor: "pointer", fontSize: 15 }}>
            כניסה
          </button>
        </form>
      </main>
    );
  }

  // ── Dashboard ─────────────────────────────────────────────────────────────
  return (
    <main dir="rtl" style={{ minHeight: "100vh", background: "#0d1829", color: "#e2e8f0", fontFamily: "sans-serif", padding: "32px 24px" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ marginBottom: 28, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: "#c4a044", margin: 0 }}>
              kark<span style={{ fontStyle: "italic" }}>A</span>i — לידים
            </h1>
            <p style={{ color: "#64748b", fontSize: 13, marginTop: 4 }}>{leads.length} רשומים</p>
          </div>
          <button onClick={() => { sessionStorage.removeItem("admin_token"); setToken(""); setTokenInput(""); }}
            style={{ background: "transparent", border: "1px solid rgba(255,255,255,0.15)", color: "#94a3b8", borderRadius: 8, padding: "6px 14px", cursor: "pointer", fontSize: 13 }}>
            יציאה
          </button>
        </div>

        {loading && <p style={{ color: "#64748b" }}>טוען...</p>}

        {!loading && (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", color: "#94a3b8", fontSize: 12 }}>
                  {["שם", "מייל", "טלפון", "ציון", "נושאים", "שאלות", "סשנים", "פעיל לאחרונה", ""].map(h => (
                    <th key={h} style={{ padding: "8px 12px", textAlign: "right", fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {leads.map(lead => (
                  <>
                    <tr
                      key={lead.id}
                      onClick={() => toggleLead(lead.id)}
                      style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", cursor: "pointer" }}
                      onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.04)")}
                      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
                    >
                      <td style={{ padding: "12px 12px", fontWeight: 600 }}>{lead.name}</td>
                      <td style={{ padding: "12px 12px", color: "#94a3b8" }}>{lead.email}</td>
                      <td style={{ padding: "12px 12px", color: "#94a3b8" }}>{lead.phone}</td>
                      <td style={{ padding: "12px 12px" }}><ScoreBadge score={lead.score} /></td>
                      <td style={{ padding: "12px 12px" }}>
                        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                          {lead.topics.map(t => (
                            <span key={t} style={{ background: "rgba(196,160,68,0.15)", color: "#c4a044", borderRadius: 4, padding: "1px 7px", fontSize: 11 }}>{t}</span>
                          ))}
                        </div>
                      </td>
                      <td style={{ padding: "12px 12px", textAlign: "center" }}>{lead.total_questions}</td>
                      <td style={{ padding: "12px 12px", textAlign: "center" }}>{lead.total_sessions}</td>
                      <td style={{ padding: "12px 12px", color: "#64748b", fontSize: 12 }}>{formatDate(lead.last_active)}</td>
                      <td style={{ padding: "12px 12px" }}>
                        <button onClick={e => deleteLead(e, lead.id)}
                          style={{ background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)", color: "#ef4444", borderRadius: 6, padding: "3px 10px", cursor: "pointer", fontSize: 12 }}>
                          מחק
                        </button>
                      </td>
                    </tr>

                    {expanded === lead.id && (
                      <tr key={`${lead.id}-exp`}>
                        <td colSpan={9} style={{ padding: "0 12px 16px", background: "rgba(0,0,0,0.3)" }}>
                          {!sessions[lead.id] ? (
                            <p style={{ color: "#64748b", padding: "12px 0" }}>טוען שיחות...</p>
                          ) : sessions[lead.id].length === 0 ? (
                            <p style={{ color: "#64748b", padding: "12px 0" }}>אין שיחות</p>
                          ) : (
                            sessions[lead.id].map(session => (
                              <div key={session.id} style={{ marginTop: 12, borderRight: "2px solid #c4a044", paddingRight: 12 }}>
                                <p style={{ fontWeight: 600, color: "#c4a044", marginBottom: 8, fontSize: 13 }}>
                                  {session.title} <span style={{ color: "#475569", fontWeight: 400 }}>— {formatDate(session.created_at)}</span>
                                </p>
                                {session.messages.map((msg, i) => (
                                  <div key={i} style={{ marginBottom: 6, display: "flex", gap: 8, alignItems: "flex-start" }}>
                                    <span style={{ fontSize: 11, color: msg.role === "user" ? "#c4a044" : "#64748b", minWidth: 60, paddingTop: 2 }}>
                                      {msg.role === "user" ? "👤 משתמש" : "🤖 AI"}
                                    </span>
                                    <span style={{ fontSize: 13, color: "#cbd5e1", lineHeight: 1.5 }}>{msg.content}</span>
                                  </div>
                                ))}
                              </div>
                            ))
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
            {leads.length === 0 && !loading && (
              <p style={{ textAlign: "center", color: "#475569", padding: 40 }}>אין לידים עדיין</p>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
