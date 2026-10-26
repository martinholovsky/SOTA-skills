export function setSession(res: Res, sid: string) {
  res.cookie('sid', sid, { httpOnly: true, secure: true, sameSite: 'lax' });
}
