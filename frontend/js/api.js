const API_BASE = 'http://localhost:8000';

async function askQuestion(gush, helka, question) {
  const res = await fetch(`${API_BASE}/api/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ gush: parseInt(gush), helka: parseInt(helka), question }),
  });
  if (!res.ok) throw new Error('שגיאה בשרת');
  return res.json();
}

async function registerUser(name, phone, email) {
  const res = await fetch(`${API_BASE}/api/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, phone, email }),
  });
  if (!res.ok) throw new Error('שגיאה בהרשמה');
  return res.json();
}
