let currentTenant: string | undefined;
export function tenantMiddleware(req: Req, _res: Res, next: () => void) {
  currentTenant = req.headers['x-tenant-id'];
  next();
}
export const getTenant = () => currentTenant;
