export function ThemeToggle() {
  const dark = typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
  return <button>{dark ? 'Light' : 'Dark'}</button>
}
