export function cartTotalCents(items: { priceCents: bigint; qty: bigint }[]) {
  return items.reduce((s, i) => s + i.priceCents * i.qty, 0n);
}
