import { Client } from 'pg';
export const client = new Client();
await client.connect();
