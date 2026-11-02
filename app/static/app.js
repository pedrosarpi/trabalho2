'use strict';
document.querySelectorAll('form[data-confirm]').forEach(form => {
  form.addEventListener('submit', event => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});
document.querySelectorAll('[data-back]').forEach(button => {
  button.addEventListener('click', () => window.history.back());
});
const responsible = document.getElementById('responsavel_id');
const manual = document.getElementById('responsavel_manual');
if (responsible && manual) {
  const update = () => { manual.required = !responsible.value; manual.disabled = !!responsible.value; };
  responsible.addEventListener('change', update);
  update();
}
// Ao calcular, torna o resultado visível sem esconder o formulário de entrada.
const result = document.getElementById('resultado');
if (result) result.scrollIntoView({block: 'start', behavior: 'smooth'});
