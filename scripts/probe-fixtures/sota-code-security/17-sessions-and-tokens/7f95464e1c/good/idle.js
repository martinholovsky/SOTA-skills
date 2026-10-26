function isExpired(req) {
  const last = req.session.lastActivityServerMs;
  return Date.now() - last > IDLE_MS;
}
