app.get("/api/roles", async (req, res) => {
  res.json(await Roles.listAssignments(req.query.userId));
});
