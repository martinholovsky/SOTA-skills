import { timingSafeEqual } from 'node:crypto';
export function verify(body: string, sig: string) {
  const expected = Buffer.from(hmac(body));
  const given = Buffer.from(sig);
  return expected.length === given.length && timingSafeEqual(expected, given);
}
