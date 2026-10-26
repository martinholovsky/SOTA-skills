export async function verify(token: string) {
  const { payload } = await jwtVerify(token, JWKS, { issuer: ISS, audience: AUD });
  return payload;
}
