const QUOTA_FREE = 5;
const QUOTA_REGISTERED = 50;

function getQuota() {
  const data = JSON.parse(localStorage.getItem('karka_quota') || '{}');
  const today = new Date().toDateString();
  if (data.date !== today) {
    const fresh = {
      date: today,
      used: 0,
      registered: data.registered || false,
      limit: data.registered ? QUOTA_REGISTERED : QUOTA_FREE,
    };
    localStorage.setItem('karka_quota', JSON.stringify(fresh));
    return fresh;
  }
  return data;
}

function consumeQuestion() {
  const q = getQuota();
  if (q.used >= q.limit) return false;
  q.used++;
  localStorage.setItem('karka_quota', JSON.stringify(q));
  const left = q.limit - q.used;
  const el = document.getElementById('quota-left');
  if (el) el.textContent = left;
  if (left <= 1) {
    const textEl = document.getElementById('quota-text');
    if (textEl) textEl.style.color = '#e63946';
  }
  return true;
}

function markRegistered() {
  const q = getQuota();
  q.registered = true;
  q.limit = QUOTA_REGISTERED;
  localStorage.setItem('karka_quota', JSON.stringify(q));
}
