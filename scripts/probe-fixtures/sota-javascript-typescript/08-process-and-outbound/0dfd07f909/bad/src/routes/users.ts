router.patch('/users/:id', async (req, res) => {
  const user = await User.findByIdAndUpdate(req.params.id, req.body);
  res.json(user);
});
