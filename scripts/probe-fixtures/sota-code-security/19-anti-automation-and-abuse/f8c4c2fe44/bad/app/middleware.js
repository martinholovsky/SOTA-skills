export function skipChallenge(req, res, next) {
  if (/googlebot|bingbot/i.test(req.headers['user-agent'])) return next();
  return challenge(req, res, next);
}
