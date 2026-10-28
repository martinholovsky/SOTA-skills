import { createPool } from './pool';
export const pool = await createPool(process.env.DATABASE_URL);
