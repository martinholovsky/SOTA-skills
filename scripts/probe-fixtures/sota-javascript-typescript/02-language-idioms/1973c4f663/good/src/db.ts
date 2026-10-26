import { Client } from 'pg';
export async function connectDb(): Promise<Client> {
  const client = new Client();
  await client.connect();
  return client;
}
