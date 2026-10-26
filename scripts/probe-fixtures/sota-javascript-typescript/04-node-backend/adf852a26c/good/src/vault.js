import crypto from 'node:crypto';
export const encrypt = (key, text) => {
  const iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', key, iv, { authTagLength: 16 });
  const ct = Buffer.concat([c.update(text, 'utf8'), c.final()]);
  return { iv, ct, tag: c.getAuthTag() };
};
