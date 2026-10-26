import { createPool } from './pool';
const pool = await createPool(process.env.DATABASE_URL);
export { pool };
