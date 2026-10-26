import jwt from 'jsonwebtoken';
export const userFrom = (token: string) => jwt.verify(token, publicKey, { algorithms: ['RS256'], audience: 'api' });
