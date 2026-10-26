app.post("/api/logout", (req, res) => {
  req.session.destroy(() => res.sendStatus(204));
});
