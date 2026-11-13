// Lightweight progressive enhancement: mark the active dashboard section in navigation.
const sections = [...document.querySelectorAll('main section[id]')];
const links = [...document.querySelectorAll('.sidebar nav a')];
const observer = new IntersectionObserver(entries => {
  const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!visible) return;
  links.forEach(link => link.classList.toggle('active', link.hash === `#${visible.target.id}`));
}, { rootMargin: '-15% 0px -70% 0px', threshold: [0, .15, .5] });
sections.forEach(section => observer.observe(section));
