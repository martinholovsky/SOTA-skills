app.get("/download", (req, res) => {
  res.setHeader("X-Filename", req.query.name);
  res.sendFile(resolveFile(req.query.name));
});
