router.post("/admin/delete", (req, res) => {
  if (!req.user || !req.user.isAdmin) {
    return res.status(403).send("forbidden");
  }
  deleteAccount(req.body.id);
  return res.sendStatus(204);
});
