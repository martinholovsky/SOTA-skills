export function saveTheme(theme: 'light' | 'dark') {
  localStorage.setItem('theme', theme);
  sessionStorage.setItem('lastTab', 'home');
}
