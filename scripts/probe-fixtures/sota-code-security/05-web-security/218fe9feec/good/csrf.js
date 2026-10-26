function csrfGuard(req, res, next) {
  if (!verifySignedToken(req.get("x-csrf-token"), req.session.id)) return res.sendStatus(403);
  next();
}
