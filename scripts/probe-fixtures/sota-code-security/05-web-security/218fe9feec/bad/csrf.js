function csrfGuard(req, res, next) {
  if (req.get("x-csrf-token") !== req.cookies.csrf) return res.sendStatus(403);
  next();
}
