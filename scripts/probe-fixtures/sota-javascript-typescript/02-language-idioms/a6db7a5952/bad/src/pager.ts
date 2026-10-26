export function pageSize(q: { limit?: number }) {
  return q.limit || 20;
}
export const offset = (q: { offset?: number }) => q.offset || 0;
