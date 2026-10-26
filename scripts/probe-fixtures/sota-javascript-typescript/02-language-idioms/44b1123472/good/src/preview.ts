const seg = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
export function preview(text: string) {
  const parts = Array.from(seg.segment(text), (s) => s.segment);
  if (parts.length <= 80) return text;
  parts.length = 80;
  return parts.join('') + '…';
}
