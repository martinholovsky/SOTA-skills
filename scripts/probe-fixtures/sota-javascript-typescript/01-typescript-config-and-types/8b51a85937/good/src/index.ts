export interface Client {
  get(id: string): Promise<User>;
}
export { createClient } from './client';
