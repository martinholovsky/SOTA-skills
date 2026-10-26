export function isValidQty(v: string) {
  return !isNaN(v as unknown as number);
}
