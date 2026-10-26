import jwt from 'jsonwebtoken';
export const userFrom = (token: string) => jwt.decode(token) as Claims;
