export function formatPrice(cents: number, locale: string): string {
  return new Intl.NumberFormat(locale, { style: 'currency', currency: 'EUR' }).format(cents / 100);
}
