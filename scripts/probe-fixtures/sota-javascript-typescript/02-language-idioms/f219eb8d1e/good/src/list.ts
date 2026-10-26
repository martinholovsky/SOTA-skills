const Limit = z.coerce.number().int().finite().min(1).max(100);
export function listLimit(req: Request) {
  return Limit.parse(req.query.limit);
}
