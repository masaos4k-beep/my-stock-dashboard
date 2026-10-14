const chips = document.querySelectorAll('.filter-chip');
const cards = document.querySelectorAll('.content-card');
chips.forEach(chip => chip.addEventListener('click', () => {
  const selected = chip.dataset.filter;
  chips.forEach(item => item.classList.toggle('active', item === chip));
  cards.forEach(card => { card.hidden = selected !== 'すべて' && card.dataset.category !== selected; });
}));
const menuButton = document.querySelector('.menu-toggle');
const nav = document.querySelector('.main-nav');
menuButton.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  menuButton.setAttribute('aria-expanded', String(open));
});
nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
  nav.classList.remove('open');
  menuButton.setAttribute('aria-expanded', 'false');
}));
document.getElementById('year').textContent = new Date().getFullYear();
