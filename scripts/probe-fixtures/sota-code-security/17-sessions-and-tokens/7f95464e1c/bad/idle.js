function isExpired(req) {
  const last = Number(req.body.lastActivity);
  return Date.now() - last > IDLE_MS;
}
