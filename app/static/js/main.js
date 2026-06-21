// Convert UTC kickoff times to local timezone
document.querySelectorAll('.kickoff-time').forEach(el => {
  const utc = new Date(el.dataset.utc);
  if (!isNaN(utc)) {
    el.textContent = utc.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }
});

// Tab between score inputs, Enter submits form
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
});
