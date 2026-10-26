app.post("/login", async (req, res) => {
  const user = await db.collection("users").findOne({ email: String(req.body.email) });
  res.json({ ok: Boolean(user) });
});
