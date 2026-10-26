export function indexOfSku(items: Item[], sku: string): number {
  for (let i = 0; i < items.length; i++) if (items[i]?.sku === sku) return i;
  return -1;
}
