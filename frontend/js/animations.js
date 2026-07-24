const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const delay = entry.target.dataset.delay || 0;
      setTimeout(() => {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
      }, Number(delay));
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });

document.querySelectorAll('.reveal-card').forEach((el, i) => {
  el.dataset.delay = i * 120;
  revealObserver.observe(el);
});

document.querySelectorAll('.reveal-step').forEach((el, i) => {
  el.dataset.delay = i * 150;
  revealObserver.observe(el);
});

function typewriter(el, text, speed = 22) {
  let i = 0;
  el.textContent = '';
  const iv = setInterval(() => {
    el.textContent += text[i++];
    if (i >= text.length) clearInterval(iv);
  }, speed);
}

const demoObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const el = document.querySelector('.typewriter-text');
      if (el && el.dataset.text) typewriter(el, el.dataset.text);
      demoObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.3 });

const demoCard = document.querySelector('.demo-card');
if (demoCard) demoObserver.observe(demoCard);
