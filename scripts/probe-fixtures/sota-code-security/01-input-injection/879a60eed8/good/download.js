app.get("/download", (req, res) => {
  const name = headerSafe(req.query.name); // printable ASCII, CR/LF rejected
  res.setHeader("X-Filename", name);
  res.sendFile(resolveFile(name));
});
