import { AsyncLocalStorage } from 'node:async_hooks';
const tenantStore = new AsyncLocalStorage<string>();
export function tenantMiddleware(req: Req, _res: Res, next: () => void) {
  tenantStore.run(String(req.headers['x-tenant-id']), next);
}
export function getTenant(): string {
  const t = tenantStore.getStore();
  if (t === undefined) throw new Error('no tenant in context');
  return t;
}
