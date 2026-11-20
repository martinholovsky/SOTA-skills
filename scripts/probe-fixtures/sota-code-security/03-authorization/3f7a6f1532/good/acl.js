app.get("/api/roles", requirePermission("roles:read"), async (req, res) => {
  res.json(await Roles.listAssignments(req.query.userId));
});
