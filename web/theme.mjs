const root = document.documentElement;
const toggle = document.getElementById('theme-toggle');
const systemTheme = matchMedia('(prefers-color-scheme: dark)');
let preference;
try { preference = localStorage.getItem('semaphore-theme'); } catch { /* Storage is optional. */ }

function applyTheme() {
  const theme = ['light', 'dark'].includes(preference) ? preference : systemTheme.matches ? 'dark' : 'light';
  root.dataset.theme = theme;
  const label = theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
  toggle.setAttribute('aria-label', label);
  toggle.title = label;
}

toggle.addEventListener('click', () => {
  preference = root.dataset.theme === 'dark' ? 'light' : 'dark';
  try { localStorage.setItem('semaphore-theme', preference); } catch { /* The tab keeps its choice. */ }
  applyTheme();
});
systemTheme.addEventListener('change', applyTheme);
applyTheme();
