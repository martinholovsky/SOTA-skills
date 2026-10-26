export function rememberTheme(theme: 'light' | 'dark') {
  sessionStorage.setItem('theme', theme);
}
