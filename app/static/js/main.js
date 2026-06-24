// Convert UTC kickoff times to local timezone
document.querySelectorAll('.kickoff-time').forEach(el => {
  const utc = new Date(el.dataset.utc);
  if (!isNaN(utc)) {
    el.textContent = utc.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }
});

// Tab between score inputs + AJAX submit with visual feedback
document.querySelectorAll('.pred-form').forEach(form => {
  const inputs = form.querySelectorAll('.score-input');
  inputs.forEach((input, idx) => {
    input.addEventListener('keydown', e => {
      if (e.key === 'Tab' && !e.shiftKey && idx === 0) {
        e.preventDefault();
        inputs[1].focus();
      }
    });
  });

  form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('.btn-submit');
    const body = new URLSearchParams(new FormData(form));

    btn.disabled = true;
    btn.textContent = '...';

    try {
      const res = await fetch(form.action, {
        method: 'POST',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        body,
      });

      if (res.ok) {
        btn.classList.remove('btn-submit--new', 'btn-submit--update');
        btn.classList.add('btn-submit--saved');
        btn.textContent = '✓ Salvo';
        setTimeout(() => {
          btn.textContent = '✏️ Atualizar';
          btn.classList.remove('btn-submit--saved');
          btn.classList.add('btn-submit--update');
          btn.disabled = false;
        }, 1800);
      } else {
        btn.textContent = 'Erro';
        btn.classList.add('btn-submit--error');
        setTimeout(() => {
          btn.classList.remove('btn-submit--error');
          btn.disabled = false;
          btn.textContent = btn.classList.contains('btn-submit--new') ? '⚽ Palpitar' : '✏️ Atualizar';
        }, 2000);
      }
    } catch {
      btn.textContent = 'Erro';
      btn.disabled = false;
    }
  });
});
