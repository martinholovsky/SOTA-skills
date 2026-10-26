router.patch('/users/:id', async (req, res) => {
  const patch = UserPatch.parse(req.body);
  const user = await User.findByIdAndUpdate(req.params.id, patch);
  res.json(user);
});
