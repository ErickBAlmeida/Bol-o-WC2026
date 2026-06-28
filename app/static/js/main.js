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
  const isKnockout = form.dataset.knockout === 'true';
  const picker = form.querySelector('.tiebreaker-picker');
  const tbInput = form.querySelector('input[name="tiebreaker"]');

  inputs.forEach((input, idx) => {
    input.addEventListener('keydown', e => {
      if (e.key === 'Tab' && !e.shiftKey && idx === 0) {
        e.preventDefault();
        inputs[1].focus();
      }
    });
  });

  function isDraw() {
    const h = inputs[0].value;
    const a = inputs[1].value;
    return h !== '' && a !== '' && h === a;
  }

  function updateTiebreakerVisibility() {
    if (!isKnockout || !picker) return;
    if (isDraw()) {
      picker.classList.remove('hidden');
    } else {
      picker.classList.add('hidden');
      // clear selection
      if (tbInput) tbInput.value = '';
      picker.querySelectorAll('.tb-btn').forEach(b => b.classList.remove('tb-btn--selected'));
    }
  }

  if (isKnockout && picker) {
    inputs.forEach(input => input.addEventListener('input', updateTiebreakerVisibility));

    // Restore previously saved tiebreaker selection on load
    if (tbInput && tbInput.value) {
      const saved = tbInput.value;
      picker.querySelectorAll('.tb-btn').forEach(btn => {
        if (btn.dataset.value === saved) btn.classList.add('tb-btn--selected');
      });
      updateTiebreakerVisibility();
    }

    picker.querySelectorAll('.tb-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        picker.querySelectorAll('.tb-btn').forEach(b => b.classList.remove('tb-btn--selected'));
        btn.classList.add('tb-btn--selected');
        if (tbInput) tbInput.value = btn.dataset.value;
      });
    });
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();

    // Validate tiebreaker if knockout draw
    if (isKnockout && isDraw() && tbInput && !tbInput.value) {
      picker.classList.add('tb-required');
      setTimeout(() => picker.classList.remove('tb-required'), 1500);
      return;
    }

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
