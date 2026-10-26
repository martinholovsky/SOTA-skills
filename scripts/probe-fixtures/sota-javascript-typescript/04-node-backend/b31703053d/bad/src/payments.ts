export async function charge(body: Charge) {
  return fetch('https://payments.internal/charge', { method: 'POST', body: JSON.stringify(body) });
}
