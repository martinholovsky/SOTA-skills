import { PrefsSchema } from './schema';
export function loadPrefs() {
  return PrefsSchema.safeParse(JSON.parse(localStorage.getItem('prefs') ?? '{}'));
}
