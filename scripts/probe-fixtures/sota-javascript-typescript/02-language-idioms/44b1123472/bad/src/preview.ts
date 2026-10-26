export function preview(text: string) {
  return text.length > 80 ? text.slice(0, 80) + '…' : text;
}
