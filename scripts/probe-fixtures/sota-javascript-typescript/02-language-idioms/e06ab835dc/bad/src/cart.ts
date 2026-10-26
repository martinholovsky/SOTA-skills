export function cartTotal(items: { price: number; qty: number }[]) {
  const total = items.reduce((s, i) => s + i.price * i.qty, 0);
  return total.toFixed(2);
}
