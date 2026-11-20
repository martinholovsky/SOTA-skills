export function loadPrefs(): Prefs {
  return JSON.parse(localStorage.getItem('prefs') ?? '{}') as Prefs;
}
