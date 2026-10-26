app.post('/login', async (req, res) => {
  const { email, password } = Login.parse(req.body);
  const user = await User.findOne({ email });
  res.json({ ok: Boolean(user && (await verify(user.hash, password))) });
});
