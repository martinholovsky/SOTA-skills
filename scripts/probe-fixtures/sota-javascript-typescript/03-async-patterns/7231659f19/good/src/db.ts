import { createPool } from './pool';
let poolPromise: ReturnType<typeof createPool> | undefined;
export function getPool() {
  poolPromise ??= createPool(process.env.DATABASE_URL);
  return poolPromise;
}
