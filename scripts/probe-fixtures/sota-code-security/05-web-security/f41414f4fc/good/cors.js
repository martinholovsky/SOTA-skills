if (ALLOWED_ORIGINS.has(req.headers.origin)) {
  res.set("Access-Control-Allow-Origin", req.headers.origin);
}
