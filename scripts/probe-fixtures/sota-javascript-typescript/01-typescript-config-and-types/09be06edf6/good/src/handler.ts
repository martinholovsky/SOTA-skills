export function handle(payload: unknown) {
  if (typeof payload === 'object' && payload !== null && 'id' in payload) return payload.id;
  return undefined;
}
