import { db } from './db';
export async function getUser(id: string) { return db.user.find(id); }
