export function listLimit(req: Request) {
  const limit = parseInt(req.query.limit as string, 10);
  return limit > 100 ? 100 : limit;
}
