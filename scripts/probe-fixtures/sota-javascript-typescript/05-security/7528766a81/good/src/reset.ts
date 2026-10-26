import { randomBytes } from 'node:crypto';
export const resetCode = () => randomBytes(16).toString('base64url');
