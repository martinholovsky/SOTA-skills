export function verify(body: string, signature: string) {
  const expected = hmac(body);
  return expected === signature;
}
