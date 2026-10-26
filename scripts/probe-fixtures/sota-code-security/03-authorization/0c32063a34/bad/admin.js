router.post("/admin/delete", (req, res) => {
  if (!req.user || !req.user.isAdmin) {
    res.status(403).send("forbidden");
  }
  deleteAccount(req.body.id);
  res.sendStatus(204);
});
