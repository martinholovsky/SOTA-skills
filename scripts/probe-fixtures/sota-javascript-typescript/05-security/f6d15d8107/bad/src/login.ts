export function setSession(res: Res, sid: string) {
  res.cookie('sid', sid, { sameSite: 'lax' });
}
