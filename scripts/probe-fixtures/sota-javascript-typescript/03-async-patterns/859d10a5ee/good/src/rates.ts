export async function getRates() {
  const res = await fetch('https://api.example.com/rates', { signal: AbortSignal.timeout(5000) });
  return res.json();
}
