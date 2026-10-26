app.post('/login', async (req, res) => {
  const user = await User.findOne({ email: req.body.email, password: req.body.password });
  res.json({ ok: Boolean(user) });
});
