export async function getRates() {
  const res = await fetch('https://api.example.com/rates');
  return res.json();
}
