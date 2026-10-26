import { cookies } from 'next/headers'

export async function ThemeToggle() {
  const dark = (await cookies()).get('theme')?.value === 'dark'
  return <button>{dark ? 'Light' : 'Dark'}</button>
}
