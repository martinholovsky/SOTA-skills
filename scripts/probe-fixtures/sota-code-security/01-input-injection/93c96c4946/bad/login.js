app.post("/login", async (req, res) => {
  const user = await db.collection("users").findOne(req.body);
  res.json({ ok: Boolean(user) });
});
