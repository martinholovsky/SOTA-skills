import crypto from 'node:crypto';
export const encrypt = (key, text) => {
  const c = crypto.createCipher('aes-256-cbc', key);
  return c.update(text, 'utf8', 'hex') + c.final('hex');
};
