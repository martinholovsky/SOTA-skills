export async function verify(token: string) {
  const { payload } = await jwtVerify(token, JWKS, { issuer: ISS, audience: AUD, typ: 'at+jwt' });
  return payload;
}
