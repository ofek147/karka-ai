document.addEventListener('DOMContentLoaded', () => {
  initQuotaDisplay();
  initNavScroll();
  initToolForm();
  initRegisterModal();
});

function initQuotaDisplay() {
  const q = getQuota();
  const left = q.limit - q.used;
  const el = document.getElementById('quota-left');
  if (el) el.textContent = left;
  if (left <= 1) {
    const textEl = document.getElementById('quota-text');
    if (textEl) textEl.style.color = '#e63946';
  }
}

function initNavScroll() {
  const nav = document.querySelector('.nav');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 60);
  }, { passive: true });
}

function initToolForm() {
  const btn = document.getElementById('submit-btn');
  if (!btn) return;
  btn.addEventListener('click', handleSubmit);

  const questionInput = document.getElementById('question');
  if (questionInput) {
    questionInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleSubmit();
    });
  }
}

async function handleSubmit() {
  const gush = document.getElementById('gush').value.trim();
  const helka = document.getElementById('helka').value.trim();
  const question = document.getElementById('question').value.trim();

  if (!gush || !helka || !question) {
    alert('אנא מלא את כל השדות');
    return;
  }

  if (!consumeQuestion()) {
    openRegisterModal();
    return;
  }

  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  btn.textContent = 'מחפש...';

  const resultEl = document.getElementById('result');
  resultEl.style.display = 'none';

  try {
    const data = await askQuestion(gush, helka, question);
    document.getElementById('result-meta').textContent =
      `גוש ${gush} • חלקה ${helka} • מקור: ${data.source}`;
    document.getElementById('result-answer').textContent = data.answer;
    resultEl.style.display = 'block';
    resultEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch {
    alert('שגיאה בחיבור לשרת. אנא ודא שהשרת פועל ונסה שוב.');
    const q = getQuota();
    q.used = Math.max(0, q.used - 1);
    localStorage.setItem('karka_quota', JSON.stringify(q));
    initQuotaDisplay();
  } finally {
    btn.disabled = false;
    btn.textContent = 'בדוק עכשיו ←';
  }
}

function openRegisterModal() {
  document.getElementById('register-modal').style.display = 'flex';
}

function closeRegisterModal() {
  document.getElementById('register-modal').style.display = 'none';
}

function initRegisterModal() {
  const overlay = document.getElementById('register-modal');
  if (!overlay) return;

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeRegisterModal();
  });

  const form = document.getElementById('register-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = form.querySelector('[name="name"]').value.trim();
    const phone = form.querySelector('[name="phone"]').value.trim();
    const email = form.querySelector('[name="email"]').value.trim();

    const submitBtn = form.querySelector('button[type="submit"]');
    submitBtn.disabled = true;
    submitBtn.textContent = 'רושם...';

    try {
      await registerUser(name, phone, email);
      markRegistered();
      closeRegisterModal();
      initQuotaDisplay();
    } catch {
      alert('שגיאה בהרשמה. אנא נסה שוב.');
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = 'המשך ←';
    }
  });
}
