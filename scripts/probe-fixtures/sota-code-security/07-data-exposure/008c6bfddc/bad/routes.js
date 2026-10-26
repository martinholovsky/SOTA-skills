app.post("/api/client-logs", (req, res) => {
  logger.info(req.body);
  res.sendStatus(204);
});
